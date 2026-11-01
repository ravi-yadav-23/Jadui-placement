import logging
from typing import Any, Optional
from app.core.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)

def fetch_user_history(
    table: str, 
    user_id: Optional[str] = None, 
    limit: int = 10, 
    select_cols: str = "*",
    order_col: str = "created_at",
    order_desc: bool = True
) -> list[dict[str, Any]]:
    """
    Generic function to fetch user history from a Supabase table.
    """
    limit = max(1, min(limit, 50))
    supabase = get_supabase_admin_client()
    
    query = supabase.table(table).select(select_cols)
    if user_id:
        # Note: some older schemas may not have user_id on the root table.
        # This will fail gracefully if user_id doesn't exist and fallback might be needed 
        # in the calling service, or it will just filter by user_id if it does exist.
        try:
            query = query.eq("user_id", user_id)
        except Exception as e:
            logger.warning(f"Failed to apply user_id filter to {table}: {e}")

    try:
        resp = query.order(order_col, desc=order_desc).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"Error fetching history for table {table}: {e}")
        # Try a more generic query if it failed (e.g. missing column in select_cols)
        try:
            resp = supabase.table(table).select("*").order("created_at", desc=True).limit(limit).execute()
            return resp.data or []
        except Exception as e2:
            logger.error(f"Fallback history fetch failed for table {table}: {e2}")
            return []
