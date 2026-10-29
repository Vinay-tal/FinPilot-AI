import json
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.copilot_service import (
    list_conversations,
    create_conversation,
    rename_conversation,
    delete_conversation,
    get_conversation_messages,
    process_copilot_turn,
    get_or_create_default_conversation,
)

router = APIRouter(prefix="/copilot", tags=["AI Financial Copilot"])

# ============================================================================
# Request / Response Schemas
# ============================================================================

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Optional title for new session")

class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="New title")

class SendMessageRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Financial question or instruction")

class CitationDTO(BaseModel):
    source: str
    title: str
    value: str
    detail: str

class FactsVsEstimatesDTO(BaseModel):
    retrieved_facts: List[str] = Field(default_factory=list)
    model_estimates: List[str] = Field(default_factory=list)
    hypothetical_scenarios: List[str] = Field(default_factory=list)

class CopilotTurnResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    provider_used: str
    citations: List[CitationDTO] = Field(default_factory=list)
    facts_vs_estimates: FactsVsEstimatesDTO = Field(default_factory=FactsVsEstimatesDTO)
    scenario_card: Optional[Dict[str, Any]] = None
    suggested_followups: List[str] = Field(default_factory=list)

class ConversationItemDTO(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    last_message_preview: str

class MessageItemDTO(BaseModel):
    id: str
    role: str
    content: str
    provider_used: str
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: str

# Legacy Schemas
class LegacyQueryRequest(BaseModel):
    query: str

class LegacyCopilotResponse(BaseModel):
    answer: str
    provider_used: str
    citations: Dict[str, Any]
    suggested_followups: List[str]

# ============================================================================
# Conversation Endpoints
# ============================================================================

@router.get("/conversations", response_model=List[ConversationItemDTO])
def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ConversationItemDTO]:
    """Retrieve all conversations for authenticated user."""
    return [ConversationItemDTO(**c) for c in list_conversations(db, current_user.id)]

@router.post("/conversations", response_model=ConversationItemDTO, status_code=status.HTTP_201_CREATED)
def start_new_conversation(
    req: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationItemDTO:
    """Create a new conversational session."""
    conv = create_conversation(db, current_user.id, title=req.title)
    db.commit()
    return ConversationItemDTO(
        id=str(conv.id),
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        message_count=1,
        last_message_preview="New conversation created",
    )

@router.patch("/conversations/{conversation_id}", response_model=ConversationItemDTO)
def update_conversation_title(
    conversation_id: uuid.UUID,
    req: RenameConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationItemDTO:
    """Rename a conversation title."""
    try:
        conv = rename_conversation(db, current_user.id, conversation_id, req.title)
        db.commit()
        return ConversationItemDTO(
            id=str(conv.id),
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            message_count=len(conv.messages),
            last_message_preview=conv.messages[-1].content[:80] if conv.messages else "",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and its turns."""
    deleted = delete_conversation(db, current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found or unauthorized.")
    db.commit()
    return None

# ============================================================================
# Messages & Chat Turns
# ============================================================================

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageItemDTO])
def get_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MessageItemDTO]:
    """Retrieve full message history for a conversation."""
    try:
        messages = get_conversation_messages(db, current_user.id, conversation_id)
        result = []
        for m in messages:
            cits = None
            if m.citations_json:
                try:
                    cits = json.loads(m.citations_json)
                except Exception:
                    pass
            result.append(
                MessageItemDTO(
                    id=str(m.id),
                    role=m.role,
                    content=m.content,
                    provider_used=m.provider_used,
                    citations=cits,
                    created_at=m.created_at.strftime("%I:%M %p"),
                )
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/conversations/{conversation_id}/messages", response_model=CopilotTurnResponse)
def send_message(
    conversation_id: uuid.UUID,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotTurnResponse:
    """Send a financial question within a conversation and receive grounded response."""
    try:
        res = process_copilot_turn(db, current_user.id, conversation_id, req.query)
        db.commit()
        return CopilotTurnResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Copilot reasoning failed: {str(e)}")

@router.get("/conversations/{conversation_id}/messages/stream")
def stream_copilot_response(
    conversation_id: uuid.UUID,
    query: str = Query(..., description="Financial question"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Server-Sent Events (SSE) streaming endpoint for real-time tokens."""
    try:
        turn_data = process_copilot_turn(db, current_user.id, conversation_id, query)
        db.commit()

        def event_generator():
            full_text = turn_data["answer"]
            words = full_text.split(" ")
            for i in range(0, len(words), 2):
                chunk = " ".join(words[i : i + 2]) + " "
                payload = json.dumps({"type": "chunk", "content": chunk})
                yield f"data: {payload}\n\n"

            # Final complete metadata event
            final_payload = json.dumps({
                "type": "done",
                "data": turn_data,
            })
            yield f"data: {final_payload}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Legacy Backwards-Compatible Endpoints
# ============================================================================

@router.get("/history", response_model=List[MessageItemDTO])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MessageItemDTO]:
    """Retrieve chat history of default conversation (backwards compatible)."""
    conv = get_or_create_default_conversation(db, current_user.id)
    db.commit()
    return get_messages(conv.id, current_user, db)

@router.post("/query", response_model=LegacyCopilotResponse)
def ask_copilot_legacy(
    req: LegacyQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegacyCopilotResponse:
    """Legacy query endpoint routed to copilot service."""
    conv = get_or_create_default_conversation(db, current_user.id)
    turn_res = process_copilot_turn(db, current_user.id, conv.id, req.query)
    db.commit()

    # Format citations as dictionary for legacy UI compatibility
    citations_dict = {}
    for c in turn_res.get("citations", []):
        citations_dict[c.get("title", "Metric")] = c.get("value", "")

    return LegacyCopilotResponse(
        answer=turn_res["answer"],
        provider_used=turn_res["provider_used"],
        citations=citations_dict,
        suggested_followups=turn_res["suggested_followups"],
    )
