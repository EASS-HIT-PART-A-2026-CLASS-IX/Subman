import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool  # 🚀 ייבוא חשוב שנוסף לטובת הזיכרון
from app.main import EXCHANGE_RATES, app, get_session
from app.models import Subscription

# הקמת דאטה-בייס נקי בזיכרון במיוחד עבור הטסטים (חסין ל-Threads)
@pytest.fixture(name="session")
def session_fixture():
    # הוספנו הגדרות שמאפשרות ל-FastAPI לגשת לזיכרון מ-Threads שונים
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# 1. טסט למסלול תקין של יצירת מנוי
def test_create_subscription(client: TestClient):
    payload = {
        "name": "Netflix Test",
        "price": 40.0,
        "currency": "USD",
        "category": "entertainment",
        "billing_cycle": "monthly",
        "status": "active",
        "purchase_date": "2026-06-27"
    }
    response = client.post("/subscriptions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Netflix Test"
    assert data["next_billing_date"] == "2026-07-27"  # חישוב התאריך האוטומטי

# 2. טסט שמוודא שאי אפשר להכניס מנוי כפול באותו שם
def test_create_duplicate_subscription(client: TestClient):
    payload = {
        "name": "Spotify Duplicate",
        "price": 19.90,
        "currency": "ILS",
        "category": "entertainment",
        "billing_cycle": "monthly",
        "status": "active",
        "purchase_date": "2026-06-27"
    }
    # פעם ראשונה - מצליח
    client.post("/subscriptions", json=payload)
    # פעם שנייה - נחסם
    response = client.post("/subscriptions", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Subscription already exists"

# 3. טסט למחיקת מנוי מהמערכת
def test_delete_subscription(client: TestClient):
    from app.auth import create_access_token
    
    payload = {
        "name": "To Be Deleted",
        "price": 10.0,
        "currency": "EUR",
        "category": "other",
        "billing_cycle": "weekly",
        "status": "active",
        "purchase_date": "2026-06-27"
    }
    client.post("/subscriptions", json=payload)
    
    admin_token = create_access_token({"sub": "admin", "role": "admin"})
    response = client.delete(
        "/subscriptions/To Be Deleted",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Deleted successfully"

def _seed_subscription(session: Session, name: str, **overrides) -> Subscription:
    """Insert a subscription directly for summary/filter edge-case coverage."""
    fields = {
        "name": name,
        "price": 0.0,
        "currency": "ILS",
        "category": "other",
        "billing_cycle": "monthly",
        "status": "active",
        "purchase_date": date.today(),
        "next_billing_date": None,
    }
    fields.update(overrides)
    sub = Subscription(**fields)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


# 4. EX3 enhancement — /subscriptions/summary burn-rate math and DB filtering
def test_summary_burn_rate_and_filtering(client: TestClient, session: Session):
    today = date.today()

    # Included in burn-rate and active count
    _seed_subscription(session, "Summary Monthly ILS", price=100.0, currency="ILS", billing_cycle="monthly")
    _seed_subscription(session, "Summary Monthly USD", price=10.0, currency="USD", billing_cycle="monthly")
    _seed_subscription(session, "Summary Yearly EUR", price=120.0, currency="EUR", billing_cycle="yearly")
    _seed_subscription(session, "Summary Weekly ILS", price=10.0, currency="ILS", billing_cycle="weekly")
    _seed_subscription(
        session,
        "Summary One Time Recent",
        price=50.0,
        currency="ILS",
        billing_cycle="one_time",
        purchase_date=today,
        next_billing_date="None",
    )

    # Excluded by status, future date, or one-time window rules
    _seed_subscription(session, "Summary Paused", price=999.0, status="paused")
    _seed_subscription(session, "Summary Canceled", price=888.0, status="canceled")
    _seed_subscription(
        session,
        "Summary Future 2035",
        price=500.0,
        purchase_date=date(2035, 1, 1),
    )
    _seed_subscription(
        session,
        "Summary One Time Old",
        price=200.0,
        billing_cycle="one_time",
        purchase_date=today - timedelta(days=31),
        next_billing_date="None",
    )
    _seed_subscription(
        session,
        "Summary One Time Future",
        price=300.0,
        billing_cycle="one_time",
        purchase_date=today + timedelta(days=10),
        next_billing_date="None",
    )

    expected_burn = (
        100.0
        + 10.0 * EXCHANGE_RATES["USD"]
        + 120.0 * EXCHANGE_RATES["EUR"] / 12
        + 10.0 * 4.33
        + 50.0
    )
    expected_active_count = 5

    response = client.get("/subscriptions/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["monthly_burn_rate_ils"] == round(expected_burn, 2)
    assert data["active_subscriptions"] == expected_active_count
