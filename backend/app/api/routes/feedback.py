"""Answer feedback endpoint (thumbs up/down)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.feedback import FeedbackRequest
from app.repositories import conversation_repo

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", status_code=201)
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    fb = conversation_repo.add_feedback(db, payload.message_id, payload.rating, payload.comment)
    return {"id": fb.id, "status": "recorded"}
