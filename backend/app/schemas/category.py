import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    slug: str = Field(..., min_length=2, max_length=80)
    icon: str = Field(default="tag", max_length=50)
    color: str = Field(default="#64748b", max_length=20)
    is_income: bool = Field(default=False)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_system: bool
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
