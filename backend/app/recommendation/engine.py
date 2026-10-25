"""
Rule-based recommendation engine.

Deliberately NOT machine learning. Every recommendation is a transparent
weighted score built from a handful of interpretable signals, and every
score component that contributes is turned directly into a human-readable
reason string. This module is self-contained so the scoring can be tweaked
or replaced later without touching routes or the frontend contract
(routes/recommendation.py just calls `recommend()`).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.models import Problem, Revision, SolveLog, UserSettings

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}
RECENT_WINDOW_DAYS = 14


@dataclass
class ScoredProblem:
    problem: Problem
    score: float
    reasons: list[str] = field(default_factory=list)


def _topic_solved_counts(solved_problems: list[Problem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in solved_problems:
        for t in p.topics:
            counts[t] = counts.get(t, 0) + 1
    return counts


REPETITION_LOOKBACK = 8       # how many of the most recent distinct solves to look at
REPETITION_MIN_SAMPLE = 4     # don't call out a pattern from too few data points
REPETITION_MAJORITY_FRACTION = 0.5  # a topic covering >= half of recent solves is "repetitive"


def _repetition_insight(db: Session, user_id: int) -> list[str]:
    """Answers 'am I repeatedly solving the same type of problem?' directly,
    rather than leaving it implicit in the variety penalty below. Looks at
    the most recent distinct solved problems (by solve_log date) and flags
    it when one topic dominates -- this is the same recency signal the
    scorer's variety penalty uses internally, just surfaced as plain text."""
    logs = (
        db.query(SolveLog)
        .filter(SolveLog.type == "new")
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == user_id)
        .order_by(SolveLog.date.desc())
        .all()
    )
    seen_problem_ids: set[int] = set()
    recent_problems: list[Problem] = []
    for log in logs:
        if log.problem_id in seen_problem_ids:
            continue
        seen_problem_ids.add(log.problem_id)
        recent_problems.append(log.problem)
        if len(recent_problems) >= REPETITION_LOOKBACK:
            break

    if len(recent_problems) < REPETITION_MIN_SAMPLE:
        return []

    topic_counts = _topic_solved_counts(recent_problems)
    if not topic_counts:
        return []

    top_topic, top_count = max(topic_counts.items(), key=lambda kv: kv[1])
    fraction = top_count / len(recent_problems)
    if fraction >= REPETITION_MAJORITY_FRACTION:
        return [
            f"{top_count} of your last {len(recent_problems)} solves were {top_topic} -- "
            "recommendations below are deliberately favoring other topics for variety."
        ]
    return []


def _recent_topics(db: Session, user_id: int, within_days: int = RECENT_WINDOW_DAYS) -> dict[str, int]:
    """Topic -> number of solves in the recent window (from solve_log)."""
    cutoff = date.today() - timedelta(days=within_days)
    logs = (
        db.query(SolveLog)
        .join(Problem, Problem.id == SolveLog.problem_id)
        .filter(Problem.user_id == user_id)
        .filter(SolveLog.date >= cutoff)
        .all()
    )
    counts: dict[str, int] = {}
    for log in logs:
        for t in log.problem.topics:
            counts[t] = counts.get(t, 0) + 1
    return counts


def _score_new_candidate(
    candidate: Problem,
    topic_counts: dict[str, int],
    recent_topics: dict[str, int],
    recent_difficulty_avg: float,
    settings: UserSettings,
    avoid_topics: set[str],
) -> ScoredProblem:
    score = 0.0
    reasons: list[str] = []

    # 1. topic weakness: fewer solved in this problem's topics -> higher score
    min_topic_count = min((topic_counts.get(t, 0) for t in candidate.topics), default=0)
    if min_topic_count == 0:
        score += 30
        reasons.append(
            f"you haven't solved any {', '.join(candidate.topics)} problems yet"
        )
    elif min_topic_count <= 2:
        score += 18
        reasons.append(
            f"you have solved few {', '.join(candidate.topics)} problems ({min_topic_count})"
        )
    else:
        score += 4

    # 2. difficulty progression: prefer candidates close to (recent avg + 1 step),
    #    and matching user's preferred difficulty
    cand_level = DIFFICULTY_ORDER[candidate.difficulty]
    target_level = min(2, round(recent_difficulty_avg))
    if cand_level == target_level:
        score += 15
        reasons.append(
            f"matches your recent difficulty progression (~{candidate.difficulty})"
        )
    elif abs(cand_level - target_level) == 1:
        score += 7

    if candidate.difficulty == settings.preferred_difficulty:
        score += 10
        reasons.append(f"matches your preferred difficulty ({settings.preferred_difficulty})")

    # 3. priority topics from settings
    priority_hit = set(candidate.topics) & set(settings.priority_topics or [])
    if priority_hit:
        score += 20
        reasons.append(f"in your priority topics: {', '.join(sorted(priority_hit))}")

    # 4. bookmarked / important
    if candidate.bookmarked:
        score += 12
        reasons.append("you bookmarked this problem as important")

    # 5. variety: penalize topics solved a lot very recently, and topics already
    #    picked in this same recommendation batch
    recent_hit = sum(recent_topics.get(t, 0) for t in candidate.topics)
    if recent_hit >= 3:
        score -= 12
    if set(candidate.topics) & avoid_topics:
        score -= 25
        reasons.append("picked from a different topic than your other recommendation for variety")

    reasons.append("this problem has not been attempted yet")

    return ScoredProblem(problem=candidate, score=score, reasons=reasons)


