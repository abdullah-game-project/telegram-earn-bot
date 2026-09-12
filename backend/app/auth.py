import hmac
import hashlib
import time
import logging
from urllib.parse import parse_qsl
from fastapi import HTTPException
from jose import jwt
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def validate_init_data(init_data: str) -> dict:
    """Strict Telegram WebApp initData validation"""
    if not init_data or not isinstance(init_data, str):
        raise HTTPException(status_code=401, detail="Missing initData")

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid initData format")

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    # Remove signature (Bot API 7+/8+)
    parsed.pop("signature", None)

    # Official data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        # Safe debug – add a non-reversible fingerprint of the bot token
        if settings.BOT_TOKEN:
            token_fingerprint = hashlib.sha256(settings.BOT_TOKEN.encode()).hexdigest()[:8]
            token_tail = settings.BOT_TOKEN[-6:]
        else:
            token_fingerprint = "EMPTY"
            token_tail = "EMPTY"

        logger.error(
            f"HASH MISMATCH | "
            f"token_fingerprint={token_fingerprint} | "
            f"token_tail=...{token_tail} | "
            f"received={received_hash[:12]}... | "
            f"calculated={calculated_hash[:12]}... | "
            f"auth_date={parsed.get('auth_date')} | "
            f"keys={list(parsed.keys())}"
        )
        raise HTTPException(status_code=401, detail="Invalid hash")

    # Check expiration (10 minutes)
    try:
        auth_date = int(parsed.get("auth_date", 0))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid auth_date")

    if time.time() - auth_date > 600:
        raise HTTPException(status_code=401, detail="initData expired")

    return parsed


def create_access_token(telegram_id: int) -> str:
    expire = time.time() + (settings.JWT_EXPIRE_MINUTES * 60)
    payload = {"sub": str(telegram_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
