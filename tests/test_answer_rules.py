"""Rule-based answers for common application questions."""

from types import SimpleNamespace

from packages.core.services.answer_resolver import ProfileFacts, dedupe_fields, rule_based_answer
from packages.core.services.form_schema import FieldDefinition

PROFILE = SimpleNamespace(
    notice_period_days=30, current_ctc_lpa=10.0, expected_ctc_lpa=14.0, city="Hyderabad", country="India",
    willing_to_relocate=False, work_authorization={}, current_title="Data Analyst", headline="Data Analyst",
)
FACTS = ProfileFacts(
    profile=PROFILE, prefs=SimpleNamespace(locations=["Hyderabad", "Bengaluru"], remote_mode=["hybrid", "remote"]),
    skills=["SQL", "Python"],
    titles=["Data Analyst"],
)


def ask(label: str, ftype: str = "text") -> object:
    return rule_based_answer(FieldDefinition(field_id="q", label=label, field_type=ftype), FACTS)


def test_compensation_and_notice_in_many_phrasings() -> None:
    assert ask("CTC") == "10 LPA" and ask("What is your current compensation?") == "10 LPA"
    assert ask("ECTC") == "14 LPA" and ask("What is your expected compensation?") == "14 LPA"
    assert ask("Expected CTC (in LPA)", "number") == 14.0
    assert ask("How soon can you join us?") == "30 days" and ask("Notice Period", "number") == 30
    assert ask("Where do you currently reside?") == "Hyderabad, India"


def test_yes_no_questions_only_when_the_profile_supports_them() -> None:
    assert ask("Do you have prior experience in Product Analytics?") == "Yes"
    assert ask("Do you have experience with Kubernetes?") is None
    assert ask("Are you comfortable working from our Bangalore office?") == "Yes"
    assert ask("Are you willing to relocate to Pune?") is None  # not willing, not a chosen city
    # hybrid, not on-site: a full-time office commitment is the user's call
    assert ask("Are you willing to work 5 days a week from our Bangalore office?") is None
    assert ask("Will you now or in the future require sponsorship?") is None
    assert ask("Are you able to work in the United States?") is None


def test_duplicate_standard_fields_are_dropped() -> None:
    fields = [
        FieldDefinition(field_id="first_name", label="First Name", canonical_key="first_name"),
        FieldDefinition(field_id="resume", label="Resume", canonical_key="resume", field_type="file"),
        FieldDefinition(field_id="q1", label="First Name", canonical_key="first_name"),
        FieldDefinition(field_id="q2", label="Resume/CV", canonical_key="resume_file", field_type="file"),
        FieldDefinition(field_id="q3", label="CTC"),
    ]
    assert [f.field_id for f in dedupe_fields(fields)] == ["first_name", "resume", "q3"]
