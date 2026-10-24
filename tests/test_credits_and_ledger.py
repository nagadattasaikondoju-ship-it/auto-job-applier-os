"""Tests for Phase 8: Credit balances, reservation holds, ledger accounting, and plans."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from packages.core.models.identity import CreditHold, CreditsLedger
from packages.core.services.credits import CreditsService


@pytest.mark.asyncio
async def test_credits_balance_and_grant():
    """Verify granting credits updates ledger and computes balances accurately."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    _ = CreditsLedger(
        id=uuid.uuid4(),
        user_id=user_id,
        credit_type="apply",
        amount=50,
        reason="starter_plan_grant",
        balance_after=50,
        idempotency_key=f"init_{user_id}",
        created_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Mock sum scalar query
    mock_res = MagicMock()
    mock_res.scalar.return_value = 50
    mock_db.execute.return_value = mock_res

    svc = CreditsService(mock_db)
    total = await svc.get_total_ledger_balance(user_id, "apply")
    assert total == 50

    # Test grant
    mock_res_exist = MagicMock()
    mock_res_exist.scalars.return_value.first.return_value = None
    mock_db.execute.side_effect = [mock_res_exist, mock_res]

    new_entry = await svc.grant_credits(
        user_id=user_id,
        amount=10,
        credit_type="apply",
        reason="referral_bonus",
    )
    assert new_entry.amount == 10
    assert new_entry.balance_after == 60


@pytest.mark.asyncio
async def test_credit_reservation_hold_and_capture():
    """Verify reserving holds locks available balance and capture debits ledger."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    hold_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    svc = CreditsService(mock_db)

    # Mock available balance = 10
    with (
        patch.object(svc, "get_available_balance", new_callable=AsyncMock) as mock_avail,
        patch.object(svc, "get_total_ledger_balance", new_callable=AsyncMock) as mock_total,
    ):
        mock_avail.return_value = 10
        mock_total.return_value = 10

        # Reserve hold
        hold = await svc.reserve_hold(user_id=user_id, amount=2, credit_type="apply")
        assert hold.status == "held"
        assert hold.amount == 2

        # Capture hold
        mock_hold = CreditHold(
            id=hold_id,
            user_id=user_id,
            credit_type="apply",
            amount=2,
            task_id="task-1",
            status="held",
            expires_at=datetime.now(UTC),
        )
        mock_hold_res = MagicMock()
        mock_hold_res.scalars.return_value.first.return_value = mock_hold
        mock_db.execute.return_value = mock_hold_res

        ledger_debit = await svc.capture_hold(hold_id=hold_id, reason="applied_to_job")
        assert mock_hold.status == "captured"
        assert ledger_debit.amount == -2
        assert ledger_debit.balance_after == 8


@pytest.mark.asyncio
async def test_insufficient_credits_rejection():
    """Verify reserving holds fails with HTTP 402 when balance is zero."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    mock_db = AsyncMock()
    svc = CreditsService(mock_db)

    with patch.object(svc, "get_available_balance", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = 0

        with pytest.raises(HTTPException) as exc_info:
            await svc.reserve_hold(user_id=user_id, amount=1, credit_type="apply")

        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["code"] == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_credit_hold_release():
    """Verify releasing hold restores available balance without ledger debit."""
    hold_id = uuid.uuid4()
    mock_hold = CreditHold(
        id=hold_id,
        user_id="user-123",
        credit_type="apply",
        amount=1,
        task_id="task-1",
        status="held",
        expires_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_hold
    mock_db.execute.return_value = mock_res
    mock_db.flush = AsyncMock()

    svc = CreditsService(mock_db)
    await svc.release_hold(hold_id=hold_id, reason="captcha_blocked")
    assert mock_hold.status == "released"


@pytest.mark.asyncio
async def test_credits_api_endpoints():
    """Test credit balance, plans list, topup-demo, and billing order endpoints."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with (
            patch(
                "packages.core.services.credits.CreditsService.get_available_balance",
                new_callable=AsyncMock,
            ) as mock_avail,
            patch(
                "packages.core.services.credits.CreditsService.get_active_held_amount",
                new_callable=AsyncMock,
            ) as mock_held,
            patch(
                "packages.core.services.credits.CreditsService.get_user_plan",
                new_callable=AsyncMock,
            ) as mock_plan,
            patch(
                "packages.core.services.credits.CreditsService.check_daily_application_cap",
                new_callable=AsyncMock,
            ) as mock_cap,
            patch(
                "packages.core.services.credits.CreditsService.grant_credits",
                new_callable=AsyncMock,
            ) as mock_grant,
        ):
            mock_avail.return_value = 25
            mock_held.return_value = 2
            mock_plan.return_value = {
                "plan": "starter",
                "config": {"name": "Starter", "daily_application_limit": 15},
            }
            mock_cap.return_value = {
                "can_apply": True,
                "count_today": 3,
                "daily_limit": 15,
                "remaining_today": 12,
            }
            mock_entry = MagicMock()
            mock_entry.balance_after = 35
            mock_grant.return_value = mock_entry

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Check balance
                bal_resp = await ac.get("/v1/credits/balance", headers=headers)
                assert bal_resp.status_code == 200
                data = bal_resp.json()
                assert data["apply_credits"]["available"] == 25
                assert data["plan"] == "starter"
                assert data["daily_limit"]["remaining_today"] == 12

                # 2. Get plans list
                plans_resp = await ac.get("/v1/plans")
                assert plans_resp.status_code == 200
                assert "free" in plans_resp.json()["plans"]
                assert "starter" in plans_resp.json()["plans"]

                # 3. Top up demo credits
                topup_resp = await ac.post(
                    "/v1/credits/topup-demo",
                    json={"amount": 10, "credit_type": "apply"},
                    headers=headers,
                )
                assert topup_resp.status_code == 200
                assert topup_resp.json()["balance_after"] == 35

                # 4. Create billing order (sandbox)
                order_resp = await ac.post(
                    "/v1/billing/create-order",
                    json={"plan_id": "starter"},
                    headers=headers,
                )
                assert order_resp.status_code == 200
                assert "order_id" in order_resp.json()
                assert order_resp.json()["currency"] == "INR"
    finally:
        app.dependency_overrides.pop(get_db, None)
