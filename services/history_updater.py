from db.supabase_client import supabase
from decimal import Decimal

def update_coin_history(coin_id: int, new_price: Decimal, range_str: str):
    """Append a new price to coin history arrays, maintaining rolling limits."""
    ranges = {"12h": 12, "24h": 24, "1w": 7 * 24, "max": None}

    if range_str not in ranges:
        range_str = "24h"

    res = (
        supabase.table("coin_history")
        .select("id, prices")
        .eq("coin_id", coin_id)
        .eq("range", range_str)
        .single()
        .execute()
    )

    if res.data:
        prices = res.data["prices"] or []
        prices.append(float(new_price))

        max_len = ranges[range_str]
        if max_len and len(prices) > max_len:
            prices = prices[-max_len:]  # keep recent

        supabase.table("coin_history").update({"prices": prices}).eq("id", res.data["id"]).execute()
    else:
        supabase.table("coin_history").insert({
            "coin_id": coin_id,
            "prices": [float(new_price)],
            "range": range_str
        }).execute()
