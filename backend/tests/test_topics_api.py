from datetime import date

from app.models.models import Problem
from tests.conftest import auth_headers

# There's no endpoint to create a brand-new Problem from scratch -- sync and
# seed are the only writers of new rows. So these tests insert Problem rows
# directly via db_session for setup, and only use `client` to call the
# /api/topics endpoint actually under test.


def test_topic_with_no_solves_is_low_coverage(client, db_session):
    headers = auth_headers(client, "topics1@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()

    db_session.add(Problem(
        user_id=me["id"], leetcode_id=1, title="P1", difficulty="Medium",
        topics=["Graphs"], url="https://x/1", solved=False,
    ))
    db_session.commit()

    resp = client.get("/api/topics", headers=headers)
    assert resp.status_code == 200
    stats = {s["topic"]: s for s in resp.json()}
    assert stats["Graphs"]["label"] == "low_coverage"
    assert stats["Graphs"]["solved"] == 0


def test_topic_weak_from_low_confidence_not_low_solve_count(client, db_session):
    """The whole point of this classifier (per the README) is that a topic
    is only called 'weak' from an actual low-confidence solve -- never
    purely from a low solved-count. One low-confidence solve must be enough
    to call it weak, regardless of how big the topic's catalog is."""
    headers = auth_headers(client, "topics2@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()

    db_session.add(Problem(
        user_id=me["id"], leetcode_id=1, title="P1", difficulty="Hard",
        topics=["Dynamic Programming"], url="https://x/1",
        solved=True, confidence=1, date_solved=date.today(),
    ))
    # plenty of same-topic problems the user hasn't touched -- a
    # percentage-based rule would never call this topic "weak"
    for lid in range(2, 50):
        db_session.add(Problem(
            user_id=me["id"], leetcode_id=lid, title=f"P{lid}", difficulty="Hard",
            topics=["Dynamic Programming"], url=f"https://x/{lid}", solved=False,
        ))
    db_session.commit()

    resp = client.get("/api/topics", headers=headers)
    stats = {s["topic"]: s for s in resp.json()}
    assert stats["Dynamic Programming"]["label"] == "weak"


def test_topic_strong_requires_floor_and_good_confidence(client, db_session):
    headers = auth_headers(client, "topics3@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()

    for lid in range(1, 4):
        db_session.add(Problem(
            user_id=me["id"], leetcode_id=lid, title=f"P{lid}", difficulty="Easy",
            topics=["Arrays"], url=f"https://x/{lid}",
            solved=True, confidence=5, date_solved=date.today(),
        ))
    db_session.commit()

    resp = client.get("/api/topics", headers=headers)
    stats = {s["topic"]: s for s in resp.json()}
    assert stats["Arrays"]["label"] == "strong"


def test_topics_are_scoped_per_user(client, db_session):
    headers_a = auth_headers(client, "usera@example.com", "testpass123")
    me_a = client.get("/api/auth/me", headers=headers_a).json()
    headers_b = auth_headers(client, "userb@example.com", "testpass123")

    db_session.add(Problem(
        user_id=me_a["id"], leetcode_id=1, title="Only A's", difficulty="Easy",
        topics=["Arrays"], url="https://x/1", solved=True, confidence=5, date_solved=date.today(),
    ))
    db_session.commit()

    resp_b = client.get("/api/topics", headers=headers_b)
    assert resp_b.json() == []
