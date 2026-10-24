"""Tests for rule-based matching: role/location patterns, seniority, experience and scoring."""

from types import SimpleNamespace

from packages.core.services.match_rules import (
    estimate_experience_years,
    location_patterns,
    role_title_patterns,
    rule_based_score,
    title_allowed,
)


def job(title: str, skills: list[str], description: str = "") -> SimpleNamespace:
    return SimpleNamespace(title=title, required_skills=skills, description_text=description)


def test_role_patterns_include_synonyms_and_drop_generic_words() -> None:
    pats = role_title_patterns(["Frontend Engineer"])
    assert "%frontend%" in pats and "%front-end%" in pats and "%react%" in pats
    assert "%engineer%" not in pats  # too generic on its own
    assert "%sde%" in role_title_patterns(["Software Engineer"])
    assert role_title_patterns(["Engineer"]) == ["%engineer%"]  # nothing else to go on


def test_location_aliases() -> None:
    pats = location_patterns(["Bengaluru", "Delhi NCR", "Remote"])
    assert "%bangalore%" in pats and "%gurgaon%" in pats and "%noida%" in pats
    assert all("remote" not in p for p in pats)


def test_seniority_title_filter() -> None:
    assert title_allowed("Frontend Engineer", "junior")
    assert not title_allowed("Senior Frontend Engineer", "junior")
    assert not title_allowed("Engineering Manager", "fresher")
    assert title_allowed("Software Engineer Intern", "fresher")
    assert not title_allowed("Software Engineer Intern", "mid")
    assert title_allowed("Staff Engineer", "senior")
    assert title_allowed("Senior Software Engineer", "mid")
    assert not title_allowed("SDE III", "mid") and not title_allowed("SDE-  IV  / Lead Engineer", "mid")
    assert not title_allowed("Staff Engineer", "mid")
    assert title_allowed("SDE II", "mid")


def test_experience_estimate_from_dates() -> None:
    exps = [
        SimpleNamespace(start_date="Jan 2020", end_date="Dec 2021", is_current=False),
        SimpleNamespace(start_date="2022-01", end_date=None, is_current=True),
    ]
    assert estimate_experience_years(exps) >= 4.5


def test_rule_score_prefers_relevant_jobs() -> None:
    skills = ["React", "TypeScript", "Node.js", "Jest"]
    good = rule_based_score(skills, ["Frontend Engineer"], job("Frontend Engineer", ["React", "TypeScript"], "React apps"), 70)
    bad = rule_based_score(skills, ["Frontend Engineer"], job("Collections Manager", ["Excel"], "Debt recovery"), 70)
    assert good["match_score"] > bad["match_score"]
    assert good["decision"] == "apply" and bad["decision"] == "skip"
    assert any("React" in r for r in good["fit_reasons"])
    assert bad["gaps"] == ["Excel isn't in your profile"]
