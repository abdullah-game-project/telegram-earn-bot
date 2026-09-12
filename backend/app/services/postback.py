import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PostbackLog
from app.services.balance import credit_ad_revenue

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    """Generic HMAC-SHA256 verification: signature = HMAC(POSTBACK_SECRET, raw_body).
    Swap this for your provider's specific scheme once one is chosen (many providers
    sign a canonical query string rather than the raw body)."""
    if not settings.POSTBACK_SECRET:
        logger.error("POSTBACK_SECRET is not configured; rejecting all postbacks")
        return False
    if not signature:
        return False
    expected = hmac.new(settings.POSTBACK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_postback(
    session: AsyncSession,
    *,
    provider: str,
    raw_body: bytes,
    signature: str | None,
    source_ip: str | None,
    telegram_id: int | None,
    amount_str: str | None,
    tx_id: str | None,
) -> dict:
    signature_valid = verify_signature(raw_body, signature)

    log = PostbackLog(
        provider=provider,
        source_ip=source_ip,
        raw_payload=raw_body.decode(errors="replace")[:4000],
        signature_valid=signature_valid,
        processed=False,
    )
    session.add(log)
    await session.commit()

    if not signature_valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    if settings.postback_ip_allowlist and source_ip not in settings.postback_ip_allowlist:
        log.error = "source IP not in allowlist"
        await session.commit()
        raise HTTPException(status_code=403, detail="Source IP not allowed")

    if not telegram_id or not amount_str or not tx_id:
        log.error = "missing telegram_id/amount/tx_id"
        await session.commit()
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        log.error = "invalid amount"
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        result = await credit_ad_revenue(
            session,
            telegram_id=telegram_id,
            gross_amount=amount,
            network_tx_id=f"{provider}:{tx_id}",
            description=f"{provider} offer completion",
        )
    except HTTPException as exc:
        log.error = exc.detail
        await session.commit()
        raise

    log.processed = True
    await session.commit()
    return result
