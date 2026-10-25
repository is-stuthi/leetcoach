from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import Problem, SolveLog, SyncStatus, User
from app.models.schemas import SyncRequest, SyncStatusOut
from app.routes.settings import get_or_create_settings
from app.services import leetcode_service as lc
from app.services.leetcode_service import LeetCodeSyncError

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _get_sync_status_row(db: Session, user_id: int) -> SyncStatus:
    status = db.query(SyncStatus).filter(SyncStatus.user_id == user_id).first()
    if not status:
        status = SyncStatus(user_id=user_id)
        db.add(status)
        db.commit()
        db.refresh(status)
    return status


def _upsert_catalog_problem(db: Session, user_id: int, cp: lc.CatalogProblem) -> Problem:
    """Insert or refresh catalog metadata for a problem, scoped to this
    user's own catalog. Never touches user-owned fields (solved,
    date_solved, bookmarked, confidence, needs_revision) -- those are only
    ever changed by the solved-marking step or by the user directly."""
    existing = (
        db.query(Problem)
        .filter(Problem.user_id == user_id, Problem.leetcode_id == cp.leetcode_id)
        .first()
    )
    if existing:
        existing.title = cp.title
        existing.difficulty = cp.difficulty
        existing.topics = cp.topics
        existing.url = f"https://leetcode.com/problems/{cp.slug}/"
        existing.slug = cp.slug
        if existing.source != "synced":
            existing.source = "synced"
        return existing

    problem = Problem(
        user_id=user_id,
        leetcode_id=cp.leetcode_id,
        title=cp.title,
        difficulty=cp.difficulty,
        topics=cp.topics,
        url=f"https://leetcode.com/problems/{cp.slug}/",
        slug=cp.slug,
        source="synced",
        solved=False,
    )
    db.add(problem)
    return problem


def _mark_solved(db: Session, problem: Problem, solved_on) -> bool:
    """Mark a problem solved with an authoritative real date. Returns True
    if this was a newly-recorded solve (for the newly_solved counter).
    Idempotent: re-running with the same data changes nothing further and
    never inserts a duplicate SolveLog row."""
    was_unsolved = not problem.solved
    problem.solved = True
    problem.date_solved = solved_on

    log_exists = (
        db.query(SolveLog)
        .filter(SolveLog.problem_id == problem.id, SolveLog.date == solved_on, SolveLog.type == "new")
        .first()
    )
    if not log_exists:
        db.add(SolveLog(problem_id=problem.id, date=solved_on, type="new"))

    return was_unsolved


@router.post("/leetcode", response_model=SyncStatusOut)
def sync_leetcode(
    body: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_or_create_settings(db, current_user.id)
    username = (body.username or settings.leetcode_username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="No LeetCode username configured. Set one in Settings first.")

    status = _get_sync_status_row(db, current_user.id)
    warnings: list[str] = []
    errors: list[str] = []

    # 1. profile totals (authoritative aggregate counts)
    try:
        profile = lc.fetch_public_profile(username)
    except LeetCodeSyncError as e:
        # nothing was fetched this run -- don't let stale numbers from a
        # previous successful sync linger and look like they belong here
        status.username_synced = username
        status.last_synced_at = datetime.utcnow()
        status.success = False
        status.problems_synced = 0
        status.newly_solved = 0
        status.warnings = []
        status.errors = [str(e)]
        status.reported_easy = None
        status.reported_medium = None
        status.reported_hard = None
        status.reported_total = None
        db.commit()
        db.refresh(status)
        raise HTTPException(status_code=502, detail=str(e))

    # 2. catalog: real problem pool for the recommendation engine
    catalog_result = lc.fetch_problem_catalog()
    warnings.extend(catalog_result.warnings)
    for cp in catalog_result.problems:
        _upsert_catalog_problem(db, current_user.id, cp)
    db.flush()  # so newly-inserted catalog rows get ids before the solved-matching step

    catalog_by_slug = {cp.slug: cp for cp in catalog_result.problems}

    # 3. recent accepted submissions: mark solved with real dates
    try:
        recent_result = lc.fetch_recent_accepted(username)
    except LeetCodeSyncError as e:
        recent_result = lc.RecentSolvesResult(solves=[], hit_api_limit=False)
        warnings.append(f"couldn't fetch recent submissions: {e}")

    newly_solved = 0
    if recent_result.hit_api_limit:
        warnings.append(
            f"LeetCode's public API only exposes your ~{lc.RECENT_SUBMISSIONS_LIMIT} most recent "
            "accepted submissions without login -- older solves are not individually importable. "
            "Aggregate Easy/Medium/Hard totals below are accurate regardless."
        )

    for solve in recent_result.solves:
        cp = catalog_by_slug.get(solve.slug)
        if cp is None:
            lookup = lc.fetch_question_detail(solve.slug)
            if lookup.problem is None:
                warnings.append(f"skipped '{solve.title}': {lookup.skipped_reason}")
                continue
            cp = lookup.problem
            _upsert_catalog_problem(db, current_user.id, cp)
            db.flush()

        problem = (
            db.query(Problem)
            .filter(Problem.user_id == current_user.id, Problem.leetcode_id == cp.leetcode_id)
            .first()
        )
        if problem is None:
            continue  # shouldn't happen, but never let a lookup miss crash the sync
        if _mark_solved(db, problem, solve.solved_on):
            newly_solved += 1

    # persist sync status
    status.username_synced = username
    status.last_synced_at = datetime.utcnow()
    status.success = True
    status.problems_synced = len(catalog_result.problems)
    status.newly_solved = newly_solved
    status.warnings = warnings
    status.errors = errors
    status.reported_easy = profile.easy_solved
    status.reported_medium = profile.medium_solved
    status.reported_hard = profile.hard_solved
    status.reported_total = profile.total_solved

    if settings.leetcode_username != username:
        settings.leetcode_username = username

    db.commit()
    db.refresh(status)
    return status


@router.get("/status", response_model=SyncStatusOut)
def get_sync_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_sync_status_row(db, current_user.id)
