from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime

class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    balance: Decimal
    is_banned: bool

    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    init_data: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class BalanceResponse(BaseModel):
    balance: Decimal
    telegram_id: int

class TransactionResponse(BaseModel):
    id: int
    type: str  # "earn", "withdraw", "adjustment"
    amount: Decimal
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TopPayoutResponse(BaseModel):
    rank: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    amount: Decimal

class TopReferrerResponse(BaseModel):
    rank: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    referrals: int
    earnings: Decimal
