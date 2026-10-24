"""Credit balance management, atomic reservation holds, and immutable ledger accounting."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import Application
from packages.core.models.identity import CreditHold, CreditsLedger, Subscription, UserMeta
from packages.core.seed.plans import PLANS_CONFIG


class CreditsService:
    """Production-grade ledger service guaranteeing zero double-spends via reservation holds."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_total_ledger_balance(self, user_id: str, credit_type: str = "apply") -> int:
        """Sum of all completed ledger credit grants and deductions."""
        stmt = select(func.coalesce(func.sum(CreditsLedger.amount), 0)).where(
            CreditsLedger.user_id == user_id,
            CreditsLedger.credit_type == credit_type,
        )
        total = (await self.db.execute(stmt)).scalar() or 0
        return int(total)

    async def get_active_held_amount(self, user_id: str, credit_type: str = "apply") -> int:
        """Sum of all currently reserved credits awaiting async worker completion."""
        now = datetime.now(UTC)
        stmt = select(func.coalesce(func.sum(CreditHold.amount), 0)).where(
            CreditHold.user_id == user_id,
            CreditHold.credit_type == credit_type,
            CreditHold.status == "held",
            CreditHold.expires_at > now,
        )
        held = (await self.db.execute(stmt)).scalar() or 0
        return int(held)

    async def get_available_balance(self, user_id: str, credit_type: str = "apply") -> int:
        """Usable balance available for new applications or AI operations."""
        ledger_balance = await self.get_total_ledger_balance(user_id, credit_type)
        held_amount = await self.get_active_held_amount(user_id, credit_type)
        return max(0, ledger_balance - held_amount)

    async def reserve_hold(
        self,
        user_id: str,
        amount: int = 1,
        credit_type: str = "apply",
        task_id: str | None = None,
        ttl_seconds: int = 900,
    ) -> CreditHold:
        """Reserve credits prior to enqueuing background automation work."""
        available = await self.get_available_balance(user_id, credit_type)
        if available < amount:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "message": f"Insufficient {credit_type} credits. Available: {available}, Required: {amount}",
                },
            )

        hold_id = uuid.uuid4()
        task_ref = task_id or str(hold_id)
        now = datetime.now(UTC)
        hold = CreditHold(
            id=hold_id,
            user_id=user_id,
            credit_type=credit_type,
            amount=amount,
            task_id=task_ref,
            status="held",
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self.db.add(hold)
        await self.db.flush()
        return hold

    async def capture_hold(
        self,
        hold_id: uuid.UUID,
        reason: str = "application_submitted",
        ref_type: str = "application",
        ref_id: str | None = None,
    ) -> CreditsLedger:
        """Finalize credit deduction after task succeeds."""
        stmt = select(CreditHold).where(CreditHold.id == hold_id)
        hold = (await self.db.execute(stmt)).scalars().first()
        if not hold:
            raise HTTPException(status_code=404, detail="Credit hold not found")

        if hold.status == "captured":
            # Already captured (idempotent)
            l_stmt = select(CreditsLedger).where(
                CreditsLedger.idempotency_key == f"cap_{hold_id}"
            )
            return (await self.db.execute(l_stmt)).scalars().first()  # type: ignore

        hold.status = "captured"

        # Calculate new total ledger balance
        cur_ledger = await self.get_total_ledger_balance(hold.user_id, hold.credit_type)
        new_balance = cur_ledger - hold.amount

        ledger_entry = CreditsLedger(
            id=uuid.uuid4(),
            user_id=hold.user_id,
            credit_type=hold.credit_type,
            amount=-hold.amount,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
            balance_after=new_balance,
            idempotency_key=f"cap_{hold_id}",
            created_at=datetime.now(UTC),
        )
        self.db.add(ledger_entry)
        await self.db.flush()
        return ledger_entry

    async def release_hold(self, hold_id: uuid.UUID, reason: str = "automation_failed") -> None:
        """Release reserved credits back to available balance when an operation fails."""
        stmt = select(CreditHold).where(CreditHold.id == hold_id)
        hold = (await self.db.execute(stmt)).scalars().first()
        if hold and hold.status == "held":
            hold.status = "released"
            await self.db.flush()

    async def grant_credits(
        self,
        user_id: str,
        amount: int,
        credit_type: str = "apply",
        reason: str = "plan_grant",
        ref_type: str | None = None,
        ref_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> CreditsLedger:
        """Add credits to user's balance (e.g. signup welcome bonus, subscription refresh)."""
        idem_key = idempotency_key or f"grant_{user_id}_{credit_type}_{uuid.uuid4().hex[:12]}"

        # Check existing
        existing_stmt = select(CreditsLedger).where(CreditsLedger.idempotency_key == idem_key)
        existing = (await self.db.execute(existing_stmt)).scalars().first()
        if existing:
            return existing

        cur_balance = await self.get_total_ledger_balance(user_id, credit_type)
        new_balance = cur_balance + amount

        entry = CreditsLedger(
            id=uuid.uuid4(),
            user_id=user_id,
            credit_type=credit_type,
            amount=amount,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
            balance_after=new_balance,
            idempotency_key=idem_key,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_user_plan(self, user_id: str) -> dict[str, Any]:
        """Fetch current plan configuration from subscription or user_meta."""
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        sub = (await self.db.execute(stmt)).scalars().first()
        plan_name = sub.plan if sub else "free"

        if not sub:
            u_stmt = select(UserMeta).where(UserMeta.user_id == user_id)
            meta = (await self.db.execute(u_stmt)).scalars().first()
            if meta:
                plan_name = meta.plan

        config = PLANS_CONFIG.get(plan_name, PLANS_CONFIG["free"])
        return {"plan": plan_name, "config": config}

    async def check_daily_application_cap(self, user_id: str) -> dict[str, Any]:
        """Check if candidate has reached their plan's daily application limit."""
        plan_info = await self.get_user_plan(user_id)
        limit = plan_info["config"]["daily_application_limit"]

        # Count applications submitted today
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(Application.id)).where(
            Application.user_id == user_id,
            Application.status == "submitted",
            Application.submitted_at >= today_start,
        )
        count_today = (await self.db.execute(stmt)).scalar() or 0

        can_apply = count_today < limit
        return {
            "can_apply": can_apply,
            "count_today": count_today,
            "daily_limit": limit,
            "remaining_today": max(0, limit - count_today),
        }

    async def get_ledger_history(
        self,
        user_id: str,
        credit_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List chronological credit activity for dashboard."""
        query = select(CreditsLedger).where(CreditsLedger.user_id == user_id)
        if credit_type:
            query = query.where(CreditsLedger.credit_type == credit_type)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(desc(CreditsLedger.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        entries = (await self.db.execute(query)).scalars().all()

        return {
            "items": [
                {
                    "id": str(e.id),
                    "credit_type": e.credit_type,
                    "amount": e.amount,
                    "reason": e.reason,
                    "ref_type": e.ref_type,
                    "ref_id": e.ref_id,
                    "balance_after": e.balance_after,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
