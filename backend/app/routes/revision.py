from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import Problem, Revision, SolveLog, User
from app.models.schemas import ProblemOut
from app.routes.settings import get_or_create_settings

router = APIRouter(prefix="/api/revision", tags=["revision"])


def _get_owned_problem(db: Session, problem_id: int, current_user: User) -> Problem:
    p = (
        db.query(Problem)
        .filter(Problem.id == problem_id, Problem.user_id == current_user.id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


@router.get("/due", response_model=list[ProblemOut])
def get_due(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Problem)
        .join(Revision, Revision.problem_id == Problem.id)
        .filter(Problem.user_id == current_user.id)
        .filter(Revision.active == True)  # noqa: E712
        .filter(Revision.next_revision_date <= date.today())
        .all()
    )


@router.get("", response_model=list[ProblemOut])
def get_all_revision_problems(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Problem)
        .filter(Problem.user_id == current_user.id)
        .filter(Problem.needs_revision == True)  # noqa: E712
        .all()
    )


@router.post("/{problem_id}/mark", response_model=ProblemOut)
def mark_for_revision(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _get_owned_problem(db, problem_id, current_user)
    if not p.solved:
        raise HTTPException(status_code=400, detail="Only solved problems can be scheduled for revision")

    settings = get_or_create_settings(db, current_user.id)
    intervals = settings.revision_intervals or [3, 10, 30]

    revision = db.query(Revision).filter(Revision.problem_id == p.id).first()
    if not revision:
        revision = Revision(problem_id=p.id, revision_count=0, interval_stage=0)
        db.add(revision)

    revision.active = True
    revision.next_revision_date = date.today() + timedelta(days=intervals[0])
    p.needs_revision = True

    db.commit()
    db.refresh(p)
    return p


@router.post("/{problem_id}/unmark", response_model=ProblemOut)
def unmark_revision(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _get_owned_problem(db, problem_id, current_user)

    revision = db.query(Revision).filter(Revision.problem_id == p.id).first()
    if revision:
        revision.active = False
    p.needs_revision = False

    db.commit()
    db.refresh(p)
    return p


class CompleteRevisionBody(BaseModel):
    confidence: Optional[int] = None


@router.post("/{problem_id}/complete", response_model=ProblemOut)
def complete_revision(
    problem_id: int,
    body: CompleteRevisionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _get_owned_problem(db, problem_id, current_user)

    revision = db.query(Revision).filter(Revision.problem_id == p.id).first()
    if not revision:
        raise HTTPException(status_code=400, detail="Problem is not scheduled for revision")

    settings = get_or_create_settings(db, current_user.id)
    intervals = settings.revision_intervals or [3, 10, 30]

    if body.confidence is not None:
        p.confidence = body.confidence

    today = date.today()
    struggled = body.confidence is not None and body.confidence <= 2

    if struggled:
        # revisit sooner: reset to the shortest interval instead of advancing
        revision.interval_stage = 0
        next_interval = intervals[0]
    else:
        revision.interval_stage = min(revision.interval_stage + 1, len(intervals) - 1)
        next_interval = intervals[revision.interval_stage]

    revision.revision_count += 1
    revision.last_revised_at = today

    if revision.revision_count >= len(intervals) and not struggled:
        # completed the full ladder without struggling: retire from active revision
        revision.active = False
        revision.next_revision_date = None
        p.needs_revision = False
    else:
        revision.next_revision_date = today + timedelta(days=next_interval)

    db.add(SolveLog(problem_id=p.id, date=today, type="revision"))

    db.commit()
    db.refresh(p)
    return p
