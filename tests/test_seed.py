from packages.core.seed.city_aliases import normalize_city
from packages.core.seed.field_label_synonyms import lookup_canonical_field
from packages.core.seed.plans import CREDIT_COSTS, PLANS_CONFIG
from packages.core.seed.taxonomies import ROLE_TAXONOMY, SKILL_TAXONOMY


def test_city_normalization() -> None:
    assert normalize_city("Bangalore") == "Bengaluru"
    assert normalize_city("bangalore urban") == "Bengaluru"
    assert normalize_city("Bombay") == "Mumbai"
    assert normalize_city("Gurgaon") == "Gurugram"
    assert normalize_city("Remote") == "Remote"
    assert normalize_city("Unknown City XYZ") == "Unknown City Xyz"


def test_field_label_synonyms_lookup() -> None:
    assert lookup_canonical_field("Notice Period (in days)") == "notice_period_days"
    assert lookup_canonical_field("Current CTC (in LPA)*") == "current_ctc_lpa"
    assert lookup_canonical_field("LinkedIn Profile URL") == "linkedin_url"
    assert lookup_canonical_field("Attach Resume:") == "resume_file"
    assert lookup_canonical_field("Why this company?") == "why_this_company"
    assert lookup_canonical_field("Totally Unknown Random Question") is None


def test_plans_configuration() -> None:
    assert "free" in PLANS_CONFIG
    assert "starter" in PLANS_CONFIG
    assert "pro" in PLANS_CONFIG
    assert "elite" in PLANS_CONFIG

    assert PLANS_CONFIG["free"]["auto_submit_allowed"] is False
    assert PLANS_CONFIG["pro"]["auto_submit_allowed"] is True
    assert PLANS_CONFIG["elite"]["priority_queue"] is True

    assert CREDIT_COSTS["resume_tailoring"] == 1
    assert CREDIT_COSTS["auto_submit"] == 2


def test_taxonomies_structure() -> None:
    assert "software_engineering" in ROLE_TAXONOMY
    assert "languages" in SKILL_TAXONOMY
    assert "Python" in SKILL_TAXONOMY["languages"]
