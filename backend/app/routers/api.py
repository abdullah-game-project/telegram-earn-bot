from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth import validate_init_data, create_access_token
from app.schemas import AuthRequest, AuthResponse, UserResponse, BalanceResponse
from app.services.balance import get_or_create_user
from app.models import User
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