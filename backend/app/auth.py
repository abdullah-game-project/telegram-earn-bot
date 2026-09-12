import time
import logging
import json
from fastapi import HTTPException
from jose import jwt
from aiogram.utils.web_app import check_webapp_signature, safe_parse_webapp_init_data
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def validate_init_data(init_data: str) -> dict:
    """Official Telegram WebApp validation using aiogram."""
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")

    if not check_webapp_signature(settings.BOT_TOKEN, init_data):
        token_tail = settings.BOT_TOKEN[-6:] if settings.BOT_TOKEN else "EMPTY"
        logger.error(f"HASH MISMATCH (aiogram) | token_tail=...{token_tail}")
        raise HTTPException(status_code=401, detail="Invalid hash")

    try:
        parsed = safe_parse_webapp_init_data(settings.BOT_TOKEN, init_data)
    except ValueError as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=401, detail="Invalid initData")

    auth_date = (
        parsed.auth_date.timestamp()
        if hasattr(parsed.auth_date, "timestamp")
        else int(parsed.auth_date)
    )
    if time.time() - auth_date > 600:
        raise HTTPException(status_code=401, detail="initData expired")

    result = {"auth_date": str(int(auth_date))}
    if parsed.user:
        result["user"] = json.dumps({
            "id": parsed.user.id,
            "first_name": parsed.user.first_name,
            "last_name": getattr(parsed.user, "last_name", None),
            "username": getattr(parsed.user, "username", None),
            "language_code": getattr(parsed.user, "language_code", None),
            "is_premium": getattr(parsed.user, "is_premium", False),
        }, ensure_ascii=False)

    return result

def create_access_token(telegram_id: int) -> str:
    expire = time.time() + (settings.JWT_EXPIRE_MINUTES * 60)
    payload = {"sub": str(telegram_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
