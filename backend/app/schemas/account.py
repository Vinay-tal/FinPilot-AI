import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

class AccountBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(default="SAVINGS", description="SAVINGS, CURRENT, CREDIT_CARD, INVESTMENT, WALLET")
    institution: str = Field(..., min_length=2, max_length=100)
    account_number_mask: Optional[str] = Field(default=None, max_length=20)
    currency: str = Field(default="INR", max_length=10)

class AccountCreate(AccountBase):
    balance_paise: int = Field(default=0, description="Opening balance in integer paise (1 INR = 100 paise)")

class AccountUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    account_type: Optional[str] = None
    institution: Optional[str] = None
    account_number_mask: Optional[str] = None
    balance_paise: Optional[int] = None
    is_active: Optional[bool] = None

class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    balance_paise: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    def balance_inr(self) -> float:
        """Convert integer paise to standard Rupee floating point for UI presentation."""
        return round(self.balance_paise / 100.0, 2)
