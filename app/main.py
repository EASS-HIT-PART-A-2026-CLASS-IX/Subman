from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from urllib.parse import unquote

app = FastAPI()

# מילון המרות מטבע (שערי חליפין לדוגמה)
EXCHANGE_RATES = {
    "ILS": 1.0,
    "USD": 3.7,
    "EUR": 4.0
}

class Subscription(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    currency: str
    category: str
    billing_cycle: str
    status: str

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be just whitespace')
        return v.strip()

subscriptions = []

@app.get("/subscriptions")
def get_subscriptions():
    return subscriptions

@app.post("/subscriptions", status_code=status.HTTP_201_CREATED)
def create_subscription(sub: Subscription):
    if any(s["name"].lower() == sub.name.lower() for s in subscriptions):
        raise HTTPException(status_code=400, detail="Subscription already exists")
    
    # שימוש בסינטקס המעודכן של Pydantic V2
    new_sub = sub.model_dump()
    subscriptions.append(new_sub)
    return new_sub

@app.delete("/subscriptions/{name}")
def delete_subscription(name: str):
    global subscriptions
    decoded_name = unquote(name).strip().lower()
    
    initial_count = len(subscriptions)
    subscriptions = [s for s in subscriptions if s["name"].lower() != decoded_name]
    
    if len(subscriptions) < initial_count:
        return {"message": "Deleted successfully"}
    
    raise HTTPException(status_code=404, detail=f"Subscription '{decoded_name}' not found")

@app.get("/subscriptions/summary")
def get_summary():
    active_subs = [s for s in subscriptions if s["status"] == "active"]
    
    total_ils = 0.0
    for s in active_subs:
        rate = EXCHANGE_RATES.get(s["currency"].upper(), 1.0)
        total_ils += s["price"] * rate

    return {
        "monthly_burn_rate_ils": total_ils,
        "active_subscriptions": len(active_subs)
    }