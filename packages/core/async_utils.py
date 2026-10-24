import asyncio
import threading
from collections.abc import Coroutine
from typing import Any

# Thread-local storage to cache an event loop per worker thread
_thread_local = threading.local()


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Retrieve or create a persistent asyncio event loop for the current thread."""
    loop = getattr(_thread_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop
    return loop


def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine synchronously inside a Celery worker.
    Reuses the persistent event loop of the current worker thread.
    """
    loop = get_worker_event_loop()
    return loop.run_until_complete(coro)
