import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    insight_type: str
    severity: str
    title: str
    description: str
    metadata_json: Optional[str] = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
