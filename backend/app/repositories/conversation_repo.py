"""Data access for conversations, messages, and feedback."""
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message, Feedback


def get_or_create_conversation(db: Session, conversation_id: str | None, title_hint: str) -> Conversation:
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            return conv
    title = (title_hint[:60] + "...") if len(title_hint) > 60 else title_hint
    conv = Conversation(title=title or "New conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def add_message(
    db: Session, conversation_id: str, role: str, content: str, sources: list | None = None, debug_trace: dict | None = None
) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content, sources=sources, debug_trace=debug_trace)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_conversations(db: Session) -> list[Conversation]:
    return db.query(Conversation).order_by(Conversation.created_at.desc()).all()


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def delete_conversation(db: Session, conv: Conversation) -> None:
    db.delete(conv)
    db.commit()


def add_feedback(db: Session, message_id: str, rating: int, comment: str | None) -> Feedback:
    fb = Feedback(message_id=message_id, rating=rating, comment=comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
