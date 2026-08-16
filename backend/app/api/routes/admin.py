"""Admin-only user, conversation recovery, audit, and analytics endpoints."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_admin
from app.db.database import get_db
from app.models.audit import RestoreRequest
from app.models.conversation import Conversation, Feedback, Message
from app.models.document import Document
from app.models.user import User
from app.repositories import audit_repo, conversation_repo, user_repo
from app.schemas.auth import UserOut
from app.schemas.chat import (
    AdminMessageOut,
    DebugTrace,
    RestoreRequestOut,
    RestoreRequestResolve,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def _iso(value):
    return value.isoformat() if value else None


def _user_out(user: User) -> UserOut:
    """Project a user without ever serializing the password hash."""
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login_at=_iso(user.last_login_at),
    )


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


def _restore_request_out(
    request,
    conversation_title: str | None = None,
    requester_email: str | None = None,
) -> RestoreRequestOut:
    return RestoreRequestOut(
        id=request.id,
        conversation_id=request.conversation_id,
        conversation_title=conversation_title,
        requested_by=request.requested_by,
        requester_email=requester_email,
        reason=request.reason,
        status=request.status,
        resolved_by=request.resolved_by,
        resolution_reason=request.resolution_reason,
        requested_at=request.requested_at.isoformat(),
        resolved_at=_iso(request.resolved_at),
    )


class SetActiveRequest(BaseModel):
    is_active: bool


class SetRoleRequest(BaseModel):
    role: str


class AdminConversationOut(BaseModel):
    id: str
    title: str
    owner_id: str | None
    owner_email: str | None
    created_at: str
    is_deleted: bool
    deleted_at: str | None
    deleted_by: str | None


class AuditLogOut(BaseModel):
    id: str
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    status: str
    created_at: str


def _ensure_not_last_active_admin(db: Session, user: User) -> None:
    if user.role == "ADMIN" and user.is_active and user_repo.count_active_admins(db) <= 1:
        raise HTTPException(400, "You cannot remove the last active admin.")


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [_user_out(user) for user in user_repo.list_users(db)]


@router.patch("/users/{user_id}/active", status_code=204)
def set_user_active(
    user_id: str,
    payload: SetActiveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(400, "You cannot deactivate your own account.")
    if not payload.is_active:
        _ensure_not_last_active_admin(db, user)

    user_repo.set_active(db, user, payload.is_active)
    audit_repo.log_action(
        db,
        admin,
        "USER_STATUS_CHANGE",
        target_type="user",
        target_id=user.id,
        metadata={"is_active": payload.is_active},
    )


@router.patch("/users/{user_id}/role", status_code=204)
def set_user_role(
    user_id: str,
    payload: SetRoleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if payload.role not in ("USER", "ADMIN"):
        raise HTTPException(400, "Role must be USER or ADMIN.")

    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and payload.role != "ADMIN":
        raise HTTPException(400, "You cannot remove your own admin role.")
    if payload.role != "ADMIN":
        _ensure_not_last_active_admin(db, user)

    user_repo.set_role(db, user, payload.role)
    audit_repo.log_action(
        db,
        admin,
        "USER_ROLE_CHANGE",
        target_type="user",
        target_id=user.id,
        metadata={"role": payload.role},
    )


@router.get("/conversations", response_model=list[AdminConversationOut])
def list_all_conversations(
    include_deleted: bool = Query(True),
    owner_id: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conversations = conversation_repo.list_all_conversations_admin(
        db, include_deleted=include_deleted, owner_id=owner_id
    )
    result = []
    for conversation in conversations:
        owner = user_repo.get_by_id(db, conversation.user_id) if conversation.user_id else None
        result.append(
            AdminConversationOut(
                id=conversation.id,
                title=conversation.title,
                owner_id=conversation.user_id,
                owner_email=owner.email if owner else None,
                created_at=conversation.created_at.isoformat(),
                is_deleted=conversation.is_deleted,
                deleted_at=_iso(conversation.deleted_at),
                deleted_by=conversation.deleted_by,
            )
        )
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=list[AdminMessageOut])
def admin_get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conversation = conversation_repo.get_conversation_any_owner(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")

    return [
        AdminMessageOut(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=message.sources,
            debug=_safe_debug_trace(message.id, message.debug_trace),
            created_at=message.created_at.isoformat(),
        )
        for message in conversation.messages
    ]


@router.post("/conversations/{conversation_id}/restore", status_code=204)
def admin_restore_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conversation = conversation_repo.get_conversation_any_owner(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    conversation_repo.restore_conversation(db, conversation)
    audit_repo.log_action(
        db, admin, "CONVERSATION_RESTORE", target_type="conversation", target_id=conversation.id
    )


@router.delete("/conversations/{conversation_id}/permanent", status_code=204)
def admin_permanently_delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conversation = conversation_repo.get_conversation_any_owner(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    conversation_repo.hard_delete_conversation(db, conversation)
    audit_repo.log_action(
        db,
        admin,
        "CONVERSATION_PERMANENT_DELETE",
        target_type="conversation",
        target_id=conversation_id,
    )


@router.get("/restore-requests", response_model=list[RestoreRequestOut])
def list_restore_requests(
    status: Literal["PENDING", "APPROVED", "REJECTED"] | None = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    requests = conversation_repo.list_restore_requests(db, status=status)
    result = []
    for request in requests:
        conversation = conversation_repo.get_conversation_any_owner(db, request.conversation_id)
        requester = user_repo.get_by_id(db, request.requested_by)
        result.append(
            _restore_request_out(
                request,
                conversation.title if conversation else None,
                requester.email if requester else None,
            )
        )
    return result


@router.post("/restore-requests/{request_id}/resolve", status_code=204)
def resolve_restore_request(
    request_id: str,
    payload: RestoreRequestResolve,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    request = conversation_repo.get_restore_request(db, request_id)
    if not request:
        raise HTTPException(404, "Restore request not found")
    if request.status != "PENDING":
        raise HTTPException(400, "This request has already been resolved.")

    conversation = conversation_repo.get_conversation_any_owner(db, request.conversation_id)
    if payload.approve and not conversation:
        raise HTTPException(404, "Conversation not found")

    conversation_repo.resolve_restore_request(
        db, request, payload.approve, admin.id, payload.resolution_reason
    )
    if payload.approve:
        conversation_repo.restore_conversation(db, conversation)

    audit_repo.log_action(
        db,
        admin,
        "RESTORE_REQUEST_APPROVE" if payload.approve else "RESTORE_REQUEST_REJECT",
        target_type="restore_request",
        target_id=request.id,
    )


@router.get("/audit-logs", response_model=list[AuditLogOut])
def get_audit_logs(
    limit: int = Query(200, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return [
        AuditLogOut(
            id=entry.id,
            actor_email=entry.actor_email,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            status=entry.status,
            created_at=entry.created_at.isoformat(),
        )
        for entry in audit_repo.list_logs(db, limit=limit)
    ]


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active.is_(True)).count(),
        "total_conversations": db.query(Conversation).count(),
        "deleted_conversations": db.query(Conversation)
        .filter(Conversation.is_deleted.is_(True))
        .count(),
        "total_messages": db.query(Message).count(),
        "total_documents": db.query(Document).count(),
        "positive_feedback": db.query(Feedback).filter(Feedback.rating == 1).count(),
        "negative_feedback": db.query(Feedback).filter(Feedback.rating == -1).count(),
        "pending_restore_requests": db.query(RestoreRequest)
        .filter(RestoreRequest.status == "PENDING")
        .count(),
    }
