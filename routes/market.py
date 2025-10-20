from fastapi import APIRouter, HTTPException, Query
from db.supabase_client import supabase
from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timedelta, timezone

# Market routes


router = APIRouter()


# GET /market/top
@router.get("/top")
def get_market_top(
    limit: int = Query(10, description="Number of top coins to retrieve"),
    order: str = Query("desc", description="Order of sorting: 'asc' or 'desc'"),
):
    """
    Returns top or bottom performing coins based on market cap
    """

    try:
        desc = True if order == "desc" else False
        res = (
            supabase.table("coins")
            .select("*")
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="No coins found")
        
        coins = []

        for c in res.data:
            try:
                market_cap = Decimal(c["current_price"]) * Decimal(c["circulating_supply"])
            except Exception:
                market_cap = Decimal(0)


            coins.append({
                "id": c["id"],
                "name": c["name"],
                "symbol": c["symbol"],
                "img_url": c.get("img_url"),
                "creator_id": c.get("creator_id"),
                "total_supply": float(c["total_supply"]) if c.get("total_supply") else None,
                "circulating_supply": float(c["circulating_supply"]) if c.get("circulating_supply") else None,
                "current_price": float(c["current_price"]) if c.get("current_price") else None,
                "initial_market_cap": float(c["initial_market_cap"]) if c.get("initial_market_cap") else None,
                "market_cap": float(market_cap),
                "created_at": c.get("created_at")
            })

        coins.sort(key=lambda x: x["market_cap"], reverse=desc)

        return {"coins": coins[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
            

# GET /market/leaderboard
@router.get("/leaderboard")
def get_market_leaderboard(limit: int = 10):
    """Returns top users ranked"""

    try:
        users = supabase.table("users").select("id, username, balance").execute().data
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        
        leaderboard = []
        for u in users:
            wallets = supabase.table("wallets").select("coin_id, amount").eq("user_id", u["id"]).execute().data
            total_value = Decimal(u["balance"])

            for w in wallets:
                coin = supabase.table("coins").select("current_price").eq("id", w["coin_id"]).execute().data
                if coin:
                    total_value += Decimal(coin[0]["current_price"]) * Decimal(w["amount"])

            leaderboard.append({
                "username": u["username"],
                "total_value": float(total_value)
            })

        leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
        return {"leaderboard": leaderboard[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# GET /market/recent-trades
@router.get("/recent-trades")
def get_market_recent_trades(
    limit: int = Query(10, ge=1, le=100, description="Number of trades to return (1–100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    symbol: Optional[str] = Query(None, description="Filter trades by coin symbol"),
):
    """
    Returns recent global trades with optional filtering by symbol,
    and pagination support.
    """
    try:
        # if symbol filter is provided, resolve coin_id
        coin_id = None
        if symbol:
            coin_data = (
                supabase.table("coins")
                .select("id")
                .eq("symbol", symbol.upper())
                .single()
                .execute()
                .data
            )
            if not coin_data:
                raise HTTPException(status_code=404, detail="Coin not found")
            coin_id = coin_data["id"]

        # build base query
        query = (
            supabase.table("trades")
            .select("id, buyer_id, seller_id, coin_id, amount, price_per_coin, timestamp")
            .order("timestamp", desc=True)
            .range(offset, offset + limit - 1)
        )

        if coin_id:
            query = query.eq("coin_id", coin_id)

        trades = query.execute().data or []

        trade_list = []
        for t in trades:
            coin = (
                supabase.table("coins")
                .select("symbol, name, img_url")
                .eq("id", t["coin_id"])
                .single()
                .execute()
                .data
            )
            buyer = (
                supabase.table("users")
                .select("username")
                .eq("id", t["buyer_id"])
                .single()
                .execute()
                .data
                if t.get("buyer_id") else None
            )
            seller = (
                supabase.table("users")
                .select("username")
                .eq("id", t["seller_id"])
                .single()
                .execute()
                .data
                if t.get("seller_id") else None
            )

            trade_list.append({
                "id": t["id"],
                "coin": {
                    "symbol": coin["symbol"] if coin else "UNKNOWN",
                    "name": coin["name"] if coin else None,
                    "img_url": coin["img_url"] if coin else None
                },
                "amount": float(t["amount"]),
                "price_per_coin": float(t["price_per_coin"]),
                "total_value": float(Decimal(t["amount"]) * Decimal(t["price_per_coin"])),
                "buyer": buyer["username"] if buyer else "N/A",
                "seller": seller["username"] if seller else "N/A",
                "timestamp": t["timestamp"]
            })

        return {
            "count": len(trade_list),
            "offset": offset,
            "limit": limit,
            "symbol": symbol,
            "trades": trade_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent trades: {str(e)}")
