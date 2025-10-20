from fastapi import APIRouter, HTTPException, Depends
from db.supabase_client import supabase
from schemas.trade import TradeRequest, TradeResponse
from .dependencies import get_current_user
from decimal import Decimal
from datetime import datetime, timezone


# Trade routes

router = APIRouter()

# POST /trade/buy
@router.post("/buy", response_model=TradeResponse)
def buy_trade(trade: TradeRequest, current_user=Depends(get_current_user)):
    """
    Process a buy trade:
    - Validate balance
    - Deduct balance
    - Add wallets
    - Record trade
    """
    try:
        user_id = current_user.id

        coin = supabase.table("coins").select("*").eq("symbol", trade.coin_symbol.upper()).single().execute().data
        if not coin:
            raise HTTPException(status_code=404, detail="Coin not found")

        total_cost = Decimal(trade.amount) * Decimal(trade.price_per_coin)

        # check balance
        user = supabase.table("users").select("balance").eq("id", user_id).single().execute().data
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if Decimal(user["balance"]) < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # update balance (optimistic conditional update to reduce race conditions)
        new_balance = Decimal(user["balance"]) - total_cost
        balance_res = (
            supabase.table("users")
            .update({"balance": float(new_balance)})
            .eq("id", user_id)
            .eq("balance", float(user["balance"]))
            .execute()
        )

        # If update did not affect any rows, another concurrent update likely occurred
        if not getattr(balance_res, "data", None):
            raise HTTPException(status_code=409, detail="Balance update failed due to concurrent modification; please retry")

        # update wallets (insert or upsert)
        existing = (
            supabase.table("wallets")
            .select("id, amount")
            .eq("user_id", user_id)
            .eq("coin_id", coin["id"])
            .execute()
            .data
        )

        existing = existing[0] if existing else None

        if existing:
            new_amt = Decimal(existing["amount"]) + Decimal(trade.amount)
            wallets_res = (
                supabase.table("wallets").update({"amount": float(new_amt)}).eq("id", existing["id"]).execute()
            )
            if not getattr(wallets_res, "data", None):
                raise HTTPException(status_code=500, detail="Failed to update wallet record")
        else:
            insert_res = (
                supabase.table("wallets").insert({
                    "user_id": user_id,
                    "coin_id": coin["id"],
                    "amount": float(trade.amount)
                }).execute()
            )
            if not getattr(insert_res, "data", None):
                raise HTTPException(status_code=500, detail="Failed to create wallet record")

        # record trade
        trade_data = {
            "buyer_id": user_id,
            "seller_id": None,
            "coin_id": coin["id"],
            "amount": float(trade.amount),
            "price_per_coin": float(trade.price_per_coin),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("trades").insert(trade_data).execute()

        return {"message": "Buy successful", **trade_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing buy trade: {str(e)}")


# -----------------------------
# POST /trade/sell
# -----------------------------
@router.post("/sell", response_model=TradeResponse)
def sell_trade(trade: TradeRequest, current_user=Depends(get_current_user)):
    """
    Process a sell trade:
    - Validate user wallets
    - Reduce wallets
    - Add balance
    - Record trade
    """
    try:
        user_id = current_user.id

        coin = supabase.table("coins").select("*").eq("symbol", trade.coin_symbol.upper()).single().execute().data
        if not coin:
            raise HTTPException(status_code=404, detail="Coin not found")

        holding = (
            supabase.table("wallets")
            .select("id, amount")
            .eq("user_id", user_id)
            .eq("coin_id", coin["id"])
            .single()
            .execute()
            .data
        )

        if not holding or Decimal(holding["amount"]) < Decimal(trade.amount):
            raise HTTPException(status_code=400, detail="Not enough coins to sell")

        total_value = Decimal(trade.amount) * Decimal(trade.price_per_coin)

        # reduce wallets
        new_amt = Decimal(holding["amount"]) - Decimal(trade.amount)
        if new_amt <= 0:
            delete_res = supabase.table("wallets").delete().eq("id", holding["id"]).execute()
            if not getattr(delete_res, "data", None):
                raise HTTPException(status_code=500, detail="Failed to delete wallet record")
        else:
            wallets_res = supabase.table("wallets").update({"amount": float(new_amt)}).eq("id", holding["id"]).execute()
            if not getattr(wallets_res, "data", None):
                raise HTTPException(status_code=500, detail="Failed to update wallet record")

        # add to balance (conditional update to help avoid races)
        user = supabase.table("users").select("balance").eq("id", user_id).single().execute().data
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_balance = Decimal(user["balance"]) + total_value
        balance_res = (
            supabase.table("users")
            .update({"balance": float(new_balance)})
            .eq("id", user_id)
            .eq("balance", float(user["balance"]))
            .execute()
        )
        if not getattr(balance_res, "data", None):
            raise HTTPException(status_code=409, detail="Balance update failed due to concurrent modification; please retry")

        # record trade
        trade_data = {
            "buyer_id": None,
            "seller_id": user_id,
            "coin_id": coin["id"],
            "amount": float(trade.amount),
            "price_per_coin": float(trade.price_per_coin),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("trades").insert(trade_data).execute()

        return {"message": "Sell successful", **trade_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing sell trade: {str(e)}")
