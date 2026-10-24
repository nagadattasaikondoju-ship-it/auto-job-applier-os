"""Evaluation runner executing quality benchmarks against the golden dataset."""

import json
from pathlib import Path
from typing import Any

from packages.ai.schemas import TailoredBullet, TailoredExperience, TailoredResumeOutput
from packages.ai.truth_checker import verify_resume_truthfulness


def run_golden_eval() -> dict[str, Any]:
    """Execute complete eval suite and compute core quality metrics."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    adversarial_cases = data.get("tailoring_adversarial_cases", [])
    matching_cases = data.get("matching_test_cases", [])

    total_adversarial = len(adversarial_cases)
    caught_fabrications = 0
    passed_without_catch = 0

    # 1. Evaluate Truth Checker on Adversarial Hallucination Cases
    for case in adversarial_cases:
        master_b = case["master_bullet"]
        injected_b = case["injected_bullet"]

        profile_snapshot = {
            "full_name": "Test Candidate",
            "skills": [{"name": s} for s in master_b.get("skills", [])],
            "experiences": [
                {
                    "id": "exp_1",
                    "company": "Tech Corp",
                    "title": "Software Engineer",
                    "bullets": [master_b],
                }
            ],
        }

        skills_ordered = [str(s["name"]) for s in profile_snapshot["skills"] if isinstance(s, dict) and "name" in s]

        tailored = TailoredResumeOutput(
            summary="Tailored summary",
            skills_ordered=skills_ordered,
            experiences=[
                TailoredExperience(
                    experience_id="exp_1",
                    company="Tech Corp",
                    title="Software Engineer",
                    bullets=[
                        TailoredBullet(
                            source_bullet_id=injected_b["source_bullet_id"],
                            text=injected_b["text"],
                        )
                    ],
                )
            ],
            keywords_used=[],
            changes_made=[],
        )

        res = verify_resume_truthfulness(
            tailored_resume=tailored,
            profile_snapshot=profile_snapshot,
        )
        if res.status in ("flagged", "failed"):
            caught_fabrications += 1
        else:
            passed_without_catch += 1

    fabrication_rate = passed_without_catch / total_adversarial if total_adversarial else 0.0

    # 2. Evaluate Matching Accuracy
    matching_correct = 0
    total_matching = len(matching_cases)
    for m_case in matching_cases:
        cand = m_case["candidate"]
        job = m_case["job"]
        expected = m_case["expected_decision"]

        # Deterministic match heuristic check
        exp_gap = abs(cand["exp_years"] - ((job["exp_min"] + job["exp_max"]) / 2.0))
        skill_overlap = len(set(cand["skills"]) & set(job["skills"])) / max(1, len(job["skills"]))

        predicted = "apply" if (exp_gap <= 2.0 and skill_overlap >= 0.5) else "skip"
        if predicted == expected:
            matching_correct += 1

    matching_accuracy = matching_correct / total_matching if total_matching else 1.0

    report = {
        "total_adversarial_cases": total_adversarial,
        "caught_fabrications": caught_fabrications,
        "fabrication_rate": fabrication_rate,
        "total_matching_cases": total_matching,
        "matching_accuracy": matching_accuracy,
        "passed": (fabrication_rate == 0.0 and matching_accuracy >= 0.90),
    }

    return report


if __name__ == "__main__":
    results = run_golden_eval()
    print(json.dumps(results, indent=2))
