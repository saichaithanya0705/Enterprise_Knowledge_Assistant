"""Conversation history endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import conversation_repo
from app.schemas.chat import ConversationOut, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    convs = conversation_repo.list_conversations(db)
    return [ConversationOut(id=c.id, title=c.title, created_at=c.created_at.isoformat()) for c in convs]


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    conv = conversation_repo.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return [
        MessageOut(id=m.id, role=m.role, content=m.content, sources=m.sources, created_at=m.created_at.isoformat())
        for m in conv.messages
    ]


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = conversation_repo.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    conversation_repo.delete_conversation(db, conv)
