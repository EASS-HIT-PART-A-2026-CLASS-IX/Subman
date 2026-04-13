from fastapi import FastAPI, HTTPException, status
from typing import List, Dict
import uuid

# ייבוא המודלים שלנו מהקובץ השני (שימוש בנקודה לייבוא יחסי באותה תיקייה)
from .models import SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate

app = FastAPI(title="SubMan API", description="Subscription Manager Backend for EX1")

# בסיס הנתונים שלנו בזיכרון (In-Memory Database)
db: Dict[str, SubscriptionResponse] = {}

@app.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(sub: SubscriptionCreate):
    sub_id = str(uuid.uuid4())
    new_sub = SubscriptionResponse(id=sub_id, **sub.model_dump())
    db[sub_id] = new_sub
    return new_sub

@app.get("/subscriptions", response_model=List[SubscriptionResponse])
def get_subscriptions():
    return list(db.values())

@app.get("/subscriptions/summary")
def get_summary():
    """נקודת קצה ייחודית המחשבת את קצב שריפת המזומנים החודשי"""
    total_monthly = 0.0
    active_count = 0
    
    for sub in db.values():
        if sub.status.value != "active":
            continue
            
        active_count += 1
        # המרה לחישוב חודשי לפי מסלול החיוב
        if sub.billing_cycle.value == "monthly":
            total_monthly += sub.price
        elif sub.billing_cycle.value == "yearly":
            total_monthly += sub.price / 12
        elif sub.billing_cycle.value == "weekly":
            total_monthly += sub.price * 4.33 # בערך 4.33 שבועות בחודש
            
    return {
        "active_subscriptions": active_count, 
        "monthly_burn_rate_ils": round(total_monthly, 2)
    }

@app.get("/subscriptions/{sub_id}", response_model=SubscriptionResponse)
def get_subscription(sub_id: str):
    if sub_id not in db:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return db[sub_id]

@app.put("/subscriptions/{sub_id}", response_model=SubscriptionResponse)
def update_subscription(sub_id: str, sub_update: SubscriptionUpdate):
    if sub_id not in db:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    existing_sub = db[sub_id]
    update_data = sub_update.model_dump(exclude_unset=True)
    updated_sub = existing_sub.model_copy(update=update_data)
    db[sub_id] = updated_sub
    return updated_sub

@app.delete("/subscriptions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(sub_id: str):
    if sub_id not in db:
        raise HTTPException(status_code=404, detail="Subscription not found")
    del db[sub_id]
    return None