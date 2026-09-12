import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Transaction, TransactionType, User

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            # Lost a race with a concurrent request creating the same user.
            await session.rollback()
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one()
        else:
            await session.refresh(user)
    elif username is not None or first_name is not None:
        # Keep denormalized profile fields fresh without clobbering with None.
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        await session.commit()
        await session.refresh(user)

    return user


async def _lock_user(session: AsyncSession, telegram_id: int) -> User:
    """Row-lock the user for the duration of the current transaction so concurrent
    balance mutations for the same user serialize instead of racing."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def adjust_balance(
    session: AsyncSession,
    telegram_id: int,
    amount: Decimal,
    tx_type: TransactionType,
    description: str = "",
    network_tx_id: str | None = None,
    allow_negative: bool = False,
) -> Transaction:
    """
    Atomically apply a signed `amount` to a user's balance and append a ledger row.

    - `amount` must be non-zero. Positive credits, negative debits.
    - If `network_tx_id` is provided it must be globally unique; a duplicate is
      treated as an already-processed event (idempotent) and raises 409 rather
      than silently no-op'ing, so callers can distinguish "already applied" from
      a fresh success.
    - Debits that would take the balance below zero are rejected unless
      `allow_negative` is explicitly set (used only by admin adjustments).
    """
    if amount == 0:
        raise HTTPException(status_code=400, detail="Amount must be non-zero")

    if network_tx_id:
        existing = await session.execute(
            select(Transaction).where(Transaction.network_tx_id == network_tx_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Transaction already processed")

    user = await _lock_user(session, telegram_id)

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    new_balance = user.balance + amount
    if new_balance < 0 and not allow_negative:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance = new_balance

    tx = Transaction(
        user_id=telegram_id,
        type=tx_type.value,
        amount=amount,
        balance_after=new_balance,
        network_tx_id=network_tx_id,
        description=description,
    )
    session.add(tx)

    try:
        await session.commit()
    except IntegrityError:
        # Guards the (rare) race where two requests with the same network_tx_id
        # both passed the pre-check and both reached the DB at once.
        await session.rollback()
        raise HTTPException(status_code=409, detail="Transaction already processed")

    await session.refresh(tx)
    return tx


async def credit_ad_revenue(
    session: AsyncSession,
    telegram_id: int,
    gross_amount: Decimal,
    network_tx_id: str,
    description: str = "Ad/offer revenue",
) -> dict:
    """Apply the configured user/owner revenue split and credit the user's share.
    Must only be called after the postback signature has been verified."""
    if gross_amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    user_share = settings.USER_REVENUE_SHARE
    user_amount = (gross_amount * user_share).quantize(Decimal("0.000001"))
    owner_amount = (gross_amount - user_amount).quantize(Decimal("0.000001"))

    tx = await adjust_balance(
        session,
        telegram_id,
        user_amount,
        TransactionType.EARN,
        description=f"{description} (user share {user_share:.0%})",
        network_tx_id=network_tx_id,
    )

    # Referral commission: a small extra credit to whoever referred this user,
    # funded out of the owner's share so the user's payout is unaffected.
    referral_amount = Decimal("0")
    result = await session.execute(select(User.referred_by).where(User.telegram_id == telegram_id))
    referrer_id = result.scalar_one_or_none()
    if referrer_id:
        referral_amount = (owner_amount * Decimal("0.20")).quantize(Decimal("0.000001"))
        if referral_amount > 0:
            try:
                await adjust_balance(
                    session,
                    referrer_id,
                    referral_amount,
                    TransactionType.REFERRAL_BONUS,
                    description=f"Referral bonus from user {telegram_id}",
                    network_tx_id=f"{network_tx_id}:referral",
                )
            except HTTPException as exc:
                # Don't fail the primary credit if the referrer is banned/missing.
                logger.warning("Referral bonus skipped for %s: %s", referrer_id, exc.detail)
                referral_amount = Decimal("0")

    return {
        "transaction_id": tx.id,
        "user_credited": user_amount,
        "owner_share": owner_amount,
        "referral_paid": referral_amount,
        "new_balance": tx.balance_after,
    }
