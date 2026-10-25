from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import Problem, Revision, SolveLog, User
from app.models.schemas import DashboardStats, DifficultyCounts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _current_streak(solve_dates: set[date]) -> int:
    if not solve_dates:
        return 0
    today = date.today()
    # streak counts backward from today; if nothing solved today, check if
    # yesterday keeps a streak alive (still "current" until today ends)
    start = today if today in solve_dates else (today - timedelta(days=1))
    if start not in solve_dates:
        return 0
    streak = 0
    cursor = start
    while cursor in solve_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    problems = db.query(Problem).filter(Problem.user_id == current_user.id).all()
    solved = [p for p in problems if p.solved]

    diff_counts = DifficultyCounts()
    for p in solved:
        setattr(diff_counts, p.difficulty, getattr(diff_counts, p.difficulty) + 1)

    week_ago = date.today() - timedelta(days=7)
    solved_this_week = sum(1 for p in solved if p.date_solved and p.date_solved >= week_ago)

    solve_dates = {p.date_solved for p in solved if p.date_solved}
    streak = _current_streak(solve_dates)

    topic_dist: dict[str, int] = {}
    for p in solved:
        for t in p.topics:
            topic_dist[t] = topic_dist.get(t, 0) + 1

    logs = (
        db.query(SolveLog)
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == current_user.id)
        .filter(SolveLog.date >= date.today() - timedelta(days=60))
        .all()
    )
    activity: dict[str, int] = {}
    for log in logs:
        key = log.date.isoformat()
        activity[key] = activity.get(key, 0) + 1

    due_revisions = (
        db.query(Problem)
        .join(Revision, Revision.problem_id == Problem.id)
        .filter(Problem.user_id == current_user.id)
        .filter(Revision.active == True)  # noqa: E712
        .filter(Revision.next_revision_date <= date.today())
        .all()
    )

    bookmarked = [p for p in problems if p.bookmarked]

    recent = sorted([p for p in solved if p.date_solved], key=lambda p: p.date_solved, reverse=True)[:8]

    return DashboardStats(
        total_solved=len(solved),
        total_problems=len(problems),
        difficulty_counts=diff_counts,
        solved_this_week=solved_this_week,
        current_streak=streak,
        topic_distribution=topic_dist,
        activity_over_time=activity,
        revisions_due_today=due_revisions,
        bookmarked=bookmarked,
        recent_problems=recent,
    )
