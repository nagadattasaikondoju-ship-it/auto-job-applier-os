"""Preferences accept what people actually type: rupee CTCs, long lists, duplicates."""

from apps.api.routers.preferences import PreferencesPayload


def test_rupee_ctc_converted_to_lakhs() -> None:
    p = PreferencesPayload(current_ctc_lpa=600000, expected_ctc_lpa="1200000", min_salary_lpa=500000)
    assert (p.current_ctc_lpa, p.expected_ctc_lpa, p.min_salary_lpa) == (6.0, 12.0, 5.0)
    assert PreferencesPayload(current_ctc_lpa=8.5).current_ctc_lpa == 8.5


def test_long_lists_trimmed_not_rejected() -> None:
    p = PreferencesPayload(
        target_roles=[f"Role {i}" for i in range(14)],
        role_keywords=[f"kw{i}" for i in range(45)],
        locations=["Bengaluru", "bengaluru ", "", *[f"City {i}" for i in range(20)]],
    )
    assert len(p.target_roles) == 10 and len(p.role_keywords) == 30 and len(p.locations) == 15
    assert p.locations[0] == "Bengaluru" and p.locations.count("Bengaluru") == 1


async def test_validation_error_names_the_field(client) -> None:  # type: ignore[no-untyped-def]
    resp = await client.put("/v1/preferences", json={"daily_application_limit": 500}, headers={"X-Dev-User-Id": "pref-val-user"})
    assert resp.status_code == 422
    assert resp.json()["error"]["message"] == "Please check: daily application limit"


async def test_salary_saved_before_resume_is_kept(client) -> None:  # type: ignore[no-untyped-def]
    """'I don't have a resume yet': CTC and notice must survive until the profile exists."""
    import uuid

    h = {"X-Dev-User-Id": f"no-resume-{uuid.uuid4().hex[:8]}"}
    body = {
        "target_roles": ["Data Analyst"],
        "locations": ["Bengaluru"],
        "current_ctc_lpa": 0,
        "expected_ctc_lpa": 9,
        "notice_period_days": 15,
    }
    saved = (await client.put("/v1/preferences", json=body, headers=h)).json()
    assert (saved["current_ctc_lpa"], saved["expected_ctc_lpa"], saved["notice_period_days"]) == (0, 9, 15)
    again = (await client.get("/v1/preferences", headers=h)).json()
    assert (again["current_ctc_lpa"], again["expected_ctc_lpa"], again["notice_period_days"]) == (0, 9, 15)

    # The profile created later picks the answers up
    assert (await client.put("/v1/profile", json={"full_name": "Asha Rao"}, headers=h)).status_code == 200
    profile = (await client.get("/v1/profile", headers=h)).json()
    flat = {**profile, **(profile.get("profile") or {})}
    assert (flat["current_ctc_lpa"], flat["expected_ctc_lpa"], flat["notice_period_days"]) == (0, 9, 15)


def test_stale_preparing_is_released() -> None:
    """A first batch killed by a restart must not leave 'Preparing…' on screen forever."""
    from datetime import UTC, datetime, timedelta

    from apps.api.routers.autopilot import _preparing_state

    now = datetime.now(UTC)
    assert _preparing_state({"preparing": True, "preparing_since": now.isoformat()})[0] is True
    stale, batch = _preparing_state({"preparing": True, "preparing_since": (now - timedelta(minutes=30)).isoformat()})
    assert stale is False and batch and "interrupted" in batch["stopped_reason"]
    assert _preparing_state({"preparing": True})[0] is False  # flagged before timestamps existed
    assert _preparing_state({"preparing": False, "last_batch": {"prepared": 2}}) == (False, {"prepared": 2})
