from pydantic import BaseModel, Field
from typing import Optional, List


class TradeRequest(BaseModel):
    coin_symbol: str = Field(..., example="BTC")
    amount: float = Field(..., gt=0, example=5.0)
    price_per_coin: float = Field(..., gt=0, example=0.001)


class TradeResponse(BaseModel):
    message: str
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    coin_id: int
    amount: float
    price_per_coin: float
    timestamp: str