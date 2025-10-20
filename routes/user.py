from fastapi import APIRouter, Depends, HTTPException
from db.supabase_client import supabase
from schemas.user import UserProfileResponse, UserMeResponse
from .dependencies import get_current_user

router = APIRouter()

# GET /me
@router.get("/me", response_model=UserMeResponse)
def get_user_me(current_user=Depends(get_current_user)):
    """
    Returns the currently logged-in user's full info (including email)
    """
    try:
        user_record = (
            supabase.table("users")
            .select("*")
            .eq("id", current_user.id)
            .single()
            .execute()
        )

        if not user_record.data:
            raise HTTPException(status_code=404, detail="User not found")

        return user_record.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user data: {str(e)}")


# GET /{user_id}/profile
@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(user_id: str, current_user=Depends(get_current_user)):
    """
    Get a user's full profile (with wallet + trades)
    If it's the current user, email is included.
    """
    try:
        # base user info
        user_res = (
            supabase.table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_res.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_res.data

        # Hide private info if not self
        if user["id"] != current_user.id:
            user.pop("email", None)

        # wallet
        wallet_res = (
            supabase.table("wallets")
            .select("coin_id, amount")
            .eq("user_id", user_id)
            .execute()
        )

        portfolio_value = float(user["balance"])
        wallet_list = []

        for w in wallet_res.data or []:
            coin_res = (
                supabase.table("coins")
                .select("name, symbol, current_price, img_url")
                .eq("id", w["coin_id"])
                .single()
                .execute()
            )
            if coin_res.data:
                coin_val = float(w["amount"]) * float(coin_res.data["current_price"])
                portfolio_value += coin_val
                wallet_list.append({
                    "coin_name": coin_res.data["name"],
                    "symbol": coin_res.data["symbol"],
                    "amount": float(w["amount"]),
                    "current_price": float(coin_res.data["current_price"]),
                    "value": coin_val,
                    "img_url": coin_res.data.get("img_url")
                })

        # trades
        trades_res = (
            supabase.table("trades")
            .select("coin_id, amount, price_per_coin, timestamp, buyer_id, seller_id")
            .or_(f"buyer_id.eq.{user_id},seller_id.eq.{user_id}")
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

        trade_history = []
        for t in trades_res.data or []:
            coin_info = (
                supabase.table("coins")
                .select("symbol, name")
                .eq("id", t["coin_id"])
                .single()
                .execute()
            )
            trade_history.append({
                "coin_symbol": coin_info.data["symbol"] if coin_info.data else "UNKNOWN",
                "amount": float(t["amount"]),
                "price_per_coin": float(t["price_per_coin"]),
                "timestamp": t["timestamp"],
                "trade_type": "buy" if t["buyer_id"] == user_id else "sell"
            })

        return {
            "user": user,
            "portfolio": {
                "wallets": wallet_list,
                "total_value": round(portfolio_value, 2)
            },
            "recent_trades": trade_history
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")
