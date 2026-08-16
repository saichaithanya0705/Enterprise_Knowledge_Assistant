"""Chat / RAG query endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation, message, answer, sources, debug_trace, grounded = await answer_question(
            db, payload.conversation_id, payload.message
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Failed to generate a response: {e}")

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        sources=sources,
        debug=debug_trace,
        grounded=grounded,
    )
