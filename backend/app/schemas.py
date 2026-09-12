from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    balance: Decimal
    is_banned: bool
    referral_code: str

    class Config:
        from_attributes = True


class AuthRequest(BaseModel):
    init_data: str
    referral_code: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class BalanceResponse(BaseModel):
    balance: Decimal
    telegram_id: int


class TransactionResponse(BaseModel):
    id: int
    amount: str
    type: str
    balance_after: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int


class LeaderboardEntry(BaseModel):
    rank: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    value: str
    display_name: str


class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardEntry]


class WithdrawalCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    payout_method: str = Field(min_length=1, max_length=32)
    payout_address: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=8, max_length=64)

    @field_validator("amount")
    @classmethod
    def _round_amount(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.000001"))


class WithdrawalResponse(BaseModel):
    id: int
    amount: Decimal
    status: str
    payout_method: str
    payout_address: str
    requested_at: datetime
    processed_at: Optional[datetime] = None
    admin_note: Optional[str] = None

    class Config:
        from_attributes = True


class WithdrawalReviewRequest(BaseModel):
    approve: bool
    note: Optional[str] = None


class AdminAdjustBalanceRequest(BaseModel):
    telegram_id: int
    amount: Decimal
    reason: str = Field(min_length=1, max_length=256)


class AdminBanRequest(BaseModel):
    telegram_id: int
    banned: bool
    reason: Optional[str] = None
