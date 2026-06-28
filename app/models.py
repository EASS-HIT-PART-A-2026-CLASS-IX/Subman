from datetime import date
from typing import Optional

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=2, index=True, unique=True)
    price: float = Field(ge=0)
    currency: str = "ILS"
    category: str = "other"
    billing_cycle: str = "monthly"
    status: str = "active"
    purchase_date: date = Field(default_factory=date.today)
    next_billing_date: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value < 0:
            raise ValueError("עלות המנוי חייבת להיות אי-שלילית")
        return value

    @field_validator("next_billing_date")
    @classmethod
    def check_next_billing_not_in_past(cls, value: Optional[str]) -> Optional[str]:
        if value and value != "None":
            parsed = date.fromisoformat(value)
            if parsed < date.today():
                raise ValueError("תאריך החיוב הבא לא יכול להיות בעבר")
        return value
