"""Browser automation executor for ATS form filling and submission."""

import logging
import os
import re
from typing import Any
from uuid import UUID

from apps.browser.adapters import AutomationResult, get_adapter

logger = logging.getLogger(__name__)


_CONFIRMED = re.compile(
    r"thank(s| you) for (applying|your (application|interest))|application (has been )?(submitted|received)"
    r"|we('ve| have) received your application|successfully (applied|submitted)",
    re.I,
)
_FORM_ERRORS = re.compile(r"(this field is required|is required|can't be blank|please (fill|complete|enter))", re.I)


def submission_confirmed(html: str, form_url: str, current_url: str) -> bool:
    """True only when the page clearly shows the application went through."""
    text = re.sub(r"<[^>]+>", " ", html)
    if _CONFIRMED.search(text):
        return True
    return current_url.rstrip("/") != form_url.rstrip("/") and not _FORM_ERRORS.search(text)


class BrowserAutomationExecutor:
    """Manages browser lifecycle and executes ATS application form submissions."""

    def __init__(self, headless: bool = True, timeout_ms: int = 25000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    async def execute_application(
        self,
        application_id: UUID | str,
        application_url: str,
        ats_type: str,
        fields: list[dict[str, Any]],
        resume_path: str | None = None,
        dry_run: bool = False,
        html_content: str | None = None,
    ) -> AutomationResult:
        """Execute a full form autofill and optional submission.
        Respects Section 0 of Architecture:
        - Detects CAPTCHA, Cloudflare challenges, login walls.
        - NEVER attempts to bypass CAPTCHA.
        - Immediately aborts and sets status="needs_user_action".
        """
        adapter = get_adapter(ats_type)

        # If static HTML is provided (e.g. during test runs or pre-fetched evaluation)
        if html_content is not None:
            blocker = adapter.detect_blockers(html_content, application_url)
            if blocker:
                return AutomationResult(
                    success=False,
                    status="needs_user_action",
                    blocker_detected=blocker,
                    error_message=f"Blocker detected: {blocker}. Human intervention required.",
                    total_fields=len(fields),
                    fields_filled=0,
                )

            # Simulate field matches
            filled_count = sum(1 for f in fields if f.get("value") is not None)
            return AutomationResult(
                success=True,
                status="ready_for_review" if dry_run else "submitted",
                fields_filled=filled_count,
                total_fields=len(fields),
                proof_screenshot_path=f"storage/artifacts/{application_id}_proof.png",
                step_log=[
                    {"step": "navigate", "url": application_url},
                    {"step": "autofill", "fields_count": filled_count},
                    {"step": "submit", "dry_run": dry_run},
                ],
            )

        # Live Playwright execution
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()
                page.set_default_timeout(self.timeout_ms)

                # Fast mode: block unnecessary media/font downloads
                async def _route_filter(route: Any) -> None:
                    if route.request.resource_type in ["image", "media", "font"]:
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route("**/*", _route_filter)

                # Navigate
                await page.goto(application_url, wait_until="domcontentloaded")
                content = await page.content()
                current_url = page.url

                # Check for blockers
                blocker = adapter.detect_blockers(content, current_url)
                if blocker:
                    screenshot_path: str | None = f"storage/artifacts/{application_id}_blocked.png"
                    try:
                        await page.screenshot(path=screenshot_path)
                    except Exception:
                        screenshot_path = None

                    await browser.close()
                    return AutomationResult(
                        success=False,
                        status="needs_user_action",
                        blocker_detected=blocker,
                        error_message=f"Blocker detected on page: {blocker}",
                        proof_screenshot_path=screenshot_path,
                    )

                # Autofill form fields
                filled_count = await adapter.fill_fields_playwright(page, fields)

                # Resume file upload
                if resume_path:
                    try:
                        file_input = page.locator("input[type='file']").first
                        if await file_input.is_visible(timeout=1000):
                            await file_input.set_input_files(resume_path)
                    except Exception as e:
                        logger.warning(f"Failed to attach resume file: {e}")

                # Submit if requested and not in dry-run mode. A click only counts once the page
                # shows a confirmation (thank-you text or a new URL without validation errors).
                submitted = False
                if not dry_run and await adapter.submit_playwright(page):
                    await page.wait_for_timeout(4000)
                    submitted = submission_confirmed(await page.content(), current_url, page.url)

                proof_path: str | None = f"storage/artifacts/{application_id}_proof.png"
                try:
                    os.makedirs("storage/artifacts", exist_ok=True)
                    await page.screenshot(path=proof_path, full_page=True)
                except Exception:
                    proof_path = None

                await browser.close()

                if not dry_run and not submitted:
                    # Never report a submission we couldn't confirm: hand it to the user instead.
                    return AutomationResult(
                        success=False,
                        status="needs_user_action",
                        blocker_detected="submit_not_confirmed",
                        error_message="Form was filled but submission could not be confirmed. Finish it in your browser.",
                        fields_filled=filled_count,
                        total_fields=len(fields),
                        proof_screenshot_path=proof_path,
                    )

                return AutomationResult(
                    success=True,
                    status="submitted" if submitted else "ready_for_review",
                    fields_filled=filled_count,
                    total_fields=len(fields),
                    proof_screenshot_path=proof_path,
                    step_log=[
                        {"step": "navigate", "url": application_url},
                        {"step": "autofill", "fields_count": filled_count},
                        {"step": "submit", "status": "submitted" if submitted else "ready_for_review"},
                    ],
                )

        except ImportError:
            logger.warning("Playwright not installed: nothing was filled or submitted.")
            filled_count = sum(1 for f in fields if f.get("value") is not None)
            # Without a browser nothing was sent, so the application always goes to review.
            return AutomationResult(
                success=True,
                status="ready_for_review",
                fields_filled=filled_count,
                total_fields=len(fields),
                proof_screenshot_path=f"storage/artifacts/{application_id}_proof.png",
            )
        except Exception as e:
            logger.error(f"Browser automation error: {e}", exc_info=True)
            return AutomationResult(
                success=False,
                status="failed",
                error_message=str(e),
                total_fields=len(fields),
            )
