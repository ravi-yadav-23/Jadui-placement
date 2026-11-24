"""Shared fixtures for resume v2 tests.

* `db`      - a fresh InMemoryDatabase per test (no Supabase needed)
* `client`  - a TestClient for an app that mounts ONLY the v2 router
* `token()` - mints a valid HS256 Supabase-style JWT for any user id
"""

import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import InMemoryDatabase, get_db
from app.core.errors import register_error_handlers
from app.resume.api import router

TEST_SECRET = "test-secret-at-least-32-bytes-long-123456"


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "fake")


def make_token(user_id: str, expires_in: int = 3600, secret: str = TEST_SECRET) -> str:
    claims = {"sub": user_id, "email": f"{user_id}@test.dev", "aud": "authenticated",
              "exp": int(time.time()) + expires_in}
    return jwt.encode(claims, secret, algorithm="HS256")


def auth(user_id: str = "user-a") -> dict:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture
def db() -> InMemoryDatabase:
    return InMemoryDatabase()


@pytest.fixture
def client(db) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router, prefix="/api/v2")
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
