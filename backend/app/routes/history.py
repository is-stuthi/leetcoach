from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import Problem, SolveLog, User
from app.models.schemas import SolveLogOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[SolveLogOut])
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logs = (
        db.query(SolveLog)
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == current_user.id)
        .order_by(SolveLog.date.desc())
        .all()
    )
    return logs


@router.get("/calendar")
def get_calendar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 84,
):
    """Day -> solve count, for an activity-heatmap style calendar."""
    start = date.today() - timedelta(days=days)
    logs = (
        db.query(SolveLog)
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == current_user.id)
        .filter(SolveLog.date >= start)
        .all()
    )
    counts: dict[str, int] = {}
    for log in logs:
        key = log.date.isoformat()
        counts[key] = counts.get(key, 0) + 1
    return counts
