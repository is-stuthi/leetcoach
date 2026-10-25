"""
LeetCode sync service.

Talks to LeetCode's public GraphQL endpoint using only a username -- no
password, cookies, or session credentials, ever. This module is a pure
external-API client: it fetches and normalizes data but does not touch the
database (see routes/sync.py for the orchestration that upserts fetched data
into our tables). Keeping the boundary here means a future change to how
LeetCode's API works only touches this one file.

Known limitation (LeetCode's public API does not expose more than this
without an authenticated session cookie, which we deliberately never ask
for): `recentAcSubmissionList` only returns a user's ~20 most recent accepted
submissions. There is no public way to fetch a user's *entire* solved
history by username alone. To still be useful, sync also pulls a broad
problem catalog (independent of the user) via `problemsetQuestionList` so
the recommendation engine always has a real pool of unsolved candidates to
draw from, and reports LeetCode's own aggregate Easy/Medium/Hard totals
(which *are* fully accurate) alongside however many individual solves we
could actually identify.
"""

import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests

GRAPHQL_URL = "https://leetcode.com/graphql"
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (compatible; LeetCoach/1.0; +personal-use-dashboard)",
}
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5

RECENT_SUBMISSIONS_LIMIT = 20  # LeetCode caps this regardless of what's requested

# LeetCode topic-tag slug -> our display name, for the ~10 core patterns this
# app is built around. Any tag not listed here is dropped when normalizing a
# problem's topics (see _core_topics) -- LeetCode has ~90 tags total, and
# keeping all of them would blow up every topic-based view in this app.
CORE_TOPIC_TAGS = {
    "array": "Array",
    "hash-table": "Hash Table",
    "two-pointers": "Two Pointers",
    "sliding-window": "Sliding Window",
    "linked-list": "Linked List",
    "binary-search": "Binary Search",
    "tree": "Trees",
    "graph": "Graphs",
    "heap-priority-queue": "Heap / Priority Queue",
    "dynamic-programming": "Dynamic Programming",
}


class LeetCodeSyncError(Exception):
    """Raised for unrecoverable sync failures (user not found, API unreachable)."""


@dataclass
class LeetCodeProfileSummary:
    username: str
    total_solved: int
    easy_solved: int
    medium_solved: int
    hard_solved: int


@dataclass
class CatalogProblem:
    leetcode_id: int
    title: str
    slug: str
    difficulty: str
    topics: list[str]


@dataclass
class RecentSolve:
    slug: str
    title: str
    solved_on: date


def is_sync_available() -> bool:
    return True


def _core_topics(tags: list[dict]) -> list[str]:
    """Map LeetCode topic tags to this app's ~10 core patterns, dropping
    anything else. LeetCode's full tag vocabulary has ~90 entries (down to
    things like 'Manacher' or "Tarjan's SCC Algorithm") which would blow up
    every topic-based view (filters, priority-topic picker, strength
    analysis) built around a small, meaningful set of patterns. A synced
    problem can end up with zero topics if none of its tags map to our
    core set -- that's fine, it's still fully usable, just unfiltered by
    topic."""
    return sorted({CORE_TOPIC_TAGS[t["slug"]] for t in tags if t["slug"] in CORE_TOPIC_TAGS})


def _graphql_request(query: str, variables: dict) -> dict:
    """POST a GraphQL query with retry/backoff. Raises LeetCodeSyncError on
    unrecoverable failure (network error exhausted retries, non-200, or a
    GraphQL-level error payload)."""
    last_error: Optional[str] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            last_error = f"network error contacting LeetCode: {e}"
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue

        if resp.status_code == 429:
            last_error = "rate limited by LeetCode (429)"
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue
        if resp.status_code >= 500:
            last_error = f"LeetCode server error ({resp.status_code})"
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue
        if resp.status_code != 200:
            raise LeetCodeSyncError(f"LeetCode returned HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except ValueError as e:
            raise LeetCodeSyncError(f"malformed JSON from LeetCode: {e}")

        if "errors" in payload and payload["errors"]:
            messages = "; ".join(e.get("message", str(e)) for e in payload["errors"])
            raise LeetCodeSyncError(f"LeetCode API error: {messages}")

        data = payload.get("data")
        if data is None:
            raise LeetCodeSyncError("LeetCode response had no data")
        return data

    raise LeetCodeSyncError(last_error or "LeetCode request failed after retries")


def fetch_public_profile(username: str) -> LeetCodeProfileSummary:
    """Fetch aggregate solved counts for a public username. These totals are
    fully accurate (unlike the per-problem history below)."""
    query = """
    query userProfile($username: String!) {
      matchedUser(username: $username) {
        username
        submitStats {
          acSubmissionNum { difficulty count }
        }
      }
    }
    """
    data = _graphql_request(query, {"username": username})
    matched = data.get("matchedUser")
    if not matched:
        raise LeetCodeSyncError(f"no public LeetCode profile found for username '{username}'")

    counts = {row["difficulty"]: row["count"] for row in matched["submitStats"]["acSubmissionNum"]}
    return LeetCodeProfileSummary(
        username=matched["username"],
        total_solved=counts.get("All", 0),
        easy_solved=counts.get("Easy", 0),
        medium_solved=counts.get("Medium", 0),
        hard_solved=counts.get("Hard", 0),
    )


@dataclass
class RecentSolvesResult:
    solves: list[RecentSolve]
    hit_api_limit: bool  # True if the raw feed came back at the ~20 cap


def fetch_recent_accepted(username: str, limit: int = RECENT_SUBMISSIONS_LIMIT) -> RecentSolvesResult:
    """Fetch the user's most recent accepted submissions (capped by LeetCode
    at ~20 regardless of `limit`). Deduplicates repeated slugs (a problem
    resubmitted after being solved once appears more than once in the raw
    feed), keeping the earliest timestamp seen for each. `hit_api_limit` is
    computed from the *raw* response size, before dedup, since a run of
    duplicate slugs could otherwise mask that the cap was hit."""
    query = """
    query recentAcSubmissions($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        title
        titleSlug
        timestamp
      }
    }
    """
    data = _graphql_request(query, {"username": username, "limit": limit})
    raw = data.get("recentAcSubmissionList") or []

    earliest_by_slug: dict[str, RecentSolve] = {}
    for row in raw:
        try:
            solved_on = datetime.fromtimestamp(int(row["timestamp"])).date()
        except (KeyError, ValueError, OSError):
            continue
        slug = row["titleSlug"]
        existing = earliest_by_slug.get(slug)
        if existing is None or solved_on < existing.solved_on:
            earliest_by_slug[slug] = RecentSolve(slug=slug, title=row["title"], solved_on=solved_on)

    return RecentSolvesResult(
        solves=list(earliest_by_slug.values()),
        hit_api_limit=len(raw) >= RECENT_SUBMISSIONS_LIMIT,
    )


@dataclass
class QuestionLookupResult:
    problem: Optional[CatalogProblem]
    skipped_reason: Optional[str] = None  # e.g. "premium-only", "not found", "lookup failed"


def fetch_question_detail(slug: str) -> QuestionLookupResult:
    """Fetch metadata for a single problem by slug. Used as a best-effort
    fallback for problems missing from the bulk catalog fetch (e.g. a
    user's recent solve in a topic/page we didn't pull). Never raises --
    failures are reported back as a skip reason so the sync can continue."""
    query = """
    query questionDetail($slug: String!) {
      question(titleSlug: $slug) {
        questionFrontendId
        title
        difficulty
        topicTags { name slug }
        isPaidOnly
      }
    }
    """
    try:
        data = _graphql_request(query, {"slug": slug})
    except LeetCodeSyncError as e:
        return QuestionLookupResult(problem=None, skipped_reason=f"lookup failed: {e}")

    q = data.get("question")
    if not q:
        return QuestionLookupResult(problem=None, skipped_reason="not found")
    if q.get("isPaidOnly"):
        return QuestionLookupResult(problem=None, skipped_reason="premium-only problem")
    try:
        leetcode_id = int(q["questionFrontendId"])
    except (KeyError, TypeError, ValueError):
        return QuestionLookupResult(problem=None, skipped_reason="malformed response")

    topics = _core_topics(q.get("topicTags", []))
    problem = CatalogProblem(
        leetcode_id=leetcode_id, title=q["title"], slug=slug,
        difficulty=q["difficulty"], topics=topics,
    )
    return QuestionLookupResult(problem=problem)


@dataclass
class CatalogResult:
    problems: list[CatalogProblem]
    warnings: list[str]


def fetch_problem_catalog(per_topic_limit: int = 30) -> CatalogResult:
    """Fetch a broad, real problem catalog spanning the app's core topics,
    to serve as the recommendation engine's candidate pool. Queries once per
    core topic tag (fast: ~10 requests) and de-duplicates by leetcode_id,
    merging topic lists for problems that match more than one tag. Premium
    (paid-only) problems are excluded since the user can't open them.

    Best-effort: if a given topic's request fails, it's skipped and recorded
    in the returned warnings rather than aborting the whole catalog fetch.
    """
    query = """
    query problemsetQuestionList($limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      questionList: questionList(categorySlug: "", limit: $limit, skip: $skip, filters: $filters) {
        data { questionFrontendId title titleSlug difficulty isPaidOnly topicTags { name slug } }
      }
    }
    """
    by_id: dict[int, CatalogProblem] = {}
    warnings: list[str] = []

    for tag_slug in CORE_TOPIC_TAGS:
        try:
            data = _graphql_request(
                query, {"limit": per_topic_limit, "skip": 0, "filters": {"tags": [tag_slug]}}
            )
        except LeetCodeSyncError as e:
            warnings.append(f"couldn't fetch '{tag_slug}' problems: {e}")
            continue

        for row in data.get("questionList", {}).get("data", []):
            if row.get("isPaidOnly"):
                continue
            try:
                leetcode_id = int(row["questionFrontendId"])
            except (KeyError, TypeError, ValueError):
                continue

            topics = _core_topics(row.get("topicTags", []))
            existing = by_id.get(leetcode_id)
            if existing:
                existing.topics = sorted(set(existing.topics) | set(topics))
            else:
                by_id[leetcode_id] = CatalogProblem(
                    leetcode_id=leetcode_id, title=row["title"], slug=row["titleSlug"],
                    difficulty=row["difficulty"], topics=topics,
                )

    return CatalogResult(problems=list(by_id.values()), warnings=warnings)
