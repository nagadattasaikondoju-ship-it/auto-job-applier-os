"""Generic fallback browser automation adapter for standard career forms."""

from typing import Any

from apps.browser.adapters.base import BaseAtsAdapter


class GenericAdapter(BaseAtsAdapter):
    """Fallback adapter attempting standard DOM inputs and heuristic matching."""

    ats_name: str = "generic"

    async def fill_fields_playwright(self, page: Any, fields: list[dict[str, Any]]) -> int:
        filled = 0
        for f in fields:
            val = f.get("value")
            if val is None or f.get("field_type") == "file":
                continue

            selector = f.get("dom_selector")
            if not selector and f.get("canonical_key"):
                selector = f"input[name*='{f['canonical_key']}' i], textarea[name*='{f['canonical_key']}' i]"

            if selector:
                try:
                    locator = page.locator(selector).first
                    if await locator.is_visible(timeout=1000):
                        if f.get("field_type") == "select":
                            await locator.select_option(label=str(val))
                        else:
                            await locator.fill(str(val))
                        filled += 1
                except Exception:
                    pass

        return filled

    async def submit_playwright(self, page: Any) -> bool:
        submit_btn = page.locator("button[type='submit'], input[type='submit']").first
        if await submit_btn.is_visible(timeout=2000):
            await submit_btn.click()
            return True
        return False
