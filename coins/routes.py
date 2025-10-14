import string
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from pydantic import BaseModel, constr
from db.queries import calculate_new_price, create_coin, get_coin_by_id, get_coin_by_symbol, get_all_coins, get_coin_history, get_current_user, get_user_by_username, buy_coin, sell_coin, get_user_portfolio, get_leaderboard, get_user_profile, get_user_by_id, get_user_wallets
from typing import Optional
from utils.image import process_image, generate_filename
from config import supabase

router = APIRouter()



class GetCoinsRequest(BaseModel):
    #filtering
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort_by: Optional[str] = None  # e.g., "price", "name"
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class CoinGetHistoryRequest(BaseModel):
    symbol: str
    range: str

class BuyCoinRequest(BaseModel):
    user_id: string
    coin_symbol: str
    amount: float
    price_per_coin: float

class SellCoinRequest(BaseModel):
    user_id: string
    coin_symbol: str
    amount: float
    price_per_coin: float

VALID_RANGES = ["12h", "24h", "1w", "max"]

def validate_range(range_str: str) -> None:
    if range_str not in VALID_RANGES:
        raise HTTPException(status_code=400, detail=f"Invalid range. Must be one of {VALID_RANGES}")


@router.post("/create")
async def create_coin_endpoint(
    name: str = Form(...),
    symbol: constr(min_length=1, max_length=5) = Form(...),  # type: ignore
    current_user = Depends(get_current_user),
    file: UploadFile = File(None)
):
    try:
        existing_coin = get_coin_by_symbol(symbol)
        if existing_coin:
            raise HTTPException(status_code=400, detail="Coin with this symbol already exists")
        
        img_url = None
        if file:
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["png", "jpg", "jpeg"]:
                raise HTTPException(status_code=400, detail="Invalid image format. Only PNG and JPG are allowed.")
            
            try:
                file_bytes = await file.read()
                processed_file = process_image(file_bytes) 
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
            
            filename = generate_filename(symbol, ext)
            upload_res = supabase.storage.from_("coin-images").upload(filename, processed_file)
            if not upload_res:
                raise HTTPException(status_code=500, detail=f"Supabase upload error: {upload_res.error.message}")
            
            try:
                img_url = supabase.storage.from_("coin-images").get_public_url(filename)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting image URL: {str(e)}")
        
        try:
            create_coin(
                img_url=img_url,
                name=name,
                symbol=symbol,
                creator_id=current_user.id  # <-- use current user
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating coin in DB: {str(e)}")
        
        return {"message": "Coin created successfully", "creator": current_user.email, "img_url": img_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")


@router.post("/all")
def get_coins_endpoint(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0
):
    coins = get_all_coins(
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )

    return {"coins": coins}


@router.get("/{symbol}")
def get_coin_endpoint(symbol: str):
    coin = get_coin_by_symbol(symbol)
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")
    return {"coin": coin}



@router.get("/{symbol}/history")
def get_coin_history_endpoint(symbol: str, time_range: str = Query(...)):
    validate_range(time_range)
    coin = get_coin_by_symbol(symbol)
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")
    history = get_coin_history(coin["id"], time_range)
    if not history:
        raise HTTPException(status_code=404, detail="No history found for this coin and range")
    return {"history": history}


@router.post("/buy")
def buy_coin_endpoint(
    request: BuyCoinRequest, 
    current_user = Depends(get_current_user)
):
    coin = get_coin_by_symbol(request.coin_symbol)
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")
    
    try:
        buy_coin(current_user.id, coin["id"], request.amount, request.price_per_coin)
        calculate_new_price(coin["id"])
        return {"message": "Coin purchased successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sell")
def sell_coin_endpoint(
    request: SellCoinRequest, 
    current_user = Depends(get_current_user)
):
    coin = get_coin_by_symbol(request.coin_symbol)
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")
    
    try:
        sell_coin(current_user.id, coin["id"], request.amount, request.price_per_coin)
        calculate_new_price(coin["id"])
        return {"message": "Coin sold successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolio/{user_id}")
def get_portfolio_endpoint(user_id: string):
    portfolio = get_user_portfolio(user_id)
    return {"portfolio": portfolio}


@router.get("/leaderboard")
def get_leaderboard_endpoint(top_n: int = 10):
    leaderboard = get_leaderboard(top_n)
    return {"leaderboard": leaderboard}


@router.get("/profile/{user_id}")
def get_user_profile_endpoint(user_id: string):
    profile = get_user_profile(user_id)
    return {"profile": profile}


@router.get("/user/{user_id}")
def get_user_endpoint(user_id: string):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}


@router.get("/wallets/{user_id}")
def get_user_wallets_endpoint(user_id: string):
    wallets = get_user_wallets(user_id)
    return {"wallets": wallets}
