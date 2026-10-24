from typing import Any

PLANS_CONFIG: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Free",
        "price_inr": 0,
        "monthly_ai_credits": 10,
        "monthly_apply_credits": 10,
        "daily_application_limit": 5,
        "auto_submit_allowed": False,
        "priority_queue": False,
        "features": [
            "Master Profile & Resume Parsing",
            "10 Curated Job Matches / Week",
            "Chrome Extension Autofill",
            "Basic ATS-Friendly Resume",
        ],
    },
    "starter": {
        "name": "Starter",
        "price_inr": 499,
        "monthly_ai_credits": 50,
        "monthly_apply_credits": 50,
        "daily_application_limit": 15,
        "auto_submit_allowed": False,
        "priority_queue": False,
        "features": [
            "50 Tailored Applications / Month",
            "Unlimited Job Matches & Alerts",
            "Few-Shot AI Screening Answers",
            "Deterministic Truth Checker",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_inr": 1499,
        "monthly_ai_credits": 200,
        "monthly_apply_credits": 200,
        "daily_application_limit": 30,
        "auto_submit_allowed": True,
        "priority_queue": False,
        "features": [
            "200 Tailored Applications / Month",
            "Autopilot Continuous Auto-Apply",
            "Assisted Apply with Step Screenshots",
            "Company-Tailored Cover Letters",
        ],
    },
    "elite": {
        "name": "Elite",
        "price_inr": 2999,
        "monthly_ai_credits": 500,
        "monthly_apply_credits": 500,
        "daily_application_limit": 60,
        "auto_submit_allowed": True,
        "priority_queue": True,
        "features": [
            "500 Tailored Applications / Month",
            "Dedicated Priority Worker Queue",
            "Multi-Resume Version Management",
            "Full Application Event Audit Trail",
        ],
    },
}

CREDIT_COSTS: dict[str, int] = {
    "resume_tailoring": 1,  # AI credit
    "cover_letter": 1,  # AI credit
    "screening_answers": 1,  # AI credit per application
    "extension_autofill": 1,  # Apply credit
    "assisted_apply": 1,  # Apply credit
    "auto_submit": 2,  # Apply credit
    "priority_processing": 1,  # Additional credit
}
