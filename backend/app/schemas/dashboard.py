import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.transaction import TransactionResponse

class CashflowTrendItem(BaseModel):
    month: str
    income_paise: int
    expenses_paise: int
    net_paise: int
    income_inr: float
    expenses_inr: float
    net_inr: float

class CategorySpendItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    category_color: str
    spent_paise: int
    spent_inr: float
    percentage: float

class DashboardSummaryResponse(BaseModel):
    period: str
    total_income_paise: int
    total_income_inr: float
    total_expenses_paise: int
    total_expenses_inr: float
    net_savings_paise: int
    net_savings_inr: float
    savings_rate: float
    total_liquid_balance_paise: int
    total_liquid_balance_inr: float
    total_debt_balance_paise: int
    total_debt_balance_inr: float
    accounts_count: int
    transactions_count: int
    health_score: int
    health_grade: str
    recent_transactions: List[TransactionResponse]
