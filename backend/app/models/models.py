from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    leetcode_id = Column(Integer, index=True, nullable=False)
    title = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # Easy / Medium / Hard
    topics = Column(JSON, nullable=False, default=list)  # list[str]
    url = Column(String, nullable=False)
    slug = Column(String, nullable=True)  # LeetCode titleSlug, used for sync matching
    source = Column(String, nullable=False, default="seed")  # "seed" | "synced" | "sample"

    solved = Column(Boolean, default=False)
    date_solved = Column(Date, nullable=True)

    bookmarked = Column(Boolean, default=False)
    confidence = Column(Integer, nullable=True)  # 1-5
    needs_revision = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    note = relationship("Note", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    revision = relationship("Revision", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    solve_logs = relationship("SolveLog", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "leetcode_id", name="uq_problem_user_leetcode_id"),
    )


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), unique=True, nullable=False)

    notes_text = Column(Text, default="")
    key_insight = Column(Text, default="")
    mistake = Column(Text, default="")
    time_complexity = Column(String, default="")
    space_complexity = Column(String, default="")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    problem = relationship("Problem", back_populates="note")


class Revision(Base):
    __tablename__ = "revisions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), unique=True, nullable=False)

    revision_count = Column(Integer, default=0)
    interval_stage = Column(Integer, default=0)  # index into revision_intervals
    last_revised_at = Column(Date, nullable=True)
    next_revision_date = Column(Date, nullable=True)
    active = Column(Boolean, default=True)  # false once all stages completed & not re-flagged

    problem = relationship("Problem", back_populates="revision")


class SolveLog(Base):
    __tablename__ = "solve_log"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String, nullable=False)  # "new" or "revision"

    problem = relationship("Problem", back_populates="solve_logs")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    leetcode_username = Column(String, nullable=True, default="")
    daily_target_new = Column(Integer, default=1)
    daily_target_revision = Column(Integer, default=1)
    preferred_difficulty = Column(String, default="Medium")
    priority_topics = Column(JSON, default=list)
    revision_intervals = Column(JSON, default=lambda: [3, 10, 30])


class SyncStatus(Base):
    """Tracks the most recent LeetCode sync attempt, one row per user."""
    __tablename__ = "sync_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    username_synced = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    success = Column(Boolean, default=False)
    problems_synced = Column(Integer, default=0)   # catalog problems inserted/updated
    newly_solved = Column(Integer, default=0)      # problems newly marked solved this run
    warnings = Column(JSON, default=list)          # list[str] -- non-fatal issues
    errors = Column(JSON, default=list)            # list[str] -- fatal issues for this run

    # aggregate counts as reported directly by LeetCode's own profile stats,
    # for comparison against what we could individually track (see README)
    reported_easy = Column(Integer, nullable=True)
    reported_medium = Column(Integer, nullable=True)
    reported_hard = Column(Integer, nullable=True)
    reported_total = Column(Integer, nullable=True)
