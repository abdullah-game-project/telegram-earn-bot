from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from app.database import get_db
from app.auth import validate_init_data, create_access_token
from app.schemas import (
    AuthRequest,
    AuthResponse,
    BalanceResponse,
    LeaderboardResponse,
    TransactionListResponse,
    UserResponse,
)
from app.services.balance import get_or_create_user
from app.models import Transaction, User
from jose import jwt, JWTError
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["api"])
settings = get_settings()

async def get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_db)
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        telegram_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user or user.is_banned:
        raise HTTPException(status_code=403, detail="User not found or banned")
    return user

@router.post("/auth", response_model=AuthResponse)
async def authenticate(data: AuthRequest, session: AsyncSession = Depends(get_db)):
    parsed = validate_init_data(data.init_data)

    user_data = {}
    if "user" in parsed:
        import json
        user_data = json.loads(parsed["user"])

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="User ID missing")

    user = await get_or_create_user(
        session,
        telegram_id=telegram_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name")
    )

    token = create_access_token(telegram_id)

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=BalanceResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return BalanceResponse(
        telegram_id=current_user.telegram_id,
        balance=current_user.balance
    )

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

    count_result = await session.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    result = await session.execute(
        query
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return TransactionListResponse(
        transactions=[
            {
                "id": transaction.id,
                "amount": str(transaction.amount),
                "type": transaction.type,
                "status": "completed",
                "description": transaction.description,
                "created_at": transaction.created_at,
            }
            for transaction in result.scalars().all()
        ],
        total=total,
    )

@router.get("/leaderboard/payouts", response_model=LeaderboardResponse)
async def get_top_payouts(
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            func.sum(Transaction.amount).label("total_payout"),
        )
        .join(
            Transaction,
            and_(
                Transaction.user_id == User.telegram_id,
                Transaction.type == "withdraw",
            ),
        )
        .where(User.is_banned.is_(False))
        .group_by(User.telegram_id, User.username, User.first_name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
    )

    leaderboard = []
    for rank, row in enumerate(result, 1):
        display_name = f"@{row.username}" if row.username else row.first_name or f"User {row.telegram_id}"
        leaderboard.append({
            "rank": rank,
            "telegram_id": row.telegram_id,
            "username": row.username,
            "first_name": row.first_name,
            "value": str(row.total_payout),
            "display_name": display_name,
        })

    return {"leaderboard": leaderboard}

@router.get("/leaderboard/referrers", response_model=LeaderboardResponse)
async def get_top_referrers(
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            func.count(Transaction.id).label("referral_count"),
        )
        .join(
            Transaction,
            and_(
                Transaction.user_id == User.telegram_id,
                Transaction.type == "referral",
            ),
        )
        .where(User.is_banned.is_(False))
        .group_by(User.telegram_id, User.username, User.first_name)
        .order_by(func.count(Transaction.id).desc())
        .limit(limit)
    )

    leaderboard = []
    for rank, row in enumerate(result, 1):
        display_name = f"@{row.username}" if row.username else row.first_name or f"User {row.telegram_id}"
        leaderboard.append({
            "rank": rank,
            "telegram_id": row.telegram_id,
            "username": row.username,
            "first_name": row.first_name,
            "value": str(row.referral_count),
            "display_name": display_name,
        })

    return {"leaderboard": leaderboard}