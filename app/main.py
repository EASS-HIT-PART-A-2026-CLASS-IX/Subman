import os
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Generator, List
from urllib.parse import unquote

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Subscription
import time
from sqlalchemy.exc import OperationalError
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import (
    TokenData,
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
)
 
# ---------------------------------------------------------------------------
# Config (swap for pydantic-settings / .env in production)
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///subman.db")

# Stub exchange rates — replace with a live FX API call in production
EXCHANGE_RATES = {
    "ILS": 1.0,
    "USD": 3.7,
    "EUR": 4.0,
}

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event("startup"))
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # מנגנון Retry חכם להתחברות ל-PostgreSQL בזמן עליית הדוקר
    retries = 5
    while retries > 0:
        try:
            print("🔄 Attempting to connect to the database and create tables...")
            SQLModel.metadata.create_all(engine)
            print("✅ Database connection successful! Tables are ready.")
            break
        except OperationalError:
            retries -= 1
            print(f"⚠️ Database not ready yet. Retries left: {retries}. Waiting 3 seconds...")
            time.sleep(3)
            
    if retries == 0:
        print("❌ Could not connect to the database. Exiting.")
        raise RuntimeError("Database connection failed permanently.")
        
    yield

app = FastAPI(lifespan=lifespan)

class Token(BaseModel):
    access_token: str
    token_type: str
 
@app.post("/auth/token", response_model=Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Exchange username + password for a JWT access token.
    Use the token as:  Authorization: Bearer <token>
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, token_type="bearer")
# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

# ---------------------------------------------------------------------------
# Billing helpers
# ---------------------------------------------------------------------------

def _add_months(source: date, months: int = 1) -> date:
    """Advance a date by N months, clamping day to the target month's last day."""
    month_index = source.month - 1 + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1
    last_day = monthrange(year, month)[1]
    return date(year, month, min(source.day, last_day))


def calculate_next_billing(reference_date: date, cycle: str) -> str:
    """
    Return the next billing date that is strictly in the future.
    For one-time purchases there is no next billing date.
    """
    if cycle == "one_time":
        return "None"

    today = date.today()
    next_date = reference_date

    # Advance until the date is in the future
    while next_date <= today:
        if cycle == "daily":
            next_date += timedelta(days=1)
        elif cycle == "weekly":
            next_date += timedelta(weeks=1)
        elif cycle == "monthly":
            next_date = _add_months(next_date, 1)
        elif cycle == "yearly":
            next_date = _add_months(next_date, 12)
        else:
            next_date = _add_months(next_date, 1)

    return next_date.isoformat()

# ---------------------------------------------------------------------------
# Audit trail (background task)
# ---------------------------------------------------------------------------

async def log_audit_trail(action: str, sub_name: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] ACTION: {action} subscription for {sub_name.upper()}\n"
    with open("audit.log", "a", encoding="utf-8") as audit_file:
        audit_file.write(entry)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/subscriptions", response_model=List[Subscription])
def get_subscriptions(session: Session = Depends(get_session)) -> List[Subscription]:
    return session.exec(select(Subscription)).all()


@app.post("/subscriptions", status_code=status.HTTP_201_CREATED, response_model=Subscription)
def create_subscription(
    background_tasks: BackgroundTasks,
    sub_data: dict = Body(...),
    session: Session = Depends(get_session),
) -> Subscription:
    try:
        sub = Subscription.model_validate(sub_data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    existing = session.exec(
        select(Subscription).where(func.lower(Subscription.name) == sub.name.lower())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subscription already exists")

    next_billing = calculate_next_billing(sub.purchase_date, sub.billing_cycle)

    db_sub = Subscription(
        name=sub.name,
        price=sub.price,
        currency=sub.currency,
        category=sub.category,
        billing_cycle=sub.billing_cycle,
        status=sub.status,
        purchase_date=sub.purchase_date,
        next_billing_date=next_billing,
    )
    session.add(db_sub)
    session.commit()
    session.refresh(db_sub)

    background_tasks.add_task(log_audit_trail, "Created", db_sub.name)
    return db_sub


@app.delete("/subscriptions/{name}")
def delete_subscription(
    name: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: TokenData = Depends(require_admin),   # ← JWT guard
) -> dict:
    """Delete a subscription. Requires admin JWT token."""
    decoded_name = unquote(name).strip()
    subscription = session.exec(
        select(Subscription).where(
            func.lower(Subscription.name) == decoded_name.lower()
        )
    ).first()
 
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription '{decoded_name}' not found",
        )
 
    sub_name = subscription.name
    session.delete(subscription)
    session.commit()
 
    background_tasks.add_task(log_audit_trail, "Deleted", sub_name)
    return {"message": "Deleted successfully"}

@app.get("/subscriptions/summary")
def get_summary(session: Session = Depends(get_session)) -> dict:
    """
    Returns the monthly burn rate (normalized to ILS) and the count of active subscriptions.
    Filters out future subscriptions and structures calculations efficiently.
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # 1. 🔥 סינון חכם ברמת ה-DB למנויים רגילים (התחלה היום או בעבר)
    standard_subs = session.exec(
        select(Subscription).where(
            Subscription.status == "active",
            Subscription.billing_cycle != "one_time",
            Subscription.purchase_date <= today  # חוסם את באג 2035!
        )
    ).all()

    # 2. 🔥 סינון חכם ברמת ה-DB למנויים חד-פעמיים (רק בתוך חלון 30 הימים האחרונים)
    one_time_subs = session.exec(
        select(Subscription).where(
            Subscription.status == "active",
            Subscription.billing_cycle == "one_time",
            Subscription.purchase_date >= thirty_days_ago,
            Subscription.purchase_date <= today  # מונע כניסת one_time עתידי
        )
    ).all()

    total_ils = 0.0

    # חישוב עלויות למנויים רגילים
    for s in standard_subs:
        rate = EXCHANGE_RATES.get(s.currency.upper(), 1.0)
        base_price_ils = s.price * rate

        if s.billing_cycle == "daily":
            total_ils += base_price_ils * 30
        elif s.billing_cycle == "weekly":
            total_ils += base_price_ils * 4.33
        elif s.billing_cycle == "monthly":
            total_ils += base_price_ils
        elif s.billing_cycle == "yearly":
            total_ils += base_price_ils / 12

    # חישוב עלויות למנויים חד-פעמיים (כולם כבר מסוננים פיקס לחלון ה-30 יום)
    for s in one_time_subs:
        rate = EXCHANGE_RATES.get(s.currency.upper(), 1.0)
        total_ils += s.price * rate

    # 🎯 סכימת כמות המנויים שבאמת רצים ורלוונטיים לחודש הנוכחי
    total_active_current_month = len(standard_subs) + len(one_time_subs)

    return {
        "monthly_burn_rate_ils": round(total_ils, 2),  # עיגול של ה-Float כדי שייראה מקצועי
        "active_subscriptions": total_active_current_month,
    }