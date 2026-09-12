import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_admin
from app.database import get_db
from app.models import AdminAuditLog, TransactionType, User, WithdrawalRequest
from app.schemas import (
    AdminAdjustBalanceRequest,
    AdminBanRequest,
    WithdrawalResponse,
    WithdrawalReviewRequest,
)
from app.services.balance import adjust_balance
from app.services.withdrawal import mark_paid, review_withdrawal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


async def _audit(session: AsyncSession, admin: User, action: str, target_user_id: int | None, detail: str):
    session.add(
        AdminAuditLog(
            admin_telegram_id=admin.telegram_id,
            action=action,
            target_user_id=target_user_id,
            detail=detail,
        )
    )
    await session.commit()


@router.get("/withdrawals/pending", response_model=list[WithdrawalResponse])
async def list_pending_withdrawals(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.status == "pending")
        .order_by(WithdrawalRequest.requested_at.asc())
    )
    return [WithdrawalResponse.model_validate(w) for w in result.scalars().all()]


@router.post("/withdrawals/{withdrawal_id}/review", response_model=WithdrawalResponse)
async def review_withdrawal_route(
    withdrawal_id: int,
    data: WithdrawalReviewRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await review_withdrawal(
        session, withdrawal_id, admin.telegram_id, approve=data.approve, note=data.note
    )
    await _audit(
        session,
        admin,
        action="withdrawal_approved" if data.approve else "withdrawal_rejected",
        target_user_id=result.user_id,
        detail=f"withdrawal #{withdrawal_id}: {data.note or ''}",
    )
    return WithdrawalResponse.model_validate(result)


@router.post("/withdrawals/{withdrawal_id}/mark-paid", response_model=WithdrawalResponse)
async def mark_withdrawal_paid(
    withdrawal_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await mark_paid(session, withdrawal_id, admin.telegram_id)
    await _audit(session, admin, action="withdrawal_paid", target_user_id=result.user_id, detail=f"#{withdrawal_id}")
    return WithdrawalResponse.model_validate(result)


@router.post("/users/adjust-balance")
async def adjust_user_balance(
    data: AdminAdjustBalanceRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    tx = await adjust_balance(
        session,
        data.telegram_id,
        data.amount,
        TransactionType.ADJUSTMENT,
        description=f"Admin adjustment by {admin.telegram_id}: {data.reason}",
        allow_negative=True,
    )
    await _audit(
        session,
        admin,
        action="balance_adjustment",
        target_user_id=data.telegram_id,
        detail=f"{data.amount} — {data.reason}",
    )
    return {"transaction_id": tx.id, "new_balance": str(tx.balance_after)}


@router.post("/users/ban")
async def ban_user(
    data: AdminBanRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        return {"error": "user not found"}

    user.is_banned = data.banned
    user.ban_reason = data.reason if data.banned else None
    await session.commit()

    await _audit(
        session,
        admin,
        action="user_banned" if data.banned else "user_unbanned",
        target_user_id=data.telegram_id,
        detail=data.reason or "",
    )
    return {"telegram_id": data.telegram_id, "is_banned": user.is_banned}
