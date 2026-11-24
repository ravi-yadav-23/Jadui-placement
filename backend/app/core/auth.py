"""Strict authentication for the v2 API.

Every request must carry `Authorization: Bearer <supabase access token>`.
There is deliberately NO demo-user fallback: no valid token -> 401.

Supabase can sign tokens two ways, and the token header tells us which:
  * HS256  -> legacy shared secret (SUPABASE_JWT_SECRET)
  * ES256 / RS256 -> asymmetric keys, verified with the project's public JWKS
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import AppError

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    # PyJWKClient caches the downloaded keys, so this is one HTTP call per key rotation.
    return jwt.PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")


def decode_token(token: str) -> dict:
    """Verify signature, expiry and audience; return the claims. Raises AppError(401)."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not settings.SUPABASE_JWT_SECRET:
                raise AppError("auth_misconfigured", "HS256 token but SUPABASE_JWT_SECRET is not set", 500)
            key = settings.SUPABASE_JWT_SECRET
        else:
            key = _jwks_client().get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=[alg], audience="authenticated")
    except jwt.ExpiredSignatureError as exc:
        raise AppError("token_expired", "Session expired, please sign in again", 401) from exc
    except jwt.PyJWTError as exc:
        raise AppError("invalid_token", "Invalid authentication token", 401) from exc


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if creds is None:
        raise AppError("not_authenticated", "Sign in required", 401)
    claims = decode_token(creds.credentials)
    return CurrentUser(id=claims["sub"], email=claims.get("email"))
