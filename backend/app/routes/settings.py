from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import User, UserSettings
from app.models.schemas import UserSettingsOut, UserSettingsUpdate
from app.services.leetcode_service import is_sync_available

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings:
        # belt-and-suspenders: signup already creates this row, but a
        # missing row should never 500 a request that can just create it
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=UserSettingsOut)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_or_create_settings(db, current_user.id)


@router.patch("", response_model=UserSettingsOut)
def update_settings(
    update: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_or_create_settings(db, current_user.id)
    data = update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/sync-status")
def sync_status():
    return {"available": is_sync_available()}
