"""Data access for conversations, messages, and feedback."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.audit import RestoreRequest
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


class PendingRestoreRequestError(ValueError):
    """Raised when a conversation already has a pending restore request."""


def get_or_create_conversation(
    db: Session,
    conversation_id: str | None,
    title_hint: str,
    user_id: str | None = None,
) -> Conversation:
    if conversation_id is not None:
        conv = get_conversation(db, conversation_id, user_id=user_id)
        if conv:
            return conv
        raise ConversationNotFoundError(conversation_id)
    title = (title_hint[:60] + "...") if len(title_hint) > 60 else title_hint
    # New conversations stay transient until the complete answer is ready.
    # This prevents a failed provider call from leaving an empty conversation.
    return Conversation(title=title or "New conversation", user_id=user_id)


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
            persisted = get_conversation(db, conversation.id, user_id=conversation.user_id)
            if persisted is None:
                raise ConversationNotFoundError(conversation.id)
        else:
            persisted = Conversation(
                title=conversation.title or "New conversation",
                user_id=conversation.user_id,
            )
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


def list_conversations(db: Session, user_id: str | None = None) -> list[Conversation]:
    query = db.query(Conversation).filter(Conversation.is_deleted.is_(False))
    if user_id is not None:
        query = query.filter(Conversation.user_id == user_id)
    return query.order_by(Conversation.created_at.desc()).all()


def get_conversation(
    db: Session,
    conversation_id: str,
    user_id: str | None = None,
    *,
    include_deleted: bool = False,
) -> Conversation | None:
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if user_id is not None:
        query = query.filter(Conversation.user_id == user_id)
    if not include_deleted:
        query = query.filter(Conversation.is_deleted.is_(False))
    return query.first()


def get_conversation_any_owner(db: Session, conversation_id: str) -> Conversation | None:
    return get_conversation(db, conversation_id, include_deleted=True)


def get_message(db: Session, message_id: str, user_id: str | None = None) -> Message | None:
    query = db.query(Message).join(Conversation).filter(Message.id == message_id)
    if user_id is not None:
        query = query.filter(
            Conversation.user_id == user_id,
            Conversation.is_deleted.is_(False),
        )
    return query.first()


def hard_delete_conversation(db: Session, conv: Conversation) -> None:
    db.delete(conv)
    db.commit()


def delete_conversation(db: Session, conv: Conversation) -> None:
    """Backward-compatible alias for operator-only permanent deletion."""
    hard_delete_conversation(db, conv)


def soft_delete_conversation(db: Session, conv: Conversation, deleted_by_user_id: str) -> None:
    conv.is_deleted = True
    conv.deleted_at = datetime.now(timezone.utc)
    conv.deleted_by = deleted_by_user_id
    db.commit()


def restore_conversation(db: Session, conv: Conversation) -> None:
    conv.is_deleted = False
    conv.deleted_at = None
    conv.deleted_by = None
    db.commit()


def list_deleted_conversations_for_user(db: Session, user_id: str) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.is_deleted.is_(True))
        .order_by(Conversation.deleted_at.desc())
        .all()
    )


def list_all_conversations_admin(
    db: Session,
    include_deleted: bool = True,
    owner_id: str | None = None,
) -> list[Conversation]:
    query = db.query(Conversation)
    if owner_id:
        query = query.filter(Conversation.user_id == owner_id)
    if not include_deleted:
        query = query.filter(Conversation.is_deleted.is_(False))
    return query.order_by(Conversation.created_at.desc()).all()


def add_feedback(
    db: Session,
    message_id: str,
    rating: int,
    comment: str | None,
    user_id: str | None = None,
) -> Feedback:
    try:
        message = get_message(db, message_id, user_id=user_id)
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
            if get_message(db, message_id, user_id=user_id) is None:
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


def create_restore_request(
    db: Session,
    conversation_id: str,
    requested_by: str,
    reason: str,
) -> RestoreRequest:
    existing = (
        db.query(RestoreRequest)
        .filter(
            RestoreRequest.conversation_id == conversation_id,
            RestoreRequest.requested_by == requested_by,
            RestoreRequest.status == "PENDING",
        )
        .first()
    )
    if existing:
        raise PendingRestoreRequestError(conversation_id)
    request = RestoreRequest(
        conversation_id=conversation_id,
        requested_by=requested_by,
        reason=reason,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_restore_requests(db: Session, status: str | None = None) -> list[RestoreRequest]:
    query = db.query(RestoreRequest)
    if status:
        query = query.filter(RestoreRequest.status == status)
    return query.order_by(RestoreRequest.requested_at.desc()).all()


def list_restore_requests_for_user(db: Session, user_id: str) -> list[RestoreRequest]:
    return (
        db.query(RestoreRequest)
        .filter(RestoreRequest.requested_by == user_id)
        .order_by(RestoreRequest.requested_at.desc())
        .all()
    )


def get_restore_request(db: Session, request_id: str) -> RestoreRequest | None:
    return db.query(RestoreRequest).filter(RestoreRequest.id == request_id).first()


def resolve_restore_request(
    db: Session,
    request: RestoreRequest,
    approve: bool,
    resolved_by: str,
    resolution_reason: str | None,
) -> None:
    request.status = "APPROVED" if approve else "REJECTED"
    request.resolved_by = resolved_by
    request.resolution_reason = resolution_reason
    request.resolved_at = datetime.now(timezone.utc)
    db.commit()
