from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import TransactionType
from app.services.balance import adjust_balance, credit_ad_revenue, get_or_create_user

pytestmark = pytest.mark.asyncio


async def test_credit_increases_balance(db_session):
    user = await get_or_create_user(db_session, telegram_id=1, username="alice")
    assert user.balance == Decimal("0")

    tx = await adjust_balance(db_session, 1, Decimal("5.5"), TransactionType.EARN, "test credit")
    assert tx.balance_after == Decimal("5.5")


async def test_debit_rejected_when_insufficient(db_session):
    await get_or_create_user(db_session, telegram_id=2)
    with pytest.raises(HTTPException) as exc:
        await adjust_balance(db_session, 2, Decimal("-10"), TransactionType.WITHDRAW, "over-withdraw")
    assert exc.value.status_code == 400


async def test_duplicate_network_tx_id_is_rejected(db_session):
    await get_or_create_user(db_session, telegram_id=3)
    await adjust_balance(
        db_session, 3, Decimal("2"), TransactionType.EARN, "first", network_tx_id="provider:abc123"
    )
    with pytest.raises(HTTPException) as exc:
        await adjust_balance(
            db_session, 3, Decimal("2"), TransactionType.EARN, "replay", network_tx_id="provider:abc123"
        )
    assert exc.value.status_code == 409

    # Balance must reflect exactly one credit, not two.
    user = await get_or_create_user(db_session, telegram_id=3)
    assert user.balance == Decimal("2")


async def test_banned_user_cannot_be_credited(db_session):
    user = await get_or_create_user(db_session, telegram_id=4)
    user.is_banned = True
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await adjust_balance(db_session, 4, Decimal("1"), TransactionType.EARN, "should fail")
    assert exc.value.status_code == 403


async def test_repeated_credits_sum_exactly(db_session):
    """Regression test for the ledger arithmetic: N sequential credits must sum
    to exactly N * amount, with no drift from Decimal rounding.

    Note: this does NOT exercise the SELECT ... FOR UPDATE row lock under real
    concurrency — SQLite's single shared test connection can't reproduce
    Postgres's per-row locking (there's no concept of two truly concurrent
    transactions on one SQLite connection), so a `gather()`-based race test
    here would just be testing SQLite's connection-sharing quirks, not the
    application's locking logic. The lock itself (`with_for_update()` in
    `_lock_user`) is standard SQLAlchemy/Postgres and should be verified with
    an integration test against real Postgres in CI before relying on it in
    production.
    """
    await get_or_create_user(db_session, telegram_id=5)

    n = 20
    amount = Decimal("1.000000")

    for i in range(n):
        await adjust_balance(
            db_session, 5, amount, TransactionType.EARN, f"credit {i}", network_tx_id=f"tx-{i}"
        )

    user = await get_or_create_user(db_session, telegram_id=5)
    assert user.balance == amount * n


async def test_credit_ad_revenue_splits_and_pays_referrer(db_session):
    referrer = await get_or_create_user(db_session, telegram_id=100, username="referrer")
    referred = await get_or_create_user(db_session, telegram_id=101, username="referred")
    referred.referred_by = referrer.telegram_id
    await db_session.commit()

    result = await credit_ad_revenue(db_session, telegram_id=101, gross_amount=Decimal("10"), network_tx_id="off-1")

    assert result["user_credited"] == Decimal("9.000000")  # 90% default share
    assert result["referral_paid"] > 0

    referrer_after = await get_or_create_user(db_session, telegram_id=100)
    assert referrer_after.balance == result["referral_paid"]
