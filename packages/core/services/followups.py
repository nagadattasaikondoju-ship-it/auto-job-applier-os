"""Follow-up assistant: short, polite follow-up emails after an application goes quiet."""

from datetime import UTC, datetime
from typing import Any

from packages.ai.client import AIUnavailableError, gemini_client
from packages.core.services.ats import WEAK_PHRASES, has_metric


def pick_highlight(bullets: list[str]) -> str | None:
    """The strongest real achievement to mention: measurable and not weakly phrased."""
    strong = [b.strip() for b in bullets if b and b.strip() and not any(w in b.lower() for w in WEAK_PHRASES)]
    measured = [b for b in strong if has_metric(b)]
    best = measured or strong
    return best[0].rstrip(".") if best else None


def template_follow_up(name: str, job_title: str, company: str, applied_on: datetime | None, highlight: str | None) -> dict[str, str]:
    """Deterministic follow-up used when no AI key is configured."""
    when = f"{applied_on.day} {applied_on:%B}" if applied_on else "recently"
    first = (name or "").split(" ")[0] or "there"
    highlight_line = f" Recently, I {highlight[0].lower() + highlight[1:]}." if highlight else ""
    body = (
        f"Hi,\n\n"
        f"I applied for the {job_title} role at {company} on {when} and wanted to follow up. "
        f"I'm still very interested in the position and would love to learn about next steps.{highlight_line}\n\n"
        f"Happy to share anything else that would help. Thank you for your time.\n\n"
        f"Best regards,\n{name or first}"
    )
    return {"subject": f"Following up on my application for {job_title}", "body": body}


async def draft_follow_up(
    name: str,
    job_title: str,
    company: str,
    applied_on: datetime | None,
    highlight: str | None,
    tone: str = "professional",
) -> dict[str, Any]:
    if gemini_client.is_mock:
        return {**template_follow_up(name, job_title, company, applied_on, highlight), "ai": False}

    days = (datetime.now(UTC) - applied_on).days if applied_on else None
    prompt = (
        f"Write a short follow-up email (max 110 words) from {name} to a recruiter at {company} "
        f"about their application for {job_title}"
        + (f", submitted {days} days ago" if days is not None else "")
        + f". Tone: {tone}. Mention this real achievement once if it fits: {highlight or 'none'}. "
        "Do not invent anything else. No subject line in the body. Sign off with the candidate's name."
    )
    try:
        body = (await gemini_client.generate_text(prompt, temperature=0.4, max_output_tokens=300)).strip()
    except AIUnavailableError:
        body = ""
    if len(body) < 40:
        return {**template_follow_up(name, job_title, company, applied_on, highlight), "ai": False}
    return {"subject": f"Following up on my application for {job_title}", "body": body, "ai": True}
