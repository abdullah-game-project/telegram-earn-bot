from pydantic import BaseModel
from decimal import Decimal

class UserBase(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    balance: Decimal
    is_banned: bool

class TransactionCreate(BaseModel):
    user_id: int
    type: str  # earn / withdraw / adjustment
    amount: Decimal
    description: str | None = None

class TransactionResponse(TransactionCreate):
    id: int

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"