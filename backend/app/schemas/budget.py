import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

class BudgetBase(BaseModel):
    category_id: uuid.UUID
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=2020, le=2100, description="Year")
    amount_paise: int = Field(..., gt=0, description="Monthly spending limit in integer paise")
    alert_threshold: float = Field(default=0.80, ge=0.01, le=2.0)

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount_paise: Optional[int] = Field(default=None, gt=0)
    alert_threshold: Optional[float] = Field(default=None, ge=0.01, le=2.0)

class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    month: int
    year: int
    amount_paise: int
    alert_threshold: float
    spent_paise: int = 0
    remaining_paise: int = 0
    pacing_pct: float = 0.0
    alert_status: str = "NORMAL"  # NORMAL, WARNING, EXCEEDED
    created_at: datetime
    updated_at: datetime

    @computed_field
    def amount_inr(self) -> float:
        return round(self.amount_paise / 100.0, 2)

    @computed_field
    def spent_inr(self) -> float:
        return round(self.spent_paise / 100.0, 2)

    @computed_field
    def remaining_inr(self) -> float:
        return round(self.remaining_paise / 100.0, 2)
