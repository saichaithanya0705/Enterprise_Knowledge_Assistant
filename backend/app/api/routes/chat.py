"""Chat / RAG query endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import answer_question
from app.repositories.conversation_repo import ConversationNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, response_model_exclude_none=True)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        conversation, message, answer, sources, debug_trace, grounded = await answer_question(
            db, payload.conversation_id, payload.message, user_id=current_user.id
        )
    except ConversationNotFoundError:
        raise HTTPException(404, "Conversation not found")
    except Exception:  # noqa: BLE001
        raise HTTPException(500, "Failed to generate a response.")

    safe_sources = sources if current_user.role == "ADMIN" else [
        {key: value for key, value in source.items() if key != "excerpt"}
        for source in sources
    ]
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        sources=safe_sources,
        debug=debug_trace if current_user.role == "ADMIN" else None,
        grounded=grounded,
    )
