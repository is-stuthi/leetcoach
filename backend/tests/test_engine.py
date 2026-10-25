from datetime import date, timedelta

from app.models.models import Problem, Revision, SolveLog, UserSettings
from app.recommendation.engine import recommend


def make_problem(db, user_id, leetcode_id, topics, solved=False, **kwargs):
    p = Problem(
        user_id=user_id,
        leetcode_id=leetcode_id,
        title=f"Problem {leetcode_id}",
        difficulty=kwargs.pop("difficulty", "Medium"),
        topics=topics,
        url=f"https://leetcode.com/problems/p{leetcode_id}/",
        solved=solved,
        **kwargs,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def get_settings(db, user_id):
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()


def kinds(result):
    return {item["kind"]: item["problem"] for item in result.items}


def test_new_pick_favors_an_unattempted_topic(db_session, user):
    make_problem(db_session, user.id, 1, ["Arrays"], solved=True, confidence=4, date_solved=date.today())
    make_problem(db_session, user.id, 2, ["Arrays"], solved=False)
    make_problem(db_session, user.id, 3, ["Graphs"], solved=False)

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    picked = kinds(result)["new"]
    # "Graphs" has zero solves, "Arrays" has one -- the scorer should favor
    # the topic with less coverage, per _score_new_candidate's rule 1
    assert picked.leetcode_id == 3


def test_revision_only_appears_when_actually_due(db_session, user):
    solved = make_problem(db_session, user.id, 1, ["Arrays"], solved=True, confidence=4, date_solved=date.today())
    make_problem(db_session, user.id, 2, ["Arrays"], solved=False)

    db_session.add(Revision(
        problem_id=solved.id, revision_count=1, interval_stage=0,
        next_revision_date=date.today() + timedelta(days=5), active=True,
    ))
    db_session.commit()

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    assert "revision" not in kinds(result)


def test_overdue_revision_is_picked(db_session, user):
    solved = make_problem(db_session, user.id, 1, ["Arrays"], solved=True, confidence=4, date_solved=date.today())
    make_problem(db_session, user.id, 2, ["Arrays"], solved=False)

    db_session.add(Revision(
        problem_id=solved.id, revision_count=1, interval_stage=0,
        next_revision_date=date.today() - timedelta(days=2), active=True,
    ))
    db_session.commit()

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    revision_item = next(item for item in result.items if item["kind"] == "revision")
    assert revision_item["problem"].id == solved.id
    assert any("was due" in r and "ago" in r for r in revision_item["reasons"])


def test_extra_pick_avoids_the_new_picks_topic(db_session, user):
    # "Graphs" has zero solves so it wins the "new" slot; give it a second
    # unsolved candidate too so there'd be a same-topic option available if
    # the variety rule weren't working
    make_problem(db_session, user.id, 1, ["Graphs"], solved=False)
    make_problem(db_session, user.id, 2, ["Graphs"], solved=False)
    make_problem(db_session, user.id, 3, ["Dynamic Programming"], solved=False)

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    picks = kinds(result)
    assert "Graphs" in picks["new"].topics
    assert "Graphs" not in picks["extra"].topics


def test_repetition_insight_fires_when_one_topic_dominates_recent_solves(db_session, user):
    today = date.today()
    for i in range(5):
        p = make_problem(db_session, user.id, i + 1, ["Dynamic Programming"], solved=True,
                          confidence=4, date_solved=today - timedelta(days=i))
        db_session.add(SolveLog(problem_id=p.id, date=today - timedelta(days=i), type="new"))
    db_session.commit()

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    assert len(result.insights) == 1
    assert "Dynamic Programming" in result.insights[0]


def test_recommend_never_sees_another_users_problems(db_session, user):
    from app.auth import hash_password
    from app.models.models import User

    other = User(email="other@example.com", password_hash=hash_password("otherpass123"))
    db_session.add(other)
    db_session.commit()
    db_session.add(UserSettings(user_id=other.id))
    db_session.commit()

    # the "other" user has data; our `user` fixture has none at all
    make_problem(db_session, other.id, 1, ["Arrays"], solved=False)

    settings = get_settings(db_session, user.id)
    result = recommend(db_session, settings, user.id)

    assert result.items == []
