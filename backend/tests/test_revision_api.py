from datetime import date, timedelta

from app.models.models import Problem, Revision
from tests.conftest import auth_headers


def add_solved_problem(db_session, user_id, leetcode_id=1):
    p = Problem(
        user_id=user_id, leetcode_id=leetcode_id, title=f"P{leetcode_id}",
        difficulty="Medium", topics=["Arrays"], url=f"https://x/{leetcode_id}",
        solved=True, confidence=4, date_solved=date.today(),
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def test_mark_unsolved_problem_for_revision_is_rejected(client, db_session):
    headers = auth_headers(client, "rev1@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()
    unsolved = Problem(
        user_id=me["id"], leetcode_id=1, title="P1", difficulty="Easy",
        topics=["Arrays"], url="https://x/1", solved=False,
    )
    db_session.add(unsolved)
    db_session.commit()
    db_session.refresh(unsolved)

    resp = client.post(f"/api/revision/{unsolved.id}/mark", headers=headers)
    assert resp.status_code == 400


def test_freshly_marked_revision_is_not_due_yet(client, db_session):
    """Marking schedules the FIRST rung of the ladder (3 days out by
    default), not "due today" -- it shouldn't show up in /due immediately."""
    headers = auth_headers(client, "rev2@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()
    p = add_solved_problem(db_session, me["id"])

    client.post(f"/api/revision/{p.id}/mark", headers=headers)

    due = client.get("/api/revision/due", headers=headers).json()
    assert due == []

    all_revisions = client.get("/api/revision", headers=headers).json()
    assert [r["id"] for r in all_revisions] == [p.id]


def test_overdue_revision_shows_up_in_due_list(client, db_session):
    headers = auth_headers(client, "rev2b@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()
    p = add_solved_problem(db_session, me["id"])

    client.post(f"/api/revision/{p.id}/mark", headers=headers)
    # simulate time passing: push the schedule into the past, the way a
    # real 3-day wait would naturally do
    revision = db_session.query(Revision).filter(Revision.problem_id == p.id).first()
    revision.next_revision_date = date.today() - timedelta(days=1)
    db_session.commit()

    due = client.get("/api/revision/due", headers=headers).json()
    assert [d["id"] for d in due] == [p.id]


def test_struggled_completion_resets_to_shortest_interval(client, db_session):
    headers = auth_headers(client, "rev3@example.com", "testpass123")
    me = client.get("/api/auth/me", headers=headers).json()
    p = add_solved_problem(db_session, me["id"])

    client.post(f"/api/revision/{p.id}/mark", headers=headers)
    # advance once with a good confidence rating...
    client.post(f"/api/revision/{p.id}/complete", json={"confidence": 5}, headers=headers)
    # ...then struggle on the next one
    resp = client.post(f"/api/revision/{p.id}/complete", json={"confidence": 1}, headers=headers)
    assert resp.status_code == 200

    revision = db_session.query(Revision).filter(Revision.problem_id == p.id).first()
    # default ladder is [3, 10, 30] -- struggling must reset to stage 0
    # (the 3-day interval), never continue advancing toward 30
    assert revision.interval_stage == 0
    assert revision.next_revision_date == date.today() + timedelta(days=3)


def test_cannot_mark_another_users_problem_for_revision(client, db_session):
    headers_a = auth_headers(client, "revusera@example.com", "testpass123")
    me_a = client.get("/api/auth/me", headers=headers_a).json()
    p = add_solved_problem(db_session, me_a["id"])

    headers_b = auth_headers(client, "revuserb@example.com", "testpass123")
    resp = client.post(f"/api/revision/{p.id}/mark", headers=headers_b)

    assert resp.status_code == 404


def test_cannot_complete_another_users_revision(client, db_session):
    headers_a = auth_headers(client, "revusera2@example.com", "testpass123")
    me_a = client.get("/api/auth/me", headers=headers_a).json()
    p = add_solved_problem(db_session, me_a["id"])
    client.post(f"/api/revision/{p.id}/mark", headers=headers_a)

    headers_b = auth_headers(client, "revuserb2@example.com", "testpass123")
    resp = client.post(f"/api/revision/{p.id}/complete", json={"confidence": 5}, headers=headers_b)

    assert resp.status_code == 404
