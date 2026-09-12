"""
Generic, provider-agnostic postback (S2S callback) endpoint for offerwall / ad
network integrations (AdGate, OfferToro, CPAlead, etc all work similarly: they
GET or POST to a URL you give them when a user completes an offer).

Every provider signs things slightly differently. This implementation expects:
  - Header `X-Signature`: hex HMAC-SHA256 of the raw request body, keyed with
    POSTBACK_SECRET.
  - JSON body: {"telegram_id": <int>, "amount": "<decimal string>", "tx_id": "<str>"}

When you pick a real provider, adjust `verify_signature` in
app/services/postback.py to match their scheme (some sign a query string, some
use a static "secure token" query param instead of HMAC) and adjust the field
names below to whatever their callback sends.
"""

import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.limiter import limiter
from app.database import get_db
from app.services.postback import handle_postback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/postback", tags=["postback"])
settings = get_settings()


@router.post("/{provider}")
@limiter.limit(settings.RATE_LIMIT_POSTBACK)
async def receive_postback(
    provider: str,
    request: Request,
    x_signature: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    result = await handle_postback(
        session,
        provider=provider,
        raw_body=raw_body,
        signature=x_signature,
        source_ip=request.client.host if request.client else None,
        telegram_id=payload.get("telegram_id"),
        amount_str=payload.get("amount"),
        tx_id=payload.get("tx_id"),
    )
    return {"status": "ok", **{k: str(v) for k, v in result.items()}}
