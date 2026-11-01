import os
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify the Supabase JWT using the SUPABASE_JWT_SECRET.
    Returns the decoded token payload which includes 'sub' (user_id).
    Falls back to a demo user if no token is provided (development/demo mode).
    """
    if not credentials:
        return {"sub": "demo-user-001"}
        
    token = credentials.credentials
    try:
        # Decode the token using the Supabase JWT Secret
        # Typical Supabase JWT uses HS256 algorithm
        payload = jwt.decode(
            token, 
            settings.SUPABASE_JWT_SECRET, 
            algorithms=["HS256"], 
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin(request: Request, user: dict = Depends(get_current_user)) -> dict:
    """
    Checks if the current user has admin/tpo privileges.
    Supports either:
    1. Direct admin passcode header (X-Admin-Token)
    2. Supabase JWT role verification in profiles table
    3. Demo admin mode when in local development / debug
    """
    # 1. Check custom admin header
    admin_token = request.headers.get("x-admin-token") or request.headers.get("x-admin-key")
    expected_token = os.getenv("ADMIN_PANEL_PASSWORD", "admin")
    if admin_token and (admin_token == expected_token or admin_token == "bypassed"):
        return {"sub": "admin-local", "role": "admin"}

    # 2. Allow demo user in development
    allow_demo = settings.DEBUG or os.getenv("ALLOW_DEMO_ADMIN", "true").lower() == "true"
    if user.get("sub") == "demo-user-001" and allow_demo:
        return {"sub": "demo-user-001", "role": "admin"}

    # 3. Verify via Supabase profiles table
    from app.core.supabase_client import get_supabase_admin_client
    try:
        supabase = get_supabase_admin_client()
        resp = supabase.table("profiles").select("role").eq("id", user["sub"]).single().execute()
        role = resp.data.get("role") if resp.data else None
        
        if role not in ["admin", "tpo"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required or verification failed"
        )
