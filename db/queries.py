from config import supabase
from typing import Optional

# Users
def get_user_by_username(username: str):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def get_user_by_id(user_id: int):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def create_user(username: str, hashed_password: str, balance: float = 1500.0):
    supabase.table("users").insert({
        "username": username,
        "password": hashed_password,
        "balance": balance
    }).execute()

def update_user_balance(user_id: int, new_balance: float):
    supabase.table("users").update({"balance": new_balance}).eq("id", user_id).execute()


# Coins
def get_coin_by_symbol(symbol: str):
    res = supabase.table("coins").select("*").eq("symbol", symbol).execute()
    return res.data[0] if res.data else None

def get_coin_by_id(coin_id: int):
    res = supabase.table("coins").select("*").eq("id", coin_id).execute()
    return res.data[0] if res.data else None

def get_all_coins(min_price: Optional[float] = None, max_price: Optional[float] = None,
                  sort_by: Optional[str] = None, limit: int = 10, offset: int = 0):
    query = supabase.table("coins").select("*")
    if min_price is not None:
        query = query.gte("current_price", min_price)
    if max_price is not None:
        query = query.lte("current_price", max_price)
    if sort_by in ["name", "symbol", "current_price"]:
        query = query.order(sort_by, ascending=True)
    query = query.range(offset, offset + limit - 1)
    return query.execute().data

def create_coin(img_url: str, name: str, symbol: str, creator_id: int):
    supabase.table("coins").insert({
        "img_url": img_url,
        "name": name,
        "symbol": symbol,
        "creator_id": creator_id,
        "total_supply": 1_000_000_000,
        "circulating_supply": 1_000_000_000,
        "current_price": 0.001,
        "initial_market_cap": 1000
    }).execute()

def update_coin_price(coin_id: int, new_price: float):
    supabase.table("coins").update({"current_price": new_price}).eq("id", coin_id).execute()


# Wallets
def get_wallet(user_id: int, coin_id: int):
    res = supabase.table("wallets").select("*").eq("user_id", user_id).eq("coin_id", coin_id).execute()
    return res.data[0] if res.data else None

def create_wallet(user_id: int, coin_id: int, amount: float):
    supabase.table("wallets").insert({
        "user_id": user_id,
        "coin_id": coin_id,
        "amount": amount
    }).execute()

def update_wallet(user_id: int, coin_id: int, new_amount: float):
    supabase.table("wallets").update({"amount": new_amount}).eq("user_id", user_id).eq("coin_id", coin_id).execute()

def safe_update_wallet(user_id: int, coin_id: int, delta_amount: float):
    wallet = get_wallet(user_id, coin_id)
    if wallet:
        new_amount = wallet["amount"] + delta_amount
        if new_amount < 0:
            raise ValueError("Insufficient coin balance")
        update_wallet(user_id, coin_id, new_amount)
    else:
        if delta_amount < 0:
            raise ValueError("Insufficient coin balance")
        create_wallet(user_id, coin_id, delta_amount)

def get_user_wallets(user_id: int):
    res = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
    return res.data


# Trades
def record_trade(buyer_id: Optional[int], seller_id: Optional[int], coin_id: int, amount: float, price_per_coin: float):
    supabase.table("trades").insert({
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "coin_id": coin_id,
        "amount": amount,
        "price_per_coin": price_per_coin
    }).execute()

def buy_coin(buyer_id: int, coin_id: int, amount: float, price_per_coin: float):
    buyer = get_user_by_id(buyer_id)
    total_cost = amount * price_per_coin
    if buyer["balance"] < total_cost:
        raise ValueError("Insufficient USD balance")
    update_user_balance(buyer_id, buyer["balance"] - total_cost)
    safe_update_wallet(buyer_id, coin_id, amount)
    record_trade(buyer_id, None, coin_id, amount, price_per_coin)

def sell_coin(seller_id: int, coin_id: int, amount: float, price_per_coin: float):
    wallet = get_wallet(seller_id, coin_id)
    if not wallet or wallet["amount"] < amount:
        raise ValueError("Insufficient coin balance")
    safe_update_wallet(seller_id, coin_id, -amount)
    seller = get_user_by_id(seller_id)
    update_user_balance(seller_id, seller["balance"] + amount * price_per_coin)
    record_trade(None, seller_id, coin_id, amount, price_per_coin)


# Coin History
def add_coin_history(coin_id: int, prices: list, range_str: str):
    supabase.table("coin_history").insert({
        "coin_id": coin_id,
        "prices": prices,
        "range": range_str
    }).execute()

def get_coin_history(coin_id: int, range_str: str):
    res = supabase.table("coin_history").select("*").eq("coin_id", coin_id).eq("range", range_str).execute()
    return res.data


# Leaderboard
def get_leaderboard(top_n: int = 10):
    users = supabase.table("users").select("*").execute().data
    leaderboard = []
    for u in users:
        wallets = get_user_wallets(u["id"])
        total_coins_value = sum(get_coin_by_id(w["coin_id"])["current_price"] * w["amount"] for w in wallets)
        leaderboard.append({
            "id": u["id"],
            "username": u["username"],
            "total_value": u["balance"] + total_coins_value
        })
    leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
    return leaderboard[:top_n]


# Portfolio / User Info
def get_user_portfolio(user_id: int):
    wallets = get_user_wallets(user_id)
    portfolio = []
    total_value = 0
    for w in wallets:
        coin = get_coin_by_id(w["coin_id"])
        value = w["amount"] * coin["current_price"]
        total_value += value
        portfolio.append({
            "coin_id": coin["id"],
            "symbol": coin["symbol"],
            "amount": w["amount"],
            "current_price": coin["current_price"],
            "value": value
        })
    user = get_user_by_id(user_id)
    total_value += user["balance"]
    return {"balance": user["balance"], "coins": portfolio, "total_value": total_value}

def get_user_profile(user_id: int):
    user = get_user_by_id(user_id)
    coins_created = supabase.table("coins").select("*").eq("creator_id", user_id).execute().data
    portfolio = get_user_portfolio(user_id)
    return {
        "id": user["id"],
        "username": user["username"],
        "coins_created": [c["symbol"] for c in coins_created],
        "portfolio": portfolio
    }
