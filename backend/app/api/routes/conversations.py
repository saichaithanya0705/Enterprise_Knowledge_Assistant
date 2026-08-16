"""Authenticated conversation history, deletion, and recovery endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.repositories import audit_repo, conversation_repo
from app.repositories.conversation_repo import PendingRestoreRequestError
from app.schemas.chat import (
    ConversationOut,
    DebugTrace,
    MessageOut,
    RestoreRequestCreate,
    RestoreRequestOut,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


def _safe_debug_trace(message_id: str, raw_debug: object) -> DebugTrace | None:
    if raw_debug is None:
        return None
    try:
        return DebugTrace.model_validate(raw_debug)
    except ValidationError:
        logger.warning(
            "Ignoring invalid persisted debug trace message_id=%s value_type=%s",
            message_id,
            type(raw_debug).__name__,
        )
        return None


def _restore_request_out(request, conversation_title: str | None = None) -> RestoreRequestOut:
    return RestoreRequestOut(
        id=request.id,
        conversation_id=request.conversation_id,
        conversation_title=conversation_title,
        requested_by=request.requested_by,
        reason=request.reason,
        status=request.status,
        resolved_by=request.resolved_by,
        resolution_reason=request.resolution_reason,
        requested_at=request.requested_at.isoformat(),
        resolved_at=request.resolved_at.isoformat() if request.resolved_at else None,
    )


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversations = conversation_repo.list_conversations(db, user_id=current_user.id)
    return [
        ConversationOut(
            id=item.id,
            title=item.title,
            created_at=item.created_at.isoformat(),
            deleted_at=item.deleted_at.isoformat() if item.deleted_at else None,
        )
        for item in conversations
    ]


@router.get("/deleted", response_model=list[ConversationOut])
def list_deleted_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversations = conversation_repo.list_deleted_conversations_for_user(db, current_user.id)
    return [
        ConversationOut(
            id=item.id,
            title=item.title,
            created_at=item.created_at.isoformat(),
            deleted_at=item.deleted_at.isoformat() if item.deleted_at else None,
        )
        for item in conversations
    ]


@router.get("/restore-requests/mine", response_model=list[RestoreRequestOut])
def list_my_restore_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output = []
    for request in conversation_repo.list_restore_requests_for_user(db, current_user.id):
        conversation = conversation_repo.get_conversation_any_owner(db, request.conversation_id)
        output.append(_restore_request_out(request, conversation.title if conversation else None))
    return output


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = conversation_repo.get_conversation(db, conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    is_admin = current_user.role == "ADMIN"
    return [
        MessageOut(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=message.sources if is_admin else [
                {key: value for key, value in source.items() if key != "excerpt"}
                for source in (message.sources or [])
            ],
            debug=_safe_debug_trace(message.id, message.debug_trace) if is_admin else None,
            created_at=message.created_at.isoformat(),
        )
        for message in conversation.messages
    ]


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = conversation_repo.get_conversation(db, conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    conversation_repo.soft_delete_conversation(db, conversation, current_user.id)
    audit_repo.log_action(
        db,
        current_user,
        "CONVERSATION_DELETE",
        target_type="conversation",
        target_id=conversation.id,
    )


@router.post(
    "/{conversation_id}/restore-requests",
    response_model=RestoreRequestOut,
    status_code=201,
)
def request_restore(
    conversation_id: str,
    payload: RestoreRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = conversation_repo.get_conversation_any_owner(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(404, "Conversation not found")
    if not conversation.is_deleted:
        raise HTTPException(400, "Only deleted conversations can be restored.")
    try:
        request = conversation_repo.create_restore_request(
            db,
            conversation_id,
            current_user.id,
            payload.reason,
        )
    except PendingRestoreRequestError:
        raise HTTPException(409, "A restore request is already pending for this conversation.")
    audit_repo.log_action(
        db,
        current_user,
        "RESTORE_REQUEST_SUBMIT",
        target_type="conversation",
        target_id=conversation.id,
    )
    return _restore_request_out(request, conversation.title)
