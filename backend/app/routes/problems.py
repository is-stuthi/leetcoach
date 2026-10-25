from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.auth import get_current_user
from app.database.db import get_db
from app.database.sample_problems import SAMPLE_PROBLEMS
from app.models.models import Problem, Note, User
from app.models.schemas import ProblemOut, ProblemUpdate, NoteOut, NoteUpdate

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.post("/load-sample")
def load_sample_problems(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Gives a brand-new account (no real LeetCode profile to sync yet) a
    real practice catalog to start with -- unsolved, no fake history,
    unlike the seed script's demo data. Safe to call more than once:
    skips any leetcode_id the user already has instead of duplicating it."""
    existing_ids = {
        lid for (lid,) in db.query(Problem.leetcode_id).filter(Problem.user_id == current_user.id).all()
    }

    added = 0
    for lid, title, difficulty, topics, slug in SAMPLE_PROBLEMS:
        if lid in existing_ids:
            continue
        db.add(Problem(
            user_id=current_user.id,
            leetcode_id=lid,
            title=title,
            difficulty=difficulty,
            topics=topics,
            url=f"https://leetcode.com/problems/{slug}/",
            slug=slug,
            source="sample",
            solved=False,
        ))
        added += 1

    db.commit()
    return {"added": added}


@router.get("", response_model=list[ProblemOut])
def list_problems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    solved: Optional[bool] = None,
    bookmarked: Optional[bool] = None,
    needs_revision: Optional[bool] = None,
    sort_by: str = Query("leetcode_id", pattern="^(leetcode_id|title|difficulty|date_solved|confidence)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    q = db.query(Problem).filter(Problem.user_id == current_user.id)

    if search:
        like = f"%{search}%"
        if search.isdigit():
            q = q.filter(or_(Problem.title.ilike(like), Problem.leetcode_id == int(search)))
        else:
            q = q.filter(Problem.title.ilike(like))

    if difficulty:
        q = q.filter(Problem.difficulty == difficulty)
    if solved is not None:
        q = q.filter(Problem.solved == solved)
    if bookmarked is not None:
        q = q.filter(Problem.bookmarked == bookmarked)
    if needs_revision is not None:
        q = q.filter(Problem.needs_revision == needs_revision)

    problems = q.all()

    if topic:
        problems = [p for p in problems if topic in (p.topics or [])]

    reverse = sort_dir == "desc"
    if sort_by == "date_solved":
        problems.sort(key=lambda p: (p.date_solved is None, p.date_solved), reverse=reverse)
    elif sort_by == "confidence":
        problems.sort(key=lambda p: (p.confidence is None, p.confidence), reverse=reverse)
    else:
        problems.sort(key=lambda p: getattr(p, sort_by), reverse=reverse)

    return problems


@router.get("/topics", response_model=list[str])
def list_all_topics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    topics = set()
    for p in db.query(Problem).filter(Problem.user_id == current_user.id).all():
        topics.update(p.topics or [])
    return sorted(topics)


def _get_owned_problem(db: Session, problem_id: int, current_user: User) -> Problem:
    """Shared lookup used by every route below -- always filters by both id
    AND user_id, never just id. Without the user_id check, a user could read
    or edit another user's problem simply by guessing/incrementing an id."""
    p = (
        db.query(Problem)
        .filter(Problem.id == problem_id, Problem.user_id == current_user.id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_owned_problem(db, problem_id, current_user)


@router.patch("/{problem_id}", response_model=ProblemOut)
def update_problem(
    problem_id: int,
    update: ProblemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _get_owned_problem(db, problem_id, current_user)

    data = update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return p


@router.put("/{problem_id}/note", response_model=NoteOut)
def upsert_note(
    problem_id: int,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _get_owned_problem(db, problem_id, current_user)

    note = db.query(Note).filter(Note.problem_id == p.id).first()
    if not note:
        note = Note(problem_id=p.id)
        db.add(note)

    for field, value in note_update.model_dump().items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)
    return note
