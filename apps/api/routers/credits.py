"""API router for credit balance, ledger transaction history, plans, and billing."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.seed.plans import PLANS_CONFIG
from packages.core.services.credits import CreditsService

router = APIRouter(prefix="", tags=["Credits & Billing"])


class TopupDemoRequest(BaseModel):
    amount: int = 10
    credit_type: str = "apply"
    reason: str = "demo_topup"


class CreateOrderRequest(BaseModel):
    plan_id: str
    billing_period: str = "monthly"


@router.get("/credits/balance")
async def get_credit_balance(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve candidate's usable credit balances, active holds, and daily limits."""
    svc = CreditsService(db)
    apply_avail = await svc.get_available_balance(user.user_id, "apply")
    apply_held = await svc.get_active_held_amount(user.user_id, "apply")
    ai_avail = await svc.get_available_balance(user.user_id, "ai")
    ai_held = await svc.get_active_held_amount(user.user_id, "ai")
    plan_info = await svc.get_user_plan(user.user_id)
    daily_cap = await svc.check_daily_application_cap(user.user_id)

    return {
        "apply_credits": {
            "available": apply_avail,
            "held": apply_held,
            "total": apply_avail + apply_held,
        },
        "ai_credits": {
            "available": ai_avail,
            "held": ai_held,
            "total": ai_avail + ai_held,
        },
        "plan": plan_info["plan"],
        "plan_name": plan_info["config"]["name"],
        "daily_limit": daily_cap,
    }


@router.get("/credits/ledger")
async def get_credit_ledger(
    credit_type: str | None = Query(None, description="Filter by 'apply' or 'ai'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get audit trail of credit allocations and debits."""
    svc = CreditsService(db)
    return await svc.get_ledger_history(
        user_id=user.user_id,
        credit_type=credit_type,
        page=page,
        page_size=page_size,
    )


@router.get("/plans")
async def get_available_plans() -> dict[str, Any]:
    """Return active subscription pricing and feature limits for Indian market."""
    return {"plans": PLANS_CONFIG}


@router.post("/credits/topup-demo")
async def topup_demo_credits(
    body: TopupDemoRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Top up credits for development/testing without requiring an external payment gateway."""
    svc = CreditsService(db)
    entry = await svc.grant_credits(
        user_id=user.user_id,
        amount=body.amount,
        credit_type=body.credit_type,
        reason=body.reason,
    )
    return {
        "granted": body.amount,
        "credit_type": body.credit_type,
        "balance_after": entry.balance_after,
        "success": True,
    }


@router.post("/billing/create-order")
async def create_billing_order(
    body: CreateOrderRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Order creation endpoint ready for Razorpay activation."""
    if body.plan_id not in PLANS_CONFIG:
        return {"error": "Invalid plan_id", "status": "failed"}

    plan = PLANS_CONFIG[body.plan_id]
    amount_inr = plan["price_inr"]

    # When live payment gateway is disabled/optional, return a structured sandbox order
    return {
        "order_id": f"order_sandbox_{user.user_id[:8]}_{body.plan_id}",
        "currency": "INR",
        "amount_paise": amount_inr * 100,
        "plan_id": body.plan_id,
        "gateway": "sandbox",
        "notes": "Razorpay gateway is in sandbox/mock mode as requested",
    }
