from pydantic import BaseModel, EmailStr
from typing import List, Optional


class Holding(BaseModel):
    coin_name: str
    symbol: str
    amount: float
    current_price: float
    value: float
    img_url: Optional[str]


class Trade(BaseModel):
    coin_symbol: str
    amount: float
    price_per_coin: float
    timestamp: str
    trade_type: str


class UserBase(BaseModel):
    id: str
    username: str
    balance: float
    profile_img: Optional[str]


class UserMeResponse(UserBase):
    email: Optional[EmailStr]
    created_at: Optional[str] = None


class Portfolio(BaseModel):
    wallets: List[Holding]
    total_value: float


class UserProfileResponse(BaseModel):
    user: UserMeResponse
    portfolio: Portfolio
    recent_trades: List[Trade]
