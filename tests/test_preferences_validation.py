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
