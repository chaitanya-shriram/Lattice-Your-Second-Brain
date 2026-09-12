from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from config.settings import get_settings
from storage.models import Base, Project
from utils.logger import get_logger

log = get_logger("storage.database")


def _get_engine():
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{settings.db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")  # wait 5s for a lock instead of failing immediately
        cursor.close()

    return engine


_engine = None
_SessionLocal = None


def reset_engine():
    """Discard cached engine/session — call after settings change (e.g. setup save)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _seed_defaults()
    log.info("Database initialized")


def _seed_defaults():
    from datetime import datetime
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        inbox = session.query(Project).filter(Project.is_inbox.is_(True)).first()
        if not inbox:
            inbox = Project(
                name="Personal",
                color="#37c5ab",
                position=0,
                description="Standalone tasks and errands that do not belong to any specific project.",
                is_inbox=True,
                created_at=datetime.utcnow().isoformat(),
            )
            session.add(inbox)
            session.commit()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_dependency():
    """FastAPI dependency."""
    with get_db() as session:
        yield session
