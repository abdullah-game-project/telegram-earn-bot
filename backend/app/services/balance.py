from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Transaction
from fastapi import HTTPException

USER_SHARE = Decimal("0.90")
OWNER_SHARE = Decimal("0.10")

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None = None, first_name: str | None = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            balance=Decimal("0.000000")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def credit_revenue(
    session: AsyncSession,
    user_id: int,
    amount: Decimal,
    network_tx_id: str,
    description: str = "Ad/Offer revenue"
) -> dict:
    """
    Secure 90/10 credit.
    Only call this after ad network postback is verified.
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Prevent double credit
    existing = await session.execute(
        select(Transaction).where(Transaction.network_tx_id == network_tx_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Transaction already processed")

    user = await get_or_create_user(session, user_id)

    user_amount = (amount * USER_SHARE).quantize(Decimal("0.000001"))
    owner_amount = (amount * OWNER_SHARE).quantize(Decimal("0.000001"))

    # Credit user
    user.balance += user_amount

    # Record user transaction
    tx = Transaction(
        user_id=user_id,
        type="earn",
        amount=user_amount,
        network_tx_id=network_tx_id,
        description=f"{description} | User 90%"
    )
    session.add(tx)

    # You can later add owner ledger here
    await session.commit()

    return {
        "user_credited": float(user_amount),
        "owner_share": float(owner_amount),
        "new_balance": float(user.balance)
    }