import hmac
import hashlib
import time
from urllib.parse import parse_qsl
from fastapi import HTTPException, status
from jose import jwt
from app.config import get_settings

settings = get_settings()

def validate_init_data(init_data: str) -> dict:
    """Strict Telegram WebApp initData validation"""
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid initData format")

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    # Remove signature if present (Bot API 8+)
    parsed.pop("signature", None)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid hash")

    # Prevent replay attacks
    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 600:  # 10 minutes max
        raise HTTPException(status_code=401, detail="initData expired")

    return parsed

def create_access_token(telegram_id: int) -> str:
    expire = time.time() + (settings.JWT_EXPIRE_MINUTES * 60)
    payload = {"sub": str(telegram_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)