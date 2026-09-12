import time
import logging
import json
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.web_app import check_webapp_signature, safe_parse_webapp_init_data

from app.config import get_settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_INIT_DATA_AGE_SECONDS = 600


def validate_init_data(init_data: str) -> dict:
    """Official Telegram WebApp validation using aiogram."""
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")

    if not check_webapp_signature(settings.BOT_TOKEN, init_data):
        logger.warning("initData signature mismatch")
        raise HTTPException(status_code=401, detail="Invalid hash")

    try:
        parsed = safe_parse_webapp_init_data(settings.BOT_TOKEN, init_data)
    except ValueError as e:
        logger.warning("initData parse error: %s", e)
        raise HTTPException(status_code=401, detail="Invalid initData")

    auth_date = (
        parsed.auth_date.timestamp() if hasattr(parsed.auth_date, "timestamp") else int(parsed.auth_date)
    )
    if time.time() - auth_date > MAX_INIT_DATA_AGE_SECONDS:
        raise HTTPException(status_code=401, detail="initData expired")

    result = {"auth_date": str(int(auth_date))}
    if parsed.user:
        result["user"] = json.dumps(
            {
                "id": parsed.user.id,
                "first_name": parsed.user.first_name,
                "last_name": getattr(parsed.user, "last_name", None),
                "username": getattr(parsed.user, "username", None),
                "language_code": getattr(parsed.user, "language_code", None),
                "is_premium": getattr(parsed.user, "is_premium", False),
            },
            ensure_ascii=False,
        )

    return result


def create_access_token(telegram_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(telegram_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(telegram_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    payload = {"sub": str(telegram_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1]
    telegram_id = decode_token(token, expected_type="access")

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user or user.is_banned:
        raise HTTPException(status_code=403, detail="User not found or banned")
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.telegram_id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
