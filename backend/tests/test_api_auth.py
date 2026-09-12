import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest

from app.config import get_settings

pytestmark = pytest.mark.asyncio

settings = get_settings()


def _build_init_data(user: dict, bot_token: str) -> str:
    """Build a validly-signed Telegram WebApp initData string for tests,
    mirroring Telegram's documented signing scheme."""
    import json

    data = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "AAtest",
    }
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


async def test_auth_rejects_missing_init_data(client):
    resp = await client.post("/api/auth", json={"init_data": ""})
    assert resp.status_code == 401


async def test_auth_rejects_tampered_init_data(client):
    resp = await client.post("/api/auth", json={"init_data": "user=%7B%7D&auth_date=123&hash=deadbeef"})
    assert resp.status_code == 401


async def test_full_auth_and_me_flow(client):
    init_data = _build_init_data({"id": 555, "first_name": "Ada", "username": "ada"}, settings.BOT_TOKEN)

    auth_resp = await client.post("/api/auth", json={"init_data": init_data})
    assert auth_resp.status_code == 200
    body = auth_resp.json()
    assert body["user"]["telegram_id"] == 555
    assert body["access_token"]

    me_resp = await client.get("/api/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["balance"] == "0.000000" or float(me_resp.json()["balance"]) == 0


async def test_me_requires_auth(client):
    resp = await client.get("/api/me")
    assert resp.status_code in (401, 422)


async def test_non_admin_cannot_reach_admin_routes(client):
    init_data = _build_init_data({"id": 556, "first_name": "Bob"}, settings.BOT_TOKEN)
    auth_resp = await client.post("/api/auth", json={"init_data": init_data})
    token = auth_resp.json()["access_token"]

    resp = await client.get("/admin/withdrawals/pending", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
