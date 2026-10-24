"""Lever ATS browser automation adapter."""

from typing import Any

from apps.browser.adapters.base import BaseAtsAdapter


class LeverAdapter(BaseAtsAdapter):
    """Fills Lever posting application forms."""

    ats_name: str = "lever"

    async def fill_fields_playwright(self, page: Any, fields: list[dict[str, Any]]) -> int:
        """Autofill form fields using Playwright async page."""
        filled = 0

        for f in fields:
            key = f.get("canonical_key")
            val = f.get("value")
            if val is None:
                continue

            selector = None
            if key == "full_name":
                selector = "input[name='name']"
            elif key == "email":
                selector = "input[name='email']"
            elif key == "phone":
                selector = "input[name='phone']"
            elif key == "current_company":
                selector = "input[name='org']"
            elif key == "linkedin_url":
                selector = "input[name='urls[LinkedIn]']"
            elif key == "github_url":
                selector = "input[name='urls[GitHub]']"
            elif key == "portfolio_url":
                selector = "input[name='urls[Portfolio]']"
            elif f.get("dom_selector"):
                selector = f["dom_selector"]

            if selector:
                try:
                    locator = page.locator(selector).first
                    if await locator.is_visible(timeout=1000):
                        if f.get("field_type") == "select":
                            await locator.select_option(label=str(val))
                        elif f.get("field_type") != "file":
                            await locator.fill(str(val))
                        filled += 1
                except Exception:
                    pass

        return filled

    async def submit_playwright(self, page: Any) -> bool:
        """Click submit button on Lever form."""
        submit_btn = page.locator("button[type='submit'], .template-btn-submit").first
        if await submit_btn.is_visible(timeout=2000):
            await submit_btn.click()
            return True
        return False
