from fastapi import APIRouter, HTTPException
from db.supabase_client import supabase
from datetime import datetime, timezone
from decimal import Decimal

router = APIRouter()


# public routes, mostly for just analytics and general info

# GET /stats
@router.get("/stats")
def get_api_stats():
    """
    Returns general stats about API usage and system data.
    """
    try:
        user_count = len(supabase.table("users").select("id").execute().data or [])
        coin_count = len(supabase.table("coins").select("id").execute().data or [])
        trade_count = len(supabase.table("trades").select("id").execute().data or [])

        api_total = supabase.table("api_usage").select("count").execute().data or []
        total_requests = sum(row["count"] for row in api_total) if api_total else 0

        top_endpoints = (
            supabase.table("api_usage")
            .select("endpoint, method, count, avg_response_ms, last_used")
            .order("count", desc=True)
            .limit(5)
            .execute()
            .data or []
        )

        return {
            "service": "coinbrew-api",
            "version": "v2",
            "total_users": user_count,
            "total_coins": coin_count,
            "total_trades": trade_count,
            "total_requests": total_requests,
            "top_endpoints": top_endpoints,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching API stats: {str(e)}")



# GET /health
@router.get("/health")
def health_check():
    """Confirms server and supabase are operational."""

    try:
        supabase.table("users").select("id").limit(1).execute()
        return {
            "status": "ok",
            "service": "coinbrew-api",
            "version": "v2",
            "uptime": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")