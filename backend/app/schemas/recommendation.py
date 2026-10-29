import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    recommendation_type: str
    title: str
    explanation: str
    data_period: str
    estimated_impact_inr: float
    impact_assumptions: str
    confidence: str
    suggested_action: str
    action_type: Optional[str] = None
    action_payload_json: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

class RecommendationStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status: new, accepted, dismissed, completed")

class RecommendationApplyResponse(BaseModel):
    success: bool
    message: str
    applied_action: str
    recommendation: RecommendationResponse
