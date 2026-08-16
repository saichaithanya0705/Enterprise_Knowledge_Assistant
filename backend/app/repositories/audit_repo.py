"""Data access for security audit logs with rollback-safe writes."""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    actor: User | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    status: str = "success",
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        status=status,
        metadata_json=metadata,
    )
    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except SQLAlchemyError:
        db.rollback()
        raise


def list_logs(db: Session, limit: int = 200) -> list[AuditLog]:
    safe_limit = max(1, min(limit, 200))
    try:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(safe_limit).all()
    except SQLAlchemyError:
        db.rollback()
        raise
