"""Data access for conversations, messages, and feedback."""
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message, Feedback


class ConversationNotFoundError(LookupError):
    """Raised when a caller references a conversation that does not exist."""


class MessageNotFoundError(LookupError):
    """Raised when feedback targets a message deleted before insertion."""


class InvalidFeedbackMessageError(ValueError):
    """Raised when feedback targets a non-assistant message."""


class DuplicateFeedbackError(ValueError):
    """Raised when feedback already exists for an assistant message."""


class FeedbackPersistenceError(RuntimeError):
    """Raised when feedback cannot be persisted safely."""


def get_or_create_conversation(db: Session, conversation_id: str | None, title_hint: str) -> Conversation:
    if conversation_id is not None:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            return conv
        raise ConversationNotFoundError(conversation_id)
    title = (title_hint[:60] + "...") if len(title_hint) > 60 else title_hint
    # New conversations stay transient until the complete answer is ready.
    # This prevents a failed provider call from leaving an empty conversation.
    return Conversation(title=title or "New conversation")


def add_turn(
    db: Session,
    conversation: Conversation,
    question: str,
    answer: str,
    sources: list | None = None,
    debug_trace: dict | None = None,
) -> tuple[Conversation, Message]:
    """Persist a user/assistant turn in one transaction after generation succeeds."""
    try:
        if conversation.id:
            persisted = get_conversation(db, conversation.id)
            if persisted is None:
                raise ConversationNotFoundError(conversation.id)
        else:
            persisted = Conversation(title=conversation.title or "New conversation")
            db.add(persisted)
            db.flush()

        user_message = Message(
            conversation_id=persisted.id,
            role="user",
            content=question,
        )
        assistant_message = Message(
            conversation_id=persisted.id,
            role="assistant",
            content=answer,
            sources=sources,
            debug_trace=debug_trace,
        )
        db.add_all([user_message, assistant_message])
        db.commit()
        db.refresh(assistant_message)
        return persisted, assistant_message
    except Exception:
        db.rollback()
        raise


def list_conversations(db: Session) -> list[Conversation]:
    return db.query(Conversation).order_by(Conversation.created_at.desc()).all()


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_message(db: Session, message_id: str) -> Message | None:
    return db.query(Message).filter(Message.id == message_id).first()


def delete_conversation(db: Session, conv: Conversation) -> None:
    db.delete(conv)
    db.commit()


def add_feedback(db: Session, message_id: str, rating: int, comment: str | None) -> Feedback:
    try:
        message = get_message(db, message_id)
        if message is None:
            raise MessageNotFoundError(message_id)
        if message.role != "assistant":
            raise InvalidFeedbackMessageError(message_id)
        if db.query(Feedback).filter(Feedback.message_id == message_id).first() is not None:
            raise DuplicateFeedbackError(message_id)

        fb = Feedback(message_id=message_id, rating=rating, comment=comment)
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return fb
    except (MessageNotFoundError, InvalidFeedbackMessageError, DuplicateFeedbackError):
        db.rollback()
        raise
    except IntegrityError:
        # The target or an identical feedback row may have changed after the
        # preflight checks. Re-read only after rollback, then expose a typed,
        # sanitized outcome to the API layer.
        db.rollback()
        try:
            if get_message(db, message_id) is None:
                raise MessageNotFoundError(message_id)
            if db.query(Feedback).filter(Feedback.message_id == message_id).first() is not None:
                raise DuplicateFeedbackError(message_id)
        except (MessageNotFoundError, DuplicateFeedbackError):
            raise
        except SQLAlchemyError as error:
            db.rollback()
            raise FeedbackPersistenceError from error
        raise FeedbackPersistenceError
    except SQLAlchemyError as error:
        db.rollback()
        raise FeedbackPersistenceError from error
