"""HTTP routes for the coach chat (mounted at /api/v2)."""

from fastapi import APIRouter, Depends

from app.coach import service
from app.coach.schemas import CoachMessage, SendMessage
from app.core.auth import CurrentUser, get_current_user
from app.core.db import Database, get_db

router = APIRouter(tags=["coach-v2"])


@router.get("/coach/messages", response_model=list[CoachMessage])
def messages(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return service.list_messages(db, user.id)


@router.post("/coach/messages", response_model=CoachMessage)
def send(body: SendMessage, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Ask the coach. Returns its reply, with 0-3 proposed actions (buttons) that only run when clicked."""
    return service.send(db, user.id, body.content)


@router.delete("/coach/messages", status_code=204)
def clear(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.clear(db, user.id)
