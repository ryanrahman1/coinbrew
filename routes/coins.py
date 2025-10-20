from fastapi import APIRouter, File, Form, HTTPException, Depends, Query, UploadFile
from db.supabase_client import supabase
from schemas.coin import CoinCreate, CoinResponse
from typing import List, Optional
from decimal import Decimal
from .dependencies import get_current_user
from io import BytesIO
from PIL import Image
import uuid

router = APIRouter()


def generate_filename(symbol: str, ext: str) -> str:
    unique_id = uuid.uuid4().hex
    return f"{symbol.strip().upper()}-{unique_id}.{ext}"


def process_image(file_bytes: bytes, max_size=(500, 500)) -> bytes:
    img = Image.open(BytesIO(file_bytes))
    img.thumbnail(max_size, Image.LANCZOS)
    output = BytesIO()
    img_format = img.format if img.format else "JPEG"

    if img_format.upper() == "PNG":
        img.save(output, format="PNG", optimize=True)
    else:
        img.save(output, format="JPEG", quality=85, optimize=True)

    output.seek(0)
    return output.getvalue()


@router.get("/search", response_model=List[CoinResponse])
def search_coins(query: str = Query(..., description="Search query for coin name or symbol")):
    try:
        res = (
            supabase.table("coins")
            .select("*")
            .or_(f"name.ilike.%{query}%,symbol.ilike.%{query}%".replace("{query}", query))
            .execute()
        )
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching coins: {str(e)}")


@router.get("/", response_model=List[CoinResponse])
def get_coins(
    min_price: Optional[float] = Query(None),
    sort_by: Optional[str] = Query("current_price"),
    limit: int = Query(20),
    offset: int = Query(0),
    order: str = Query("desc")
):
    try:
        query = supabase.table("coins").select("*")

        if min_price is not None:
            query = query.gte("current_price", min_price)

        desc = order == "desc"
        query = query.order(sort_by, desc=desc).range(offset, offset + limit - 1)
        res = query.execute()

        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching coins: {str(e)}")


@router.get("/{symbol}", response_model=CoinResponse)
def get_coin(symbol: str):
    res = supabase.table("coins").select("*").eq("symbol", symbol.upper()).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Coin not found")
    return res.data


@router.get("/{symbol}/history")
def get_coin_history(symbol: str, time_range: str = Query("7d", description="12h | 24h | 1w | max")):
    valid_ranges = ["12h", "24h", "1w", "max"]
    if time_range not in valid_ranges:
        raise HTTPException(status_code=400, detail="Invalid time range")

    try:
        coin = supabase.table("coins").select("id").eq("symbol", symbol.upper()).single().execute()
        if not coin.data:
            raise HTTPException(status_code=404, detail="Coin not found")

        coin_id = coin.data["id"]
        history = supabase.table("coin_history").select("*").eq("coin_id", coin_id).eq("range", time_range).execute()

        if not history.data:
            return {"message": "No historical data available"}

        return {"history": history.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching coin history: {str(e)}")


@router.post("/create", response_model=CoinResponse)
async def create_coin(
    name: str = Form(...),
    symbol: str = Form(...),
    file: UploadFile = File(None),
    current_user=Depends(get_current_user)
):
    try:
        existing = supabase.table("coins").select("*").eq("symbol", symbol.upper()).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Coin with this symbol already exists")

        img_url = None
        if file:
            file_bytes = await file.read()
            if len(file_bytes) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image file too large (max 5MB)")

            ext = file.filename.split(".")[-1].lower()
            if ext not in ["png", "jpg", "jpeg"]:
                raise HTTPException(status_code=400, detail="Invalid image format. Only PNG and JPG are allowed.")

            processed_bytes = process_image(file_bytes)
            filename = generate_filename(symbol, ext)
            storage_res = supabase.storage.from_("coin-images").upload(filename, processed_bytes)

            if "error" in storage_res and storage_res["error"]:
                raise HTTPException(status_code=500, detail=f"Error uploading image: {storage_res['error']['message']}")

            img_url = supabase.storage.from_("coin-images").get_public_url(filename)

        data = {
            "name": name,
            "symbol": symbol.upper(),
            "img_url": img_url,
            "creator_id": current_user.id,
            "total_supply": float(1000000),
            "circulating_supply": float(1000000),
            "current_price": float(0.001),
            "initial_market_cap": float(1000.00)
        }

        res = supabase.table("coins").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Error creating coin")

        return res.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exception creating coin: {str(e)}")
