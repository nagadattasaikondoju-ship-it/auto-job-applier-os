"""ATS browser automation adapters registry."""

from apps.browser.adapters.base import AutomationResult, BaseAtsAdapter
from apps.browser.adapters.generic import GenericAdapter
from apps.browser.adapters.greenhouse import GreenhouseAdapter
from apps.browser.adapters.lever import LeverAdapter

ADAPTERS: dict[str, type[BaseAtsAdapter]] = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": GenericAdapter,
    "workable": GenericAdapter,
    "generic": GenericAdapter,
}


def get_adapter(ats_type: str) -> BaseAtsAdapter:
    """Return appropriate adapter instance for detected ATS."""
    cls = ADAPTERS.get(ats_type.lower(), GenericAdapter)
    return cls()


__all__ = ["AutomationResult", "BaseAtsAdapter", "get_adapter"]
