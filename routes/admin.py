from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from db.supabase_client import supabase
from services.history_updater import update_coin_history
from services.auth_admin import verify_admin_key  

router = APIRouter()


def update_coin_price(coin_id: int, new_price: Decimal):
    """Update a coin's price in the database."""
    supabase.table("coins").update({
        "current_price": new_price,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", coin_id).execute()


def calculate_new_price(coin_id: int, range_str: str = "6h"):
    """Dynamic and more sensitive price recalculation based on trades."""
    coin_data = supabase.table("coins").select("*").eq("id", coin_id).execute().data
    if not coin_data:
        raise ValueError("Coin not found")

    coin = coin_data[0]
    P_current = Decimal(coin["current_price"])
    circulating_supply = Decimal(coin["circulating_supply"])

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=6)

    trades = (
        supabase.table("trades")
        .select("*")
        .eq("coin_id", coin_id)
        .gte("timestamp", window_start.isoformat())
        .execute()
        .data
    )

    # if no trades, random noise (more volatile)
    if not trades:
        volatility = Decimal("0.02")  # up to ±2%
        random_factor = Decimal(1) + Decimal(volatility) * Decimal.from_float((0.5 - __import__("random").random()) * 2)
        P_new = P_current * random_factor
    else:
        total_buy = sum(t["amount"] * t["price_per_coin"] for t in trades if t["buyer_id"])
        total_sell = sum(t["amount"] * t["price_per_coin"] for t in trades if t["seller_id"])
        net_demand = Decimal(total_buy - total_sell)

        # increased sensitivity
        alpha, beta, lambda_smooth = Decimal("0.0015"), Decimal("0.0010"), Decimal("0.5")
        price_change_factor = (alpha + beta) * (net_demand / circulating_supply)
        P_calc = P_current * (1 + price_change_factor)
        P_new = lambda_smooth * P_calc + (1 - lambda_smooth) * P_current

        # cap volatility to ±30%
        max_change = Decimal("0.3")
        P_new = max(P_current * (1 - max_change), min(P_current * (1 + max_change), P_new))

    update_coin_price(coin_id, P_new)
    update_coin_history(coin_id, P_new, range_str)
    return P_new


# POST /admin/update-market
@router.post("/update-market")
def update_market_data(admin=Depends(verify_admin_key)):
    """Recalculate all coin prices."""
    try:
        coins = supabase.table("coins").select("id").execute().data
        if not coins:
            return {"message": "No coins found."}

        updated = 0
        for coin in coins:
            calculate_new_price(coin["id"])
            updated += 1

        return {"message": f"Updated {updated} coins successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /admin/recalculate-marketcap
@router.post("/recalculate-marketcap")
def recalculate_market_cap(admin=Depends(verify_admin_key)):
    """Recalculate each coin's market cap."""
    try:
        coins = supabase.table("coins").select("id, current_price, circulating_supply").execute().data
        for coin in coins:
            market_cap = Decimal(coin["current_price"]) * Decimal(coin["circulating_supply"])
            supabase.table("coins").update({"initial_market_cap": market_cap}).eq("id", coin["id"]).execute()
        return {"message": "Market caps recalculated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /admin/refresh-coin/{symbol}
@router.post("/refresh-coin/{symbol}")
def refresh_coin_data(symbol: str, admin=Depends(verify_admin_key)):
    """Force price + history update for a specific coin."""
    try:
        coin = supabase.table("coins").select("id").eq("symbol", symbol.upper()).single().execute()
        if not coin.data:
            raise HTTPException(status_code=404, detail="Coin not found")

        new_price = calculate_new_price(coin.data["id"])
        return {"message": f"{symbol} refreshed successfully", "new_price": float(new_price)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET /admin/status
@router.get("/status")
def get_admin_status(admin=Depends(verify_admin_key)):
    """Simple status check."""
    return {"status": "Admin routes operational", "timestamp": datetime.now(timezone.utc).isoformat()}
