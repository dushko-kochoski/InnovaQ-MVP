from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.base import Base

# check_same_thread=False: FastAPI may service a request and its background
# task on different threads; SQLite forbids cross-thread use by default.
_connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all() -> None:
    # Import side effect registers all models on Base.metadata
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