def _score_revision_candidate(candidate: Problem, revision: Revision) -> ScoredProblem:
    today = date.today()
    days_overdue = (today - revision.next_revision_date).days if revision.next_revision_date else 0
    score = 0.0
    reasons = []

    if days_overdue > 0:
        score += 20 + min(days_overdue * 4, 40)
        reasons.append(f"revision was due {days_overdue} day(s) ago")
    else:
        score += 20
        reasons.append("revision is due today")

    confidence = candidate.confidence or 3
    if confidence <= 2:
        score += (3 - confidence) * 10
        reasons.append(f"low confidence ({confidence}/5) on this one, worth revisiting sooner")

    if candidate.bookmarked:
        score += 5
        reasons.append("bookmarked as important")

    return ScoredProblem(problem=candidate, score=score, reasons=reasons)


@dataclass
class RecommendationResult:
    items: list[dict]
    insights: list[str]


def recommend(db: Session, settings: UserSettings, user_id: int) -> RecommendationResult:
    """
    Returns up to 3 recommendation dicts: one "new", one "revision" (if
    anything is due), and one "extra" practice pick with a different topic
    focus than the "new" pick for variety. Also returns top-level insights
    (e.g. repetition warnings) that aren't tied to any single pick.
    """
    all_problems = db.query(Problem).filter(Problem.user_id == user_id).all()
    solved = [p for p in all_problems if p.solved]
    unsolved = [p for p in all_problems if not p.solved]

    topic_counts = _topic_solved_counts(solved)
    recent_topics = _recent_topics(db, user_id)

    recent_solved = sorted(
        [p for p in solved if p.date_solved], key=lambda p: p.date_solved, reverse=True
    )[:5]
    recent_difficulty_avg = (
        sum(DIFFICULTY_ORDER[p.difficulty] for p in recent_solved) / len(recent_solved)
        if recent_solved else 1.0
    )

    results: list[dict] = []
    avoid_topics: set[str] = set()

    # --- primary "new" pick ---
    new_scored = [
        _score_new_candidate(c, topic_counts, recent_topics, recent_difficulty_avg, settings, avoid_topics)
        for c in unsolved
    ]
    new_scored.sort(key=lambda s: s.score, reverse=True)
    if new_scored:
        top = new_scored[0]
        results.append({"problem": top.problem, "kind": "new", "score": top.score, "reasons": top.reasons})
        avoid_topics |= set(top.problem.topics)

    # --- revision pick (only if something is due today or overdue) ---
    due_revisions = (
        db.query(Revision)
        .join(Problem, Problem.id == Revision.problem_id)
        .filter(Problem.user_id == user_id)
        .filter(Revision.active == True)  # noqa: E712
        .filter(Revision.next_revision_date <= date.today())
        .all()
    )
    if due_revisions:
        rev_scored = [
            _score_revision_candidate(r.problem, r) for r in due_revisions
        ]
        rev_scored.sort(key=lambda s: s.score, reverse=True)
        top_rev = rev_scored[0]
        results.append({
            "problem": top_rev.problem, "kind": "revision",
            "score": top_rev.score, "reasons": top_rev.reasons,
        })

    # --- extra practice pick: best remaining candidate with different topics ---
    remaining = [s for s in new_scored[1:] if not (set(s.problem.topics) & avoid_topics)]
    if remaining:
        remaining.sort(key=lambda s: s.score, reverse=True)
        extra = remaining[0]
        results.append({
            "problem": extra.problem, "kind": "extra",
            "score": extra.score, "reasons": extra.reasons,
        })
    elif len(new_scored) > 1:
        # no disjoint-topic candidate available; fall back to next best overall
        extra = new_scored[1]
        results.append({
            "problem": extra.problem, "kind": "extra",
            "score": extra.score, "reasons": extra.reasons,
        })

    return RecommendationResult(items=results, insights=_repetition_insight(db, user_id))
