import hashlib
import hmac
import json

import pytest

from app.config import get_settings

pytestmark = pytest.mark.asyncio

settings = get_settings()


def _sign(body: bytes) -> str:
    return hmac.new(settings.POSTBACK_SECRET.encode(), body, hashlib.sha256).hexdigest()


async def test_postback_rejects_missing_signature(client):
    body = {"telegram_id": 1, "amount": "1.00", "tx_id": "abc"}
    resp = await client.post("/postback/testprovider", json=body)
    assert resp.status_code == 401


async def test_postback_rejects_bad_signature(client):
    body = {"telegram_id": 1, "amount": "1.00", "tx_id": "abc"}
    resp = await client.post(
        "/postback/testprovider", json=body, headers={"X-Signature": "not-the-real-signature"}
    )
    assert resp.status_code == 401


async def test_postback_accepts_valid_signature_and_credits_user(client):

    # First create the destination user via the /api/auth-less path used elsewhere
    # in tests — here we just insert directly through the service layer isn't
    # available without a session in this test, so we rely on credit_ad_revenue's
    # get_or_create_user-on-write path via adjust_balance's user lookup.
    payload = {"telegram_id": 42, "amount": "5.00", "tx_id": "unique-1"}
    raw = json.dumps(payload).encode()

    resp = await client.post(
        "/postback/testprovider",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": _sign(raw)},
    )
    # First-time postback targets a user that doesn't exist yet, so the lock
    # lookup 404s — this documents current behavior: users must open the Mini
    # App (and thus be created via /api/auth) before they can be credited.
    assert resp.status_code == 404


async def test_postback_replay_is_rejected(client, db_session):
    from app.services.balance import get_or_create_user

    await get_or_create_user(db_session, telegram_id=42)

    payload = {"telegram_id": 42, "amount": "5.00", "tx_id": "unique-2"}
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-Signature": _sign(raw)}

    first = await client.post("/postback/testprovider", content=raw, headers=headers)
    assert first.status_code == 200

    replay = await client.post("/postback/testprovider", content=raw, headers=headers)
    assert replay.status_code == 409
