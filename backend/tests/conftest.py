"""Shared fixtures: in-memory SQLite DB and an httpx AsyncClient against the app."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_db
from backend.main import app
from backend.models.base import Base

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # one shared in-memory DB across sessions/threads
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Background tasks open their own session via webhooks.SessionLocal —
    # point it at the test engine so runs never touch the dev DB.
    import backend.api.routes.webhooks as webhooks_module

    monkeypatch.setattr(webhooks_module, "SessionLocal", TestSessionLocal)
    # ASGITransport hits the app in-process; lifespan (seeding against the real
    # dev DB) is intentionally not run.
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()
