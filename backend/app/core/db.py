"""Tiny data-access layer used by the v2 API.

Design choice: every read/write takes `user_id` as a required argument, so it is
impossible to write a query that forgets to scope by owner (the IDOR bugs in the old code).

Two implementations share the same methods:
  * SupabaseDatabase  - real Postgres + Storage (service-role key, so WE enforce user_id)
  * InMemoryDatabase  - plain dicts, used by tests so they run without a database
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database(Protocol):
    def insert(self, table: str, user_id: str, row: dict) -> dict: ...
    def get(self, table: str, user_id: str, row_id: str) -> dict | None: ...
    def find_one(self, table: str, user_id: str, **equals: Any) -> dict | None: ...
    def list(self, table: str, user_id: str, columns: str = "*", limit: int = 50, **equals: Any) -> list[dict]: ...
    def update(self, table: str, user_id: str, row_id: str, fields: dict) -> dict | None: ...
    def delete(self, table: str, user_id: str, row_id: str) -> None: ...
    def count_since(self, table: str, user_id: str, since_iso: str) -> int: ...
    def upsert_many(self, table: str, rows: list[dict], on_conflict: str) -> None: ...
    def log(self, table: str, row: dict) -> None: ...
    # Storage
    def upload_file(self, path: str, data: bytes, mime_type: str) -> None: ...
    def signed_url(self, path: str, expires_in: int = 300) -> str: ...
    def delete_file(self, path: str) -> None: ...


class SupabaseDatabase:
    def __init__(self) -> None:
        from supabase import create_client  # imported lazily: tests never need it

        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.bucket = settings.RESUME_STORAGE_BUCKET

    def _scoped(self, table: str, user_id: str, columns: str = "*"):
        return self.client.table(table).select(columns).eq("user_id", user_id)

    def insert(self, table, user_id, row):
        return self.client.table(table).insert({**row, "user_id": user_id}).execute().data[0]

    def get(self, table, user_id, row_id):
        rows = self._scoped(table, user_id).eq("id", row_id).limit(1).execute().data
        return rows[0] if rows else None

    def find_one(self, table, user_id, **equals):
        query = self._scoped(table, user_id)
        for column, value in equals.items():
            query = query.eq(column, value)
        rows = query.order("created_at", desc=True).limit(1).execute().data
        return rows[0] if rows else None

    def list(self, table, user_id, columns="*", limit=50, **equals):
        query = self._scoped(table, user_id, columns)
        for column, value in equals.items():
            query = query.eq(column, value)
        return query.order("created_at", desc=True).limit(limit).execute().data

    def update(self, table, user_id, row_id, fields):
        rows = (
            self.client.table(table).update(fields).eq("user_id", user_id).eq("id", row_id).execute().data
        )
        return rows[0] if rows else None

    def delete(self, table, user_id, row_id):
        self.client.table(table).delete().eq("user_id", user_id).eq("id", row_id).execute()

    def count_since(self, table, user_id, since_iso):
        resp = (
            self.client.table(table)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", since_iso)
            .execute()
        )
        return resp.count or 0

    def upsert_many(self, table, rows, on_conflict):
        if rows:
            self.client.table(table).upsert(rows, on_conflict=on_conflict, ignore_duplicates=True).execute()

    def log(self, table, row):
        self.client.table(table).insert(row).execute()

    def upload_file(self, path, data, mime_type):
        self.client.storage.from_(self.bucket).upload(path, data, {"content-type": mime_type, "upsert": "true"})

    def signed_url(self, path, expires_in=300):
        resp = self.client.storage.from_(self.bucket).create_signed_url(path, expires_in)
        return resp.get("signedURL") or resp.get("signedUrl") or ""

    def delete_file(self, path):
        self.client.storage.from_(self.bucket).remove([path])


class InMemoryDatabase:
    """Same behaviour as SupabaseDatabase, backed by dicts. Newest rows come first in list()."""

    def __init__(self) -> None:
        self.tables: dict[str, dict[str, dict]] = {}
        self.files: dict[str, bytes] = {}
        self.logs: dict[str, list[dict]] = {}

    def _table(self, table: str) -> dict[str, dict]:
        return self.tables.setdefault(table, {})

    def _owned(self, table: str, user_id: str) -> list[dict]:
        rows = [r for r in self._table(table).values() if r["user_id"] == user_id]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def insert(self, table, user_id, row):
        new = {"id": str(uuid.uuid4()), "created_at": utc_now(), **row, "user_id": user_id}
        self._table(table)[new["id"]] = new
        return dict(new)

    def get(self, table, user_id, row_id):
        row = self._table(table).get(row_id)
        return dict(row) if row and row["user_id"] == user_id else None

    def find_one(self, table, user_id, **equals):
        for row in self._owned(table, user_id):
            if all(row.get(k) == v for k, v in equals.items()):
                return dict(row)
        return None

    def list(self, table, user_id, columns="*", limit=50, **equals):
        rows = [r for r in self._owned(table, user_id) if all(r.get(k) == v for k, v in equals.items())]
        return [dict(r) for r in rows[:limit]]

    def update(self, table, user_id, row_id, fields):
        row = self._table(table).get(row_id)
        if not row or row["user_id"] != user_id:
            return None
        row.update(fields)
        return dict(row)

    def delete(self, table, user_id, row_id):
        row = self._table(table).get(row_id)
        if row and row["user_id"] == user_id:
            del self._table(table)[row_id]

    def count_since(self, table, user_id, since_iso):
        return sum(1 for r in self._owned(table, user_id) if r["created_at"] >= since_iso)

    def upsert_many(self, table, rows, on_conflict):
        keys = on_conflict.split(",")
        existing = {tuple(r.get(k) for k in keys) for r in self._table(table).values()}
        for row in rows:
            if tuple(row.get(k) for k in keys) not in existing:
                self.insert(table, row["user_id"], row)

    def log(self, table, row):
        self.logs.setdefault(table, []).append(row)

    def upload_file(self, path, data, mime_type):
        self.files[path] = data

    def signed_url(self, path, expires_in=300):
        return f"memory://{path}"

    def delete_file(self, path):
        self.files.pop(path, None)


@lru_cache(maxsize=1)
def get_db() -> Database:
    """FastAPI dependency (one shared instance). Tests replace it with `app.dependency_overrides[get_db]`."""
    if settings.DATABASE_BACKEND == "memory":
        return InMemoryDatabase()
    return SupabaseDatabase()
