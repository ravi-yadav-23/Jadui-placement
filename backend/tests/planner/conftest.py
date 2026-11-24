"""Fixtures for planner v2 tests: auth + fake LLM from the resume tests, all v2 routers, and profile builders."""

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.coach.api import router as coach_router
from app.core.db import InMemoryDatabase, get_db
from app.core.errors import register_error_handlers
from app.dashboard.api import router as dashboard_router
from app.interview.api import router as interview_router
from app.planner.api import router as planner_router
from app.planner.schemas import PlannerProfile
from app.resume.api import router as resume_router
from tests.resume.conftest import _test_settings  # noqa: F401  (autouse: test JWT secret + fake LLM)

MONDAY = date(2026, 12, 7)


def profile(**overrides) -> PlannerProfile:
    """A 3rd-year B.Tech student targeting product companies, 2 h weekdays + 5 h weekends, Python."""
    base = dict(status="student", degree="btech", year=3, goal="internship", target_role="backend",
                company_types=["product"], weekday_hours=2, weekend_hours=5, language="python",
                language_comfort=3, ratings={"dsa": 1, "os": 1, "dbms": 2, "cn": 0, "oop": 2},
                problems_solved="lt50", projects=1)
    return PlannerProfile.model_validate({**base, **overrides})


@pytest.fixture
def db() -> InMemoryDatabase:
    return InMemoryDatabase()


@pytest.fixture
def client(db) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    for router in (resume_router, interview_router, planner_router, dashboard_router, coach_router):
        app.include_router(router, prefix="/api/v2")
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
