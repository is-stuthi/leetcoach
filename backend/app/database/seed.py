"""
Seeds the database with realistic mock LeetCode data so the app is fully
usable without any real LeetCode account/sync. Safe to re-run: it wipes and
recreates all tables first.
"""

from datetime import date, timedelta

from app.auth import hash_password
from app.database.db import Base, engine, SessionLocal
from app.database.sample_problems import SAMPLE_PROBLEMS
from app.models.models import Problem, Note, Revision, SolveLog, User, UserSettings

TODAY = date.today()

DEMO_EMAIL = "demo@leetcoach.app"
DEMO_PASSWORD = "demopass123"


def d(days_ago: int) -> date:
    """Return a date `days_ago` days before today (negative = future)."""
    return TODAY - timedelta(days=days_ago)


PROBLEM_DATA = SAMPLE_PROBLEMS

# solved, oldest -> newest, paired with "days ago solved"
SOLVED_OFFSETS = [
    (1, 49), (121, 46), (217, 43), (238, 40), (53, 38), (56, 35),
    (49, 33), (347, 31), (242, 29), (125, 27), (15, 25), (11, 23),
    (3, 21), (424, 19), (206, 17), (21, 15), (141, 14), (704, 12),
    (33, 10), (226, 9), (104, 7), (102, 6), (98, 4), (200, 3),
    (215, 2), (70, 2), (198, 1), (322, 0),
]
SOLVED_IDS = {lid for lid, _ in SOLVED_OFFSETS}
OFFSET_BY_ID = dict(SOLVED_OFFSETS)

BOOKMARKED_IDS = {42, 76, 15, 200, 322, 235}

# confidence overrides for specific solved problems; everything else cycles a default spread
CONFIDENCE_OVERRIDES = {
    15: 2,    # struggled
    424: 3,
    98: 4,
    200: 2,   # struggled
    322: 2,   # struggled, just solved
    49: 3,
}
DEFAULT_CONFIDENCE_CYCLE = [4, 5, 3, 4, 5, 3, 4]

# revision records: leetcode_id -> dict
# next_delta follows d()'s convention: positive = days ago (overdue/past),
# negative = days from now (future, not due yet), 0 = due today.
REVISIONS = {
    49: dict(revision_count=1, interval_stage=1, last_revised_delta=3, next_delta=0),
    15: dict(revision_count=0, interval_stage=0, last_revised_delta=None, next_delta=2),
    424: dict(revision_count=0, interval_stage=0, last_revised_delta=None, next_delta=0),
    98: dict(revision_count=0, interval_stage=0, last_revised_delta=None, next_delta=-1),
    200: dict(revision_count=0, interval_stage=0, last_revised_delta=None, next_delta=0),
    322: dict(revision_count=0, interval_stage=0, last_revised_delta=None, next_delta=-3),
}

# a few solved problems get a personal note attached, to demo the notebook
NOTES = {
    1: dict(
        notes_text="Classic. Used a hash map of value -> index for O(n).",
        key_insight="Complement lookup avoids the O(n^2) brute force.",
        mistake="Initially forgot to check the complement before inserting current value.",
        time_complexity="O(n)", space_complexity="O(n)",
    ),
    15: dict(
        notes_text="Sort first, then two pointers per fixed first element.",
        key_insight="Skipping duplicates for i, lo, and hi avoids duplicate triplets.",
        mistake="Missed the duplicate-skip on the outer loop, got duplicate triplets.",
        time_complexity="O(n^2)", space_complexity="O(1) extra (excl. sort)",
    ),
    49: dict(
        notes_text="Group by sorted-string key or by 26-count tuple key.",
        key_insight="Anagrams share the same character count signature.",
        mistake="Used sorted string key which is O(k log k) per word instead of O(k) counting.",
        time_complexity="O(n*k log k)", space_complexity="O(n*k)",
    ),
    200: dict(
        notes_text="DFS flood-fill from every unvisited '1'.",
        key_insight="Mutating the grid in place to mark visited avoids a separate visited set.",
        mistake="Forgot to bounds-check before recursing, caused index errors.",
        time_complexity="O(rows*cols)", space_complexity="O(rows*cols) worst case recursion depth",
    ),
    98: dict(
        notes_text="Pass down (low, high) bounds instead of just comparing to children.",
        key_insight="A node's whole subtree must fit within an inherited valid range, not just vs its direct parent.",
        mistake="Only compared node to immediate parent, missed a deeper violation.",
        time_complexity="O(n)", space_complexity="O(h)",
    ),
    322: dict(
        notes_text="Bottom-up DP over amounts 0..target.",
        key_insight="dp[a] = 1 + min(dp[a-c] for c in coins if a-c>=0).",
        mistake="Forgot to initialize dp[0]=0 and used float('inf') sentinel incorrectly at first.",
        time_complexity="O(amount * coins)", space_complexity="O(amount)",
    ),
}


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        demo_user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        db.add(demo_user)
        db.flush()  # assign demo_user.id before problems reference it

        problems_by_lid = {}
        for lid, title, difficulty, topics, slug in PROBLEM_DATA:
            solved = lid in SOLVED_IDS
            confidence = None
            date_solved = None
            if solved:
                date_solved = d(OFFSET_BY_ID[lid])
                confidence = CONFIDENCE_OVERRIDES.get(
                    lid, DEFAULT_CONFIDENCE_CYCLE[lid % len(DEFAULT_CONFIDENCE_CYCLE)]
                )

            p = Problem(
                user_id=demo_user.id,
                leetcode_id=lid,
                title=title,
                difficulty=difficulty,
                topics=topics,
                url=f"https://leetcode.com/problems/{slug}/",
                slug=slug,
                source="seed",
                solved=solved,
                date_solved=date_solved,
                bookmarked=lid in BOOKMARKED_IDS,
                confidence=confidence,
                needs_revision=lid in REVISIONS,
            )
            db.add(p)
            problems_by_lid[lid] = p

        db.flush()  # assign ids

        # solve log entries (drives streak / weekly count / history)
        for lid, offset in SOLVED_OFFSETS:
            db.add(SolveLog(problem_id=problems_by_lid[lid].id, date=d(offset), type="new"))
        # a couple of revision-type solve log entries for history variety
        db.add(SolveLog(problem_id=problems_by_lid[49].id, date=d(3), type="revision"))

        # revisions
        for lid, r in REVISIONS.items():
            db.add(Revision(
                problem_id=problems_by_lid[lid].id,
                revision_count=r["revision_count"],
                interval_stage=r["interval_stage"],
                last_revised_at=d(r["last_revised_delta"]) if r["last_revised_delta"] is not None else None,
                next_revision_date=d(r["next_delta"]),
                active=True,
            ))

        # notes
        for lid, n in NOTES.items():
            db.add(Note(problem_id=problems_by_lid[lid].id, **n))

        # default settings row
        db.add(UserSettings(
            user_id=demo_user.id,
            leetcode_username="",
            daily_target_new=1,
            daily_target_revision=1,
            preferred_difficulty="Medium",
            priority_topics=["Trees", "Graphs", "Dynamic Programming"],
            revision_intervals=[3, 10, 30],
        ))

        db.commit()
        print(f"Seeded {len(PROBLEM_DATA)} problems "
              f"({len(SOLVED_IDS)} solved, {len(PROBLEM_DATA) - len(SOLVED_IDS)} unsolved) "
              f"for demo account {DEMO_EMAIL} / {DEMO_PASSWORD}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
