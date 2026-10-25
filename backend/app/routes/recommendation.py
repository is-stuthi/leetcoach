from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import User
from app.models.schemas import RecommendationResponse
from app.recommendation.engine import recommend
from app.routes.settings import get_or_create_settings

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationResponse)
def get_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_or_create_settings(db, current_user.id)
    result = recommend(db, settings, current_user.id)
    return RecommendationResponse(items=result.items, insights=result.insights)
