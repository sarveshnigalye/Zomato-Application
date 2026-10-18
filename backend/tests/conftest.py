"""
Shared pytest fixtures for the backend test suite.
Sets up an in-memory SQLite test database and a TestClient
that replaces the production DB session dependency.
"""

import os
import sys
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.models.database import Base, get_db


# ---------------------------------------------------------------------------
# In-memory SQLite engine for test isolation
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    """Override the production DB session with an isolated in-memory session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the in-memory test database once per session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def client(setup_test_db):
    """
    TestClient with the production DB session overridden by the
    in-memory SQLite test database. Safe for parallel module-scoped use.
    """
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
