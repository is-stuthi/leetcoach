from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import Base, engine
from app.routes import auth, problems, dashboard, history, revision, recommendation, topics, settings, sync

app = FastAPI(title="LeetCoach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
