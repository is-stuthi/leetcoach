import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import Base, engine
from app.routes import auth, problems, dashboard, history, revision, recommendation, topics, settings, sync

app = FastAPI(title="LeetCoach API")

# Local dev origins are always allowed; the deployed frontend's origin (e.g.
# https://leetcoach.vercel.app) is added via an env var set on Render, since
# it doesn't exist yet at the time this code is written and will differ
# per-deployment -- hardcoding it here would mean editing code to change it.
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra_origin = os.environ.get("FRONTEND_ORIGIN")
allow_origins = _default_origins + ([_extra_origin] if _extra_origin else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # creates tables if missing; does not seed data --
    # run `python -m app.database.seed` once to populate mock data
    Base.metadata.create_all(bind=engine)


app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(dashboard.router)
app.include_router(history.router)
app.include_router(revision.router)
app.include_router(recommendation.router)
app.include_router(topics.router)
app.include_router(settings.router)
app.include_router(sync.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
