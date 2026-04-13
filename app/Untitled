from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
from enum import Enum

class CycleEnum(str, Enum):
    monthly = "monthly"
    yearly = "yearly"
    weekly = "weekly"

class StatusEnum(str, Enum):
    active = "active"
    paused = "paused"
    canceled = "canceled"

class CurrencyEnum(str, Enum):
    ILS = "ILS"
    USD = "USD"
    EUR = "EUR"

class CategoryEnum(str, Enum):
    entertainment = "entertainment"
    software = "software"
    health = "health"
    utilities = "utilities"
    other = "other"

class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=2, description="שם המנוי")
    price: float = Field(..., ge=0, description="עלות המנוי")
    currency: CurrencyEnum = CurrencyEnum.ILS
    billing_cycle: CycleEnum = CycleEnum.monthly
    category: CategoryEnum = CategoryEnum.other
    status: StatusEnum = StatusEnum.active
    next_billing_date: Optional[date] = None

class SubscriptionCreate(SubscriptionBase):
    @field_validator('next_billing_date')
    @classmethod
    def check_date_not_in_past(cls, value):
        if value and value < date.today():
            raise ValueError("תאריך החיוב הבא לא יכול להיות בעבר")
        return value

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[CurrencyEnum] = None
    billing_cycle: Optional[CycleEnum] = None
    category: Optional[CategoryEnum] = None
    status: Optional[StatusEnum] = None
    next_billing_date: Optional[date] = None

class SubscriptionResponse(SubscriptionBase):
    id: str