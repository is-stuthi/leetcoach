# LeetCoach

A personal LeetCode training dashboard: track solved problems, keep notes, run a
spaced-repetition revision schedule, and get transparent, rule-based
recommendations for what to solve next.

Ships with realistic seeded/mock data so it works immediately, and can sync
your real public LeetCode profile — by username only, no password or session
cookie, ever.

## Stack

- **Frontend:** React + TypeScript + Vite, `react-router-dom`, `recharts`
- **Backend:** Python + FastAPI + SQLAlchemy
- **Database:** SQLite (file-based, `backend/leetcoach.db`)

## Project structure

```
backend/
  app/
    main.py                    FastAPI app, CORS, router mounting
    database/
      db.py                    SQLAlchemy engine/session
      seed.py                  seeds ~40 realistic mock problems
    models/
      models.py                SQLAlchemy models
      schemas.py                Pydantic request/response schemas
    routes/                    one router per resource (problems, dashboard,
                                history, revision, recommendation, topics,
                                settings, sync)
    recommendation/
      engine.py                 rule-based recommendation scoring (isolated)
    services/
      leetcode_service.py       real LeetCode public-GraphQL client (fetch-only,
                                 no DB access -- see routes/sync.py for that)
frontend/
  src/
    api/                       typed fetch client
    components/                shared UI (tables, badges, layout, charts)
    pages/                     Dashboard, Problems, Revision, Recommendations,
                                Notebook, Settings, History
```

## Running it

### Backend

**Windows (PowerShell)** — run each line separately (`&&` is not a valid
separator in PowerShell):

```powershell
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m app.database.seed    # first run only — seeds ~40 mock problems
uvicorn app.main:app --port 8000 --reload
```

If `Activate.ps1` is blocked by execution policy, skip activation and call
the venv directly instead: `./venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload`
(prefix `pip`/seed commands with `./venv/Scripts/python.exe -m` the same way).

**macOS / Linux (bash/zsh):**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.database.seed    # first run only — seeds ~40 mock problems
uvicorn app.main:app --port 8000 --reload
```

API available at `http://127.0.0.1:8000`, interactive docs at `/docs`.

Re-run `python -m app.database.seed` any time to reset to the original demo
state (it drops and recreates all tables).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`. The frontend expects the backend on
`http://127.0.0.1:8000` (see `frontend/src/api/client.ts`).

## What's implemented

- **Dashboard** — solved counts, difficulty split, weekly count, current
  streak, difficulty/topic/activity charts, revisions due, bookmarks, recent
  solves, and a "What should I solve today?" panel.
- **Problems** — full table with search, difficulty/topic/solved/bookmark/
  revision filters, and sorting.
- **Revision** — spaced repetition with a 3 → 10 → 30 day default ladder
  (configurable in Settings). Completing a revision with confidence ≤ 2
  resets to the shortest interval instead of advancing, so struggled
  problems come back sooner. Manually schedule any solved problem for
  revision.
- **Recommendations** — transparent rule-based scoring (`backend/app/
  recommendation/engine.py`), no ML/LLM. Picks one new problem, one due
  revision (if any), and one variety/extra-practice problem, each with a
  plain-English reasons list built directly from the score components that
  fired. Also includes the topic-strength/weakness analysis (strong /
  needs practice / low-coverage), with the explicit rule that a topic is
  only called "weak" from an actual low-confidence solve, never just from a
  low solve count.
- **Notebook** — per-problem notes, key insight, mistake made, time/space
  complexity, confidence rating, bookmark and revision toggles.
- **Settings** — daily targets, preferred difficulty, priority topics,
  revision intervals, and real LeetCode sync (see below).
- **Solving History** (linked from the Dashboard, not in the main nav) —
  chronological log of every solve/revision plus an activity heatmap.
- **LeetCode Sync** — a "Sync LeetCode" button in Settings pulls your real
  public profile. See the dedicated section below for how it works and its
  limits.

Data persists in `backend/leetcoach.db` (SQLite) and survives backend
restarts.

## Where the main logic lives

- Recommendation scoring: `backend/app/recommendation/engine.py`
- Revision/spaced-repetition rules: `backend/app/routes/revision.py`
- Topic strength/weakness classification: `backend/app/routes/topics.py`
- LeetCode API client: `backend/app/services/leetcode_service.py`
- Sync orchestration (DB upserts): `backend/app/routes/sync.py`
- Seed data (40 problems across 10 topics, realistic dates): `backend/app/database/seed.py`

## LeetCode Sync

Settings has a "LeetCode Username" field and a **Sync LeetCode** button. Sync
talks only to LeetCode's public GraphQL endpoint (`leetcode.com/graphql`) —
the same one leetcode.com's own pages use for public profile data. It never
asks for or accepts a password or session cookie.

Each sync does three things:

1. **Aggregate stats** (`matchedUser`) — your true, fully-accurate total
   solved count and Easy/Medium/Hard breakdown.
2. **Practice catalog refresh** (`problemsetQuestionList`) — pulls ~200 real,
   non-premium LeetCode problems across the app's 10 core topics to serve as
   the recommendation engine's candidate pool. Existing problems are updated
   in place (title/difficulty/topics); your notes, confidence, bookmarks,
   and revision schedule are never touched by this step.
3. **Recent solves** (`recentAcSubmissionList`) — marks problems solved with
   their real solve date and logs them to Solving History.

**The one real limitation, by design:** LeetCode's public API does not expose
a user's full submission history without an authenticated session — only
their ~20 most recent accepted submissions. This app deliberately never asks
for that session cookie, so a sync can only individually mark your ~20 most
recent solves, even though step 1 shows your true lifetime total. Settings
shows both numbers side by side after a sync so this is never hidden. Running
sync again later naturally catches newly-solved problems as they age into
that recent-20 window.

**Idempotent and safe to re-run:** matching is by LeetCode's stable numeric
problem ID, so re-syncing never creates duplicate problems or duplicate
history entries, and never overwrites your notes/confidence/bookmarks/
revision state — only `solved`, `date_solved`, and catalog metadata
(title/difficulty/topics/url) are sync-owned.

**Seed data is unaffected** — `python -m app.database.seed` still resets
everything to the original 40-problem mock demo at any time; sync and seed
are just two different ways of populating the same schema.

### Auditing the recommendation engine against real data

Real sync data (tested against a real high-volume public profile) surfaced
one design flaw, since fixed: `backend/app/routes/topics.py` originally
labeled a topic "strong" by `solved / total_in_catalog >= 60%`. That ratio
breaks down once the catalog is sourced from real LeetCode data (100+
problems per topic) while the public API can only ever confirm a small,
capped number of individual solves — the 60% bar became permanently
unreachable for any real synced account, however skilled. It's now judged by
an absolute solved-count floor plus confidence instead, which holds up at
both the seed catalog's scale (~5 problems/topic) and a real synced
catalog's scale (100+ problems/topic).

The engine also now surfaces "am I repeatedly solving the same type of
problem?" as an explicit insight on the Recommendations page (`
_repetition_insight` in `engine.py`) — previously this was only handled
implicitly via a scoring penalty, with nothing shown to the user directly.
The other questions this app is meant to answer were already covered:
what-to-solve-today and what-to-revise-today by the recommendation cards,
per-pick "why" by each card's reasons list, and weak/barely-covered topics
by the Topic Analysis section.
