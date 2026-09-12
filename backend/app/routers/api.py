import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.auth import create_access_token, create_refresh_token, decode_token, get_current_user, validate_init_data
from app.config import get_settings
from app.core.limiter import limiter
from app.database import get_db
from app.models import Transaction, TransactionType, User, WithdrawalRequest
from app.schemas import (
    AuthRequest,
    AuthResponse,
    BalanceResponse,
    LeaderboardResponse,
    RefreshRequest,
    TransactionListResponse,
    UserResponse,
    WithdrawalCreateRequest,
    WithdrawalResponse,
)
from app.services.balance import get_or_create_user
from app.services.withdrawal import create_withdrawal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])
settings = get_settings()


@router.post("/auth", response_model=AuthResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def authenticate(request: Request, data: AuthRequest, session: AsyncSession = Depends(get_db)):
    parsed = validate_init_data(data.init_data)

    user_data = {}
    if "user" in parsed:
        user_data = json.loads(parsed["user"])

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="User ID missing")

    user = await get_or_create_user(
        session,
        telegram_id=telegram_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name"),
    )

    # Attach referrer on first sign-in only; never overwrite an existing one.
    if data.referral_code and user.referred_by is None:
        result = await session.execute(select(User).where(User.referral_code == data.referral_code))
        referrer = result.scalar_one_or_none()
        if referrer and referrer.telegram_id != user.telegram_id:
            user.referred_by = referrer.telegram_id
            await session.commit()
            await session.refresh(user)

    access_token = create_access_token(telegram_id)
    refresh_token = create_refresh_token(telegram_id)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/auth/refresh", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def refresh_token(request: Request, data: RefreshRequest):
    telegram_id = decode_token(data.refresh_token, expected_type="refresh")
    return {
        "access_token": create_access_token(telegram_id),
        "refresh_token": create_refresh_token(telegram_id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=BalanceResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return BalanceResponse(telegram_id=current_user.telegram_id, balance=current_user.balance)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: str | None = Query(None, description="Filter by transaction type"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = select(Transaction).where(Transaction.user_id == current_user.telegram_id)
    if type:
        query = query.where(Transaction.type == type)

    count_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit))

    return TransactionListResponse(
        transactions=[
            {
                "id": t.id,
                "amount": str(t.amount),
                "type": t.type,
                "balance_after": str(t.balance_after),
                "description": t.description,
                "created_at": t.created_at,
            }
            for t in result.scalars().all()
        ],
        total=total,
    )


@router.post("/withdrawals", response_model=WithdrawalResponse)
@limiter.limit(settings.RATE_LIMIT_WITHDRAW)
async def request_withdrawal(
    request: Request,
    data: WithdrawalCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await create_withdrawal(
        session,
        telegram_id=current_user.telegram_id,
        amount=data.amount,
        payout_method=data.payout_method,
        payout_address=data.payout_address,
        idempotency_key=data.idempotency_key,
    )
    return WithdrawalResponse.model_validate(result)


@router.get("/withdrawals", response_model=list[WithdrawalResponse])
async def list_my_withdrawals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == current_user.telegram_id)
        .order_by(WithdrawalRequest.requested_at.desc())
    )
    return [WithdrawalResponse.model_validate(w) for w in result.scalars().all()]


@router.get("/referrals/me")
async def my_referral_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(func.count()).select_from(User).where(User.referred_by == current_user.telegram_id)
    )
    referral_count = result.scalar_one()

    earned_result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.user_id == current_user.telegram_id,
                Transaction.type == TransactionType.REFERRAL_BONUS.value,
            )
        )
    )
    total_earned = earned_result.scalar_one()

    return {
        "referral_code": current_user.referral_code,
        "referral_count": referral_count,
        "total_referral_earnings": str(total_earned),
    }


def _build_leaderboard(rows) -> list[dict]:
    leaderboard = []
    for rank, row in enumerate(rows, 1):
        display_name = f"@{row.username}" if row.username else row.first_name or f"User {row.telegram_id}"
        leaderboard.append(
            {
                "rank": rank,
                "telegram_id": row.telegram_id,
                "username": row.username,
                "first_name": row.first_name,
                "value": str(row.value),
                "display_name": display_name,
            }
        )
    return leaderboard


@router.get("/leaderboard/payouts", response_model=LeaderboardResponse)
async def get_top_payouts(limit: int = Query(20, ge=1, le=50), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            func.sum(-Transaction.amount).label("value"),
        )
        .join(
            Transaction,
            and_(Transaction.user_id == User.telegram_id, Transaction.type == TransactionType.WITHDRAW.value),
        )
        .where(User.is_banned.is_(False))
        .group_by(User.telegram_id, User.username, User.first_name)
        .order_by(func.sum(-Transaction.amount).desc())
        .limit(limit)
    )
    return {"leaderboard": _build_leaderboard(result)}


@router.get("/leaderboard/referrers", response_model=LeaderboardResponse)
async def get_top_referrers(limit: int = Query(20, ge=1, le=50), session: AsyncSession = Depends(get_db)):
    referred = aliased(User)
    result = await session.execute(
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            func.count(referred.telegram_id).label("value"),
        )
        .join(referred, referred.referred_by == User.telegram_id)
        .where(User.is_banned.is_(False))
        .group_by(User.telegram_id, User.username, User.first_name)
        .order_by(func.count(referred.telegram_id).desc())
        .limit(limit)
    )
    return {"leaderboard": _build_leaderboard(result)}
