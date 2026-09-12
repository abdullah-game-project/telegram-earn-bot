from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import TransactionType, WithdrawalRequest, WithdrawalStatus
from app.services.balance import adjust_balance

settings = get_settings()


async def create_withdrawal(
    session: AsyncSession,
    telegram_id: int,
    amount: Decimal,
    payout_method: str,
    payout_address: str,
    idempotency_key: str,
) -> WithdrawalRequest:
    if amount < settings.MIN_WITHDRAWAL_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum withdrawal is {settings.MIN_WITHDRAWAL_AMOUNT}",
        )
    if amount > settings.MAX_WITHDRAWAL_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum withdrawal is {settings.MAX_WITHDRAWAL_AMOUNT}",
        )

    existing = await session.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.idempotency_key == idempotency_key)
    )
    if existing_request := existing.scalar_one_or_none():
        # Client retried the same request (e.g. after a network timeout) — return
        # the original instead of creating a duplicate hold.
        return existing_request

    # Debit the balance immediately as a "hold" so the funds can't be spent twice
    # while the withdrawal is pending manual/automated review.
    hold_tx = await adjust_balance(
        session,
        telegram_id,
        -amount,
        TransactionType.WITHDRAW,
        description="Withdrawal requested (held pending review)",
    )

    request = WithdrawalRequest(
        user_id=telegram_id,
        amount=amount,
        status=WithdrawalStatus.PENDING.value,
        payout_method=payout_method,
        payout_address=payout_address,
        idempotency_key=idempotency_key,
        hold_transaction_id=hold_tx.id,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def review_withdrawal(
    session: AsyncSession,
    withdrawal_id: int,
    admin_telegram_id: int,
    approve: bool,
    note: str | None = None,
) -> WithdrawalRequest:
    result = await session.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != WithdrawalStatus.PENDING.value:
        raise HTTPException(status_code=409, detail=f"Request already {request.status}")

    if approve:
        request.status = WithdrawalStatus.APPROVED.value
    else:
        # Reverse the hold so the user gets their balance back.
        await adjust_balance(
            session,
            request.user_id,
            request.amount,
            TransactionType.WITHDRAW_REVERSAL,
            description=f"Withdrawal #{request.id} rejected: {note or 'no reason given'}",
        )
        request.status = WithdrawalStatus.REJECTED.value

    request.reviewed_by_admin_id = admin_telegram_id
    request.admin_note = note
    request.processed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(request)
    return request


async def mark_paid(session: AsyncSession, withdrawal_id: int, admin_telegram_id: int) -> WithdrawalRequest:
    result = await session.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != WithdrawalStatus.APPROVED.value:
        raise HTTPException(status_code=409, detail="Only approved requests can be marked paid")

    request.status = WithdrawalStatus.PAID.value
    request.reviewed_by_admin_id = admin_telegram_id
    request.processed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(request)
    return request
