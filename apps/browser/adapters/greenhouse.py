"""Greenhouse ATS browser automation adapter."""

from typing import Any

from apps.browser.adapters.base import BaseAtsAdapter


class GreenhouseAdapter(BaseAtsAdapter):
    """Fills Greenhouse board application forms."""

    ats_name: str = "greenhouse"

    async def fill_fields_playwright(self, page: Any, fields: list[dict[str, Any]]) -> int:
        """Autofill form fields using Playwright async page."""
        filled = 0

        # Standard field mapping
        for f in fields:
            key = f.get("canonical_key")
            val = f.get("value")
            if val is None:
                continue

            selector = None
            if key == "first_name":
                selector = "#first_name"
            elif key == "last_name":
                selector = "#last_name"
            elif key == "email":
                selector = "#email"
            elif key == "phone":
                selector = "#phone"
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
        """Click submit button on Greenhouse form."""
        submit_btn = page.locator("#submit_app, button[type='submit']").first
        if await submit_btn.is_visible(timeout=2000):
            await submit_btn.click()
            return True
        return False
