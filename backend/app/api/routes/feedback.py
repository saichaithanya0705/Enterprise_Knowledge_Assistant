"""Answer feedback endpoint (thumbs up/down)."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackRequest
from app.repositories import conversation_repo
from app.repositories.conversation_repo import (
    DuplicateFeedbackError,
    FeedbackPersistenceError,
    InvalidFeedbackMessageError,
    MessageNotFoundError,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


@router.post("", status_code=201)
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        fb = conversation_repo.add_feedback(
            db,
            payload.message_id,
            payload.rating,
            payload.comment,
            user_id=current_user.id,
        )
    except MessageNotFoundError:
        raise HTTPException(404, "Message not found")
    except InvalidFeedbackMessageError:
        raise HTTPException(400, "Feedback can only be submitted for assistant messages")
    except DuplicateFeedbackError:
        raise HTTPException(409, "Feedback already exists for this message")
    except FeedbackPersistenceError:
        db.rollback()
        logger.warning(
            "Feedback persistence failed message_id=%s error_type=%s",
            payload.message_id,
            FeedbackPersistenceError.__name__,
        )
        raise HTTPException(500, "Unable to record feedback.")
    except Exception as error:  # noqa: BLE001 - keep database details out of the API
        db.rollback()
        logger.warning(
            "Feedback persistence failed message_id=%s error_type=%s",
            payload.message_id,
            type(error).__name__,
        )
        raise HTTPException(500, "Unable to record feedback.")
    return {"id": fb.id, "status": "recorded"}
