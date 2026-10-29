import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

class RecurringBase(BaseModel):
    category_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=150)
    merchant_name: str = Field(..., min_length=2, max_length=150)
    expected_amount_paise: int = Field(..., gt=0)
    frequency: str = Field(default="MONTHLY")
    next_expected_date: date

class RecurringCreate(RecurringBase):
    pass

class RecurringResponse(RecurringBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    last_detected_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    def expected_amount_inr(self) -> float:
        return round(self.expected_amount_paise / 100.0, 2)
