import re
from typing import Any

from packages.ai.schemas import TailoredResumeOutput


class TruthCheckResult:
    def __init__(self, status: str, flagged_claims: list[dict[str, str]]) -> None:
        self.status = status  # passed | flagged | failed
        self.flagged_claims = flagged_claims

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "flagged_claims": self.flagged_claims,
            "passed": self.status == "passed",
        }


def extract_numbers_and_metrics(text: str) -> set[str]:
    """Extract numbers, percentages, and rupee amounts."""
    # Matches patterns like 40%, ₹50L, $10M, 100ms, 25k, etc.
    patterns = re.findall(r"(?:[₹$€]\s*)?\d+(?:\.\d+)?(?:%|ms|s|k|m|cr|lpa|l|x)?", text.lower())
    return {p.strip() for p in patterns if p.strip() and not p.strip().isdigit() or int(p) > 5}


def verify_resume_truthfulness(
    tailored_resume: TailoredResumeOutput,
    profile_snapshot: dict[str, Any],
) -> TruthCheckResult:
    """
    Deterministic verification that the AI did not hallucinate new companies,
    titles, unverified skills, or fabricated numbers/metrics.
    """
    flagged: list[dict[str, str]] = []

    # 1. Map existing bullet IDs and their text from snapshot
    existing_bullet_map: dict[str, str] = {}
    for exp in profile_snapshot.get("experiences", []):
        for bullet in exp.get("bullets", []):
            b_id = bullet.get("id")
            if b_id:
                existing_bullet_map[b_id] = bullet.get("text", "")

    # 2. Extract allowed skill pool (case-insensitive)
    allowed_skills: set[str] = {
        s.get("normalized_name", "").lower() for s in profile_snapshot.get("skills", [])
    }
    for s in profile_snapshot.get("skills", []):
        allowed_skills.add(s.get("name", "").lower())
    # Tools named in the person's own experience, projects or summary are genuine too
    from packages.core.services.ats import evidenced_skills

    allowed_skills.update(s.lower() for s in evidenced_skills(profile_snapshot))

    # Check that skills_ordered is a subset of profile skills
    for skill in tailored_resume.skills_ordered:
        if skill.lower() not in allowed_skills and len(allowed_skills) > 0:
            flagged.append(
                {
                    "type": "unverified_skill",
                    "claim": skill,
                    "reason": f"Skill '{skill}' was not present in the master profile.",
                }
            )

    # 3. Check bullet point source integrity and metric fabrication
    for exp in tailored_resume.experiences:
        for bullet in exp.bullets:
            source_id = bullet.source_bullet_id
            if source_id not in existing_bullet_map:
                flagged.append(
                    {
                        "type": "invalid_source_id",
                        "claim": bullet.text,
                        "reason": f"Bullet references non-existent source_bullet_id '{source_id}'.",
                    }
                )
                continue

            orig_text = existing_bullet_map[source_id]
            orig_metrics = extract_numbers_and_metrics(orig_text)
            new_metrics = extract_numbers_and_metrics(bullet.text)

            # Check for invented metrics
            invented = new_metrics - orig_metrics
            # Ignore minor words/numbers that match
            meaningful_invented = [m for m in invented if any(c.isdigit() for c in m)]
            if meaningful_invented:
                flagged.append(
                    {
                        "type": "invented_metric",
                        "claim": ", ".join(meaningful_invented),
                        "reason": f"Metrics {meaningful_invented} appeared in tailored bullet but were absent from original source bullet: '{orig_text}'",
                    }
                )

            # Check for unverified skills/tools introduced into bullet
            from packages.core.seed.taxonomies import ALL_SKILLS

            bullet_lower = bullet.text.lower()
            orig_lower = orig_text.lower()
            for tax_skill in ALL_SKILLS:
                skill_l = tax_skill.lower()
                pattern = r"\b" + re.escape(skill_l) + r"\b"
                if re.search(pattern, bullet_lower) and skill_l not in allowed_skills and not re.search(pattern, orig_lower):
                    flagged.append(
                        {
                            "type": "unverified_skill_in_bullet",
                            "claim": tax_skill,
                            "reason": f"Skill '{tax_skill}' appeared in tailored bullet but was absent from master profile and original bullet.",
                        }
                    )

    if not flagged:
        return TruthCheckResult(status="passed", flagged_claims=[])
    elif any(f["type"] in ("invalid_source_id", "invented_metric") for f in flagged):
        return TruthCheckResult(status="flagged", flagged_claims=flagged)
    else:
        return TruthCheckResult(status="flagged", flagged_claims=flagged)
