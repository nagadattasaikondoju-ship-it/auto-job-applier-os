"""Slow application pages: one retry rescues a slow first load; a dead page gets a clear message."""

import asyncio
import contextlib
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from apps.browser.executor import BrowserAutomationExecutor, is_navigation_timeout

FORM = b"<html><body><form><input name='name'><button type='submit'>Submit application</button></form></body></html>"


def _chromium_available() -> bool:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) or os.path.isdir("/opt/pw-browsers")


pytestmark = pytest.mark.skipif(not _chromium_available(), reason="needs Playwright Chromium")


def _serve(delays: list[float]) -> tuple[ThreadingHTTPServer, str]:
    """Serve FORM, sleeping delays[i] seconds before the i-th page request (last delay repeats)."""
    calls = {"n": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            i = min(calls["n"], len(delays) - 1)
            calls["n"] += 1
            time.sleep(delays[i])
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with contextlib.suppress(BrokenPipeError):  # the browser gave up on this request
                self.wfile.write(FORM)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/apply"


def _run(url: str) -> object:
    executor = BrowserAutomationExecutor(timeout_ms=2000, navigation_timeout_ms=1500)
    return asyncio.run(
        executor.execute_application("t1", url, "generic", [{"label": "Name", "value": "Asha"}], dry_run=True)
    )


def test_slow_first_load_is_retried() -> None:
    server, url = _serve([3.0, 0.0])
    try:
        result = _run(url)
    finally:
        server.shutdown()
    assert result.status == "ready_for_review", result.error_message


def test_page_that_never_loads_gets_a_clear_message() -> None:
    server, url = _serve([3.0])
    try:
        result = _run(url)
    finally:
        server.shutdown()
    assert result.status == "failed"
    assert "didn't load in time" in (result.error_message or "")
    assert "Timeout" not in (result.error_message or "")


def test_is_navigation_timeout() -> None:
    class TimeoutError(Exception):  # same name as Playwright's
        pass

    assert is_navigation_timeout(TimeoutError("Page.goto: Timeout 25000ms exceeded."))
    assert not is_navigation_timeout(TimeoutError("Locator.click: Timeout 2000ms exceeded."))
    assert not is_navigation_timeout(ValueError("Page.goto: net::ERR_NAME_NOT_RESOLVED"))
