"""Supabase admin client for backend persistence."""

from __future__ import annotations

import os

from fastapi import HTTPException
from supabase import create_client, Client
from .config import settings

_client: Client | None = None

def get_supabase_admin_client() -> Client:
    global _client
    if _client is not None:
        return _client
        
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured")
        
    _client = create_client(url, key)
    return _client
