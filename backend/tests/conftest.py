"""
Shared pytest fixtures.

Every test gets its own throwaway in-memory SQLite database -- never the
real leetcoach.db file. `StaticPool` keeps it alive for the whole test
(normally each new connection to an in-memory SQLite db gets its own blank
database; StaticPool pins everything to one connection so the data a test
writes is still there when it reads it back).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database.db import Base, get_db
from app.main import app
from app.models.models import User, UserSettings


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """A FastAPI TestClient wired to the throwaway db_session instead of
    the real database -- every HTTP call a test makes through this client
    reads/writes db_session, so tests can set up data directly and then
    hit the real routes exactly like the frontend would."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user(db_session):
    """A plain user row with its required settings row, for tests that
    only need an owner id and don't care about going through signup."""
    u = User(email="test@example.com", password_hash=hash_password("testpass123"))
    db_session.add(u)
    db_session.commit()
    db_session.add(UserSettings(user_id=u.id))
    db_session.commit()
    return u


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Sign up a fresh account through the real endpoint and return headers
    with its token attached -- used by API-level tests that want a real,
    end-to-end-issued token rather than one hand-built in the test."""
    client.post("/api/auth/signup", json={"email": email, "password": password})
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
