from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


# ---------- Auth ----------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Note ----------

class NoteBase(BaseModel):
    notes_text: str = ""
    key_insight: str = ""
    mistake: str = ""
    time_complexity: str = ""
    space_complexity: str = ""


class NoteUpdate(NoteBase):
    pass


class NoteOut(NoteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    problem_id: int
    updated_at: datetime


# ---------- Revision ----------

class RevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    problem_id: int
    revision_count: int
    interval_stage: int
    last_revised_at: Optional[date] = None
    next_revision_date: Optional[date] = None
    active: bool


# ---------- Problem ----------

class ProblemBase(BaseModel):
    leetcode_id: int
    title: str
    difficulty: str
    topics: list[str]
    url: str


class ProblemOut(ProblemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    solved: bool
    date_solved: Optional[date] = None
    bookmarked: bool
    confidence: Optional[int] = None
    needs_revision: bool
    source: str = "seed"
    note: Optional[NoteOut] = None
    revision: Optional[RevisionOut] = None


class ProblemUpdate(BaseModel):
    solved: Optional[bool] = None
    date_solved: Optional[date] = None
    bookmarked: Optional[bool] = None
    confidence: Optional[int] = None
    needs_revision: Optional[bool] = None


# ---------- Settings ----------

class UserSettingsBase(BaseModel):
    leetcode_username: str = ""
    daily_target_new: int = 1
    daily_target_revision: int = 1
    preferred_difficulty: str = "Medium"
    priority_topics: list[str] = []
    revision_intervals: list[int] = [3, 10, 30]


class UserSettingsOut(UserSettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserSettingsUpdate(BaseModel):
    leetcode_username: Optional[str] = None
    daily_target_new: Optional[int] = None
    daily_target_revision: Optional[int] = None
    preferred_difficulty: Optional[str] = None
    priority_topics: Optional[list[str]] = None
    revision_intervals: Optional[list[int]] = None


# ---------- Solve log / history ----------

class SolveLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    problem_id: int
    date: date
    type: str
    problem: ProblemOut


# ---------- Dashboard ----------

class DifficultyCounts(BaseModel):
    Easy: int = 0
    Medium: int = 0
    Hard: int = 0


class DashboardStats(BaseModel):
    total_solved: int
    total_problems: int
    difficulty_counts: DifficultyCounts
    solved_this_week: int
    current_streak: int
    topic_distribution: dict[str, int]
    activity_over_time: dict[str, int]  # date -> count
    revisions_due_today: list[ProblemOut]
    bookmarked: list[ProblemOut]
    recent_problems: list[ProblemOut]


# ---------- Recommendation ----------

class RecommendationItem(BaseModel):
    problem: ProblemOut
    kind: str  # "new" | "revision" | "extra"
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]
    insights: list[str] = []


# ---------- Topic analysis ----------

class TopicStat(BaseModel):
    topic: str
    solved: int
    total: int
    coverage: float  # solved/total
    avg_confidence: Optional[float] = None
    label: str  # "strong" | "weak" | "low_coverage" | "neutral"
    reason: str


# ---------- LeetCode sync ----------

class SyncRequest(BaseModel):
    username: Optional[str] = None  # falls back to settings.leetcode_username


class SyncStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username_synced: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    success: bool
    problems_synced: int
    newly_solved: int
    warnings: list[str] = []
    errors: list[str] = []
    reported_easy: Optional[int] = None
    reported_medium: Optional[int] = None
    reported_hard: Optional[int] = None
    reported_total: Optional[int] = None
