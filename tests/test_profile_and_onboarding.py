import uuid

from packages.ai.schemas import (
    TailoredBullet,
    TailoredExperience,
    TailoredResumeOutput,
)
from packages.ai.truth_checker import verify_resume_truthfulness
from packages.core.models.profile import Education, Experience, Profile, Skill
from packages.core.services.onboarding import get_next_question_from_state
from packages.core.services.profile import compute_profile_completeness


def test_profile_completeness_scoring() -> None:
    # 1. Empty profile
    empty_result = compute_profile_completeness(None)
    assert empty_result["score"] == 0
    assert empty_result["can_start_autopilot"] is False

    # 2. Complete master profile
    profile = Profile(
        user_id="user-123",
        full_name="Naga Datta Sai",
        email="naga@example.com",
        phone="+91 9876543210",
        city="Bengaluru",
        headline="Senior AI Systems Engineer",
        summary="Experienced Full Stack and AI Engineer",
        expected_ctc_lpa=25.0,
        notice_period_days=30,
        work_authorization={"India": True},
    )
    experiences = [
        Experience(
            id=uuid.uuid4(),
            user_id="user-123",
            company="Tech Corp",
            title="Software Engineer",
            start_date="2023-01",
            bullets=[{"id": "b1", "text": "Built real-time streaming pipeline."}],
        )
    ]
    educations = [
        Education(
            id=uuid.uuid4(),
            user_id="user-123",
            institution="IIT",
            degree="B.Tech",
            field="Computer Science",
            grade="8.8",
        )
    ]
    skills = [
        Skill(id=uuid.uuid4(), user_id="user-123", name="Python", normalized_name="python"),
        Skill(id=uuid.uuid4(), user_id="user-123", name="FastAPI", normalized_name="fastapi"),
        Skill(id=uuid.uuid4(), user_id="user-123", name="TypeScript", normalized_name="typescript"),
    ]

    res = compute_profile_completeness(profile, experiences, educations, skills)
    assert res["score"] >= 80
    assert res["can_start_autopilot"] is True
    assert len(res["missing_fields"]) == 0


def test_truth_checker_prevents_hallucination() -> None:
    snapshot = {
        "skills": [
            {"name": "Python", "normalized_name": "python"},
            {"name": "FastAPI", "normalized_name": "fastapi"},
        ],
        "experiences": [
            {
                "bullets": [
                    {
                        "id": "b1",
                        "text": "Engineered async task queue handling 50k jobs daily.",
                    }
                ]
            }
        ],
    }

    # Case A: Valid tailored resume (all source bullets exist, no fabricated metrics)
    valid_tailored = TailoredResumeOutput(
        summary="Backend specialist in FastAPI.",
        skills_ordered=["Python", "FastAPI"],
        experiences=[
            TailoredExperience(
                experience_id="exp-1",
                company="Tech Corp",
                title="Engineer",
                bullets=[
                    TailoredBullet(
                        source_bullet_id="b1",
                        text="Engineered async task queue handling 50k jobs daily with high reliability.",
                    )
                ],
            )
        ],
        keywords_used=["FastAPI", "Python"],
        changes_made=["Emphasized reliability"],
    )
    result_valid = verify_resume_truthfulness(valid_tailored, snapshot)
    assert result_valid.status == "passed"

    # Case B: Adversarial case: AI invented a 99% reduction metric absent from original bullet
    fabricated_tailored = TailoredResumeOutput(
        summary="Backend engineer",
        skills_ordered=["Python", "FastAPI"],
        experiences=[
            TailoredExperience(
                experience_id="exp-1",
                company="Tech Corp",
                title="Engineer",
                bullets=[
                    TailoredBullet(
                        source_bullet_id="b1",
                        text="Engineered async task queue handling 50k jobs daily and reduced server latency by 99% saving ₹50L.",
                    )
                ],
            )
        ],
        keywords_used=[],
        changes_made=[],
    )
    result_fabricated = verify_resume_truthfulness(fabricated_tailored, snapshot)
    assert result_fabricated.status == "flagged"
    assert any(claim["type"] == "invented_metric" for claim in result_fabricated.flagged_claims)

    # Case C: Adversarial case: Invented skill absent from profile
    invented_skill_tailored = TailoredResumeOutput(
        summary="Kubernetes Expert",
        skills_ordered=["Python", "FastAPI", "Kubernetes", "Rust"],
        experiences=[
            TailoredExperience(
                experience_id="exp-1",
                company="Tech Corp",
                title="Engineer",
                bullets=[
                    TailoredBullet(
                        source_bullet_id="b1",
                        text="Engineered async task queue handling 50k jobs daily.",
                    )
                ],
            )
        ],
        keywords_used=[],
        changes_made=[],
    )
    result_skill = verify_resume_truthfulness(invented_skill_tailored, snapshot)
    assert result_skill.status == "flagged"
    assert any(claim["type"] == "unverified_skill" for claim in result_skill.flagged_claims)


def test_adaptive_questionnaire_navigation() -> None:
    # Initially no answers
    next_q = get_next_question_from_state(stored_answers={})
    assert next_q["completed"] is False
    assert next_q["question"]["id"] == "target_roles"

    # When target_roles answered, moves to seniority
    next_q2 = get_next_question_from_state(stored_answers={"target_roles": ["Backend Engineer"]})
    assert next_q2["completed"] is False
    assert next_q2["question"]["id"] == "seniority"
