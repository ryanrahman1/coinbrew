from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime

class CoinBase(BaseModel):
    name: str = Field(..., example="Bitcoin")
    symbol: str = Field(..., example="BTC")
    img_url: Optional[str] = None
    total_supply: float = Field(..., example=1000000)
    circulating_supply: float = Field(..., example=500000)

class CoinCreate(CoinBase):
    creator_id: str

class CoinResponse(CoinBase):
    id: Union[str, int]
    current_price: float
    initial_market_cap: float
    created_at: datetime
    creator_id: str

    class Config:
        orm_mode = True