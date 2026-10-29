import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

class TransactionBase(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID
    date: date
    amount_paise: int = Field(..., gt=0, description="Strictly positive amount in integer paise")
    transaction_type: str = Field(default="DEBIT", description="DEBIT or CREDIT")
    narration: str = Field(..., min_length=2, max_length=500)
    raw_narration: Optional[str] = Field(default=None, max_length=1000)
    merchant_name: Optional[str] = Field(default=None, max_length=150)
    payment_mode: str = Field(default="UPI", max_length=30)
    reference_id: Optional[str] = Field(default=None, max_length=100)

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    date: Optional[date] = None
    amount_paise: Optional[int] = Field(default=None, gt=0)
    transaction_type: Optional[str] = None
    narration: Optional[str] = None
    merchant_name: Optional[str] = None
    payment_mode: Optional[str] = None
    reference_id: Optional[str] = None
    is_recurring: Optional[bool] = None

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    account_name: Optional[str] = None
    date: date
    amount_paise: int
    transaction_type: str
    narration: str
    raw_narration: Optional[str] = None
    merchant_name: Optional[str] = None
    payment_mode: str
    reference_id: Optional[str] = None
    is_recurring: bool
    fingerprint: str
    categorization_method: str
    categorization_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    def amount_inr(self) -> float:
        """Present value in Indian Rupees."""
        return round(self.amount_paise / 100.0, 2)
