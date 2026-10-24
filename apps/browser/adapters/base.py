"""Base interface and common blocker detection for ATS browser automation adapters."""

import re
from typing import Any

from pydantic import BaseModel


class AutomationResult(BaseModel):
    """Result of a browser automation fill or submission run."""

    success: bool
    status: str  # submitted | ready_for_review | needs_user_action | failed
    blocker_detected: str | None = None
    fields_filled: int = 0
    total_fields: int = 0
    proof_screenshot_path: str | None = None
    error_message: str | None = None
    step_log: list[dict[str, Any]] = []


class BaseAtsAdapter:
    """Base class for ATS form filling and blocker detection."""

    ats_name: str = "generic"

    BLOCKER_PATTERNS = [
        (r"hcaptcha\.com|cf-turnstile|recaptcha/api|g-recaptcha|arkoselabs", "captcha_detected"),
        (r"cf-browser-verification|challenge-running|cloudflare", "anti_bot_challenge"),
        (r"sign[\s-]in to apply|log[\s-]in to apply|create account to apply", "login_wall"),
        (r"workday\.com.*(login|sign-in)", "login_wall"),
    ]

    def detect_blockers(self, html_content: str, current_url: str) -> str | None:
        """Scan HTML and URL for anti-bot, CAPTCHA, or mandatory login walls.
        Per Section 0 of Architecture: Zero bypass. Stop immediately and flag needs_user_action.
        """
        lower_html = html_content.lower()
        lower_url = current_url.lower()

        for pattern, blocker_type in self.BLOCKER_PATTERNS:
            if re.search(pattern, lower_html) or re.search(pattern, lower_url):
                return blocker_type
        return None

    async def fill_fields_playwright(self, page: Any, fields: list[dict[str, Any]]) -> int:
        """Fill the form on a Playwright page; returns how many fields were filled."""
        raise NotImplementedError

    async def submit_playwright(self, page: Any) -> bool:
        """Click the form's submit button; returns whether a click happened."""
        raise NotImplementedError

    def match_element_for_field(self, field: dict[str, Any], page_elements: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Helper to match field with page elements by selector or label."""
        field_id = field.get("field_id", "").lower()
        field_label = field.get("label", "").lower()

        for el in page_elements:
            el_id = el.get("id", "").lower()
            el_name = el.get("name", "").lower()
            el_label = el.get("label", "").lower()

            if field_id and (el_id == field_id or el_name == field_id):
                return el
            if field_label and field_label in el_label:
                return el
        return None
