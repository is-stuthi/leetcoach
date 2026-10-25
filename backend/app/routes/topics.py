from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database.db import get_db
from app.models.models import Problem, SolveLog, User
from app.models.schemas import TopicStat

router = APIRouter(prefix="/api/topics", tags=["topics"])

MIN_SOLVED_FOR_OPINION = 3     # need at least this many solves to say anything
WEAK_CONFIDENCE_THRESHOLD = 3.0
STRONG_CONFIDENCE_THRESHOLD = 3.5


@router.get("", response_model=list[TopicStat])
def get_topic_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    problems = db.query(Problem).filter(Problem.user_id == current_user.id).all()

    per_topic: dict[str, list[Problem]] = {}
    for p in problems:
        for t in p.topics:
            per_topic.setdefault(t, []).append(p)

    stats: list[TopicStat] = []
    for topic, plist in per_topic.items():
        total = len(plist)
        solved_list = [p for p in plist if p.solved]
        solved = len(solved_list)
        coverage = solved / total if total else 0.0

        confidences = [p.confidence for p in solved_list if p.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        # Strength is judged from confidence on actual attempts, gated by an
        # ABSOLUTE solved-count floor -- never from solved/total. A ratio
        # against "total available" breaks down once the practice catalog is
        # sourced from real LeetCode data: the public sync API can only ever
        # individually confirm a capped, small number of solves regardless of
        # a user's true lifetime total, while the catalog can run into the
        # hundreds. A ratio-based bar would then be permanently unreachable
        # for every real synced user, however skilled. Order matters here
        # too: a real performance signal (low confidence on attempts
        # actually made) takes priority over raw volume, so we never call a
        # topic "weak" purely because few problems have been solved in it.
        if solved == 0:
            label = "low_coverage"
            reason = f"no {topic} problems attempted yet out of {total} available -- not enough data to judge"
        elif avg_confidence is not None and avg_confidence < WEAK_CONFIDENCE_THRESHOLD:
            label = "weak"
            caveat = " (small sample, but worth extra practice)" if solved < MIN_SOLVED_FOR_OPINION else ""
            reason = f"solved {solved}/{total} but average confidence is low ({avg_confidence:.1f}/5){caveat}"
        elif solved < MIN_SOLVED_FOR_OPINION:
            label = "low_coverage"
            reason = f"only {solved} {topic} problem(s) solved so far -- too few to judge strength"
        elif avg_confidence is not None and avg_confidence >= STRONG_CONFIDENCE_THRESHOLD:
            label = "strong"
            reason = f"solved {solved}/{total} with good confidence ({avg_confidence:.1f}/5)"
        else:
            label = "neutral"
            reason = f"solved {solved}/{total}, no strong signal either way yet"

        stats.append(TopicStat(
            topic=topic, solved=solved, total=total, coverage=round(coverage, 2),
            avg_confidence=round(avg_confidence, 2) if avg_confidence is not None else None,
            label=label, reason=reason,
        ))

    stats.sort(key=lambda s: s.topic)
    return stats


@router.get("/trends")
def get_topic_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 14,
):
    cutoff = date.today() - timedelta(days=days)
    logs = (
        db.query(SolveLog)
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == current_user.id)
        .filter(SolveLog.date >= cutoff)
        .all()
    )
    trend: dict[str, int] = {}
    for log in logs:
        for t in log.problem.topics:
            trend[t] = trend.get(t, 0) + 1
    return dict(sorted(trend.items(), key=lambda kv: kv[1], reverse=True))
