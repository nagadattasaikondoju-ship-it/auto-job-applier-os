"""Which applications Applyon can submit itself, and which hand off to the user.

Auto-submit is limited to ATS forms we support that don't put a CAPTCHA or login in front of the
form. Everything else (Lever's hCaptcha, Workday logins, LinkedIn, Naukri, company sites) is
prepared the same way but finished by the user in their own browser: we never bypass a CAPTCHA.
"""

from typing import Literal

from packages.jobs_sources.detector import detect_ats

AUTO_SUBMIT_ATS = frozenset({"greenhouse", "ashby"})

ApplyMode = Literal["auto", "assisted"]

ASSISTED_REASON = {
    "lever": "Lever protects every application form with a CAPTCHA, so you submit this one yourself.",
    "workday": "Workday asks you to sign in to apply, so you submit this one yourself.",
}
DEFAULT_ASSISTED_REASON = "This site can't be submitted automatically, so you submit this one yourself."


def apply_ats(ats_type: str | None, application_url: str | None) -> str:
    """The ATS of the form the user actually applies on (aggregator jobs record 'unknown')."""
    if ats_type and ats_type not in ("unknown", "generic"):
        return ats_type
    return detect_ats(application_url or "")


def apply_mode(ats_type: str | None, application_url: str | None) -> ApplyMode:
    return "auto" if apply_ats(ats_type, application_url) in AUTO_SUBMIT_ATS else "assisted"


def assisted_reason(ats_type: str | None, application_url: str | None) -> str:
    return ASSISTED_REASON.get(apply_ats(ats_type, application_url), DEFAULT_ASSISTED_REASON)
