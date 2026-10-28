import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(DB_DIR, "leetcoach.db")

# In production (Render) this is set to a real Postgres URL. Locally, with
# no env var set, it falls back to the same SQLite file as before -- so
# nothing changes for local dev.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Render (and some other hosts) hand out URLs starting "postgres://", a
# scheme SQLAlchemy 2.0 no longer accepts -- it insists on "postgresql://".
# Same database, just a stricter URL parser than Postgres's own tools use.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# check_same_thread is a SQLite-only flag (it's what lets one connection be
# reused across FastAPI's worker threads); passing it to Postgres would error.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
