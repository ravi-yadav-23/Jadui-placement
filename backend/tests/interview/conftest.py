"""Fixtures for interview v2 tests: same auth/fake-LLM setup as the resume tests, plus both routers
(the resume and JD tracks need a parsed resume / JD from the resume pillar)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.db import InMemoryDatabase, get_db
from app.core.errors import register_error_handlers
from app.interview.api import router as interview_router
from app.resume.api import router as resume_router
from tests.resume.conftest import _test_settings  # noqa: F401  (autouse fixture: test JWT secret + fake LLM)


@pytest.fixture
def db() -> InMemoryDatabase:
    return InMemoryDatabase()


@pytest.fixture
def client(db) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(resume_router, prefix="/api/v2")
    app.include_router(interview_router, prefix="/api/v2")
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
