from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import TransactionType, WithdrawalStatus
from app.services.balance import adjust_balance, get_or_create_user
from app.services.withdrawal import create_withdrawal, review_withdrawal

pytestmark = pytest.mark.asyncio


async def _funded_user(session, telegram_id: int, amount: str) -> None:
    await get_or_create_user(session, telegram_id=telegram_id)
    await adjust_balance(session, telegram_id, Decimal(amount), TransactionType.EARN, "seed")


async def test_withdrawal_holds_balance_immediately(db_session):
    await _funded_user(db_session, 10, "50")

    req = await create_withdrawal(
        db_session, telegram_id=10, amount=Decimal("20"), payout_method="usdt_trc20",
        payout_address="T123", idempotency_key="idem-1",
    )
    assert req.status == WithdrawalStatus.PENDING.value

    user = await get_or_create_user(db_session, telegram_id=10)
    assert user.balance == Decimal("30")  # 50 - 20 held immediately


async def test_withdrawal_idempotent_on_retry(db_session):
    await _funded_user(db_session, 11, "50")

    req1 = await create_withdrawal(
        db_session, telegram_id=11, amount=Decimal("10"), payout_method="usdt_trc20",
        payout_address="T1", idempotency_key="same-key",
    )
    req2 = await create_withdrawal(
        db_session, telegram_id=11, amount=Decimal("10"), payout_method="usdt_trc20",
        payout_address="T1", idempotency_key="same-key",
    )
    assert req1.id == req2.id

    user = await get_or_create_user(db_session, telegram_id=11)
    assert user.balance == Decimal("40")  # only debited once


async def test_cannot_withdraw_more_than_balance(db_session):
    await _funded_user(db_session, 12, "5")
    with pytest.raises(HTTPException) as exc:
        await create_withdrawal(
            db_session, telegram_id=12, amount=Decimal("100"), payout_method="usdt_trc20",
            payout_address="T1", idempotency_key="idem-x",
        )
    assert exc.value.status_code == 400


async def test_rejected_withdrawal_refunds_balance(db_session):
    await _funded_user(db_session, 13, "50")
    req = await create_withdrawal(
        db_session, telegram_id=13, amount=Decimal("20"), payout_method="usdt_trc20",
        payout_address="T1", idempotency_key="idem-y",
    )
    user = await get_or_create_user(db_session, telegram_id=13)
    assert user.balance == Decimal("30")

    await review_withdrawal(db_session, req.id, admin_telegram_id=999, approve=False, note="fraud check failed")

    user = await get_or_create_user(db_session, telegram_id=13)
    assert user.balance == Decimal("50")  # fully refunded


async def test_approved_withdrawal_does_not_refund(db_session):
    await _funded_user(db_session, 14, "50")
    req = await create_withdrawal(
        db_session, telegram_id=14, amount=Decimal("20"), payout_method="usdt_trc20",
        payout_address="T1", idempotency_key="idem-z",
    )
    await review_withdrawal(db_session, req.id, admin_telegram_id=999, approve=True)

    user = await get_or_create_user(db_session, telegram_id=14)
    assert user.balance == Decimal("30")  # stays held/spent, not refunded
