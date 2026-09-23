"""Read-only Ollama direct API model inventory for an authenticated owner.

The fixed public endpoint must not receive a saved API key. Listing a name
never attests the owner's entitlement, quota, latency or successful inference.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .providers import _local_opener

PUBLIC_MODELS_URL = "https://ollama.com/v1/models"
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,179}\Z")
MAX_INVENTORY_BYTES = 256_000
MAX_MODELS = 512


class ModelInventoryUnavailable(ValueError):
    """A fixed, non-sensitive failure code; never surface upstream bodies."""


def fetch_public_models(opener=None) -> list[str]:
    """Retrieve canonical direct API IDs without inference, secrets or retries."""
    request = urllib.request.Request(PUBLIC_MODELS_URL, headers={"Accept": "application/json"}, method="GET")
    try:
        with (opener or _local_opener()).open(request, timeout=6) as response:
            if response.status != 200:
                raise ModelInventoryUnavailable("Public Ollama inventory unavailable")
            raw = response.read(MAX_INVENTORY_BYTES + 1)
        if len(raw) > MAX_INVENTORY_BYTES:
            raise ModelInventoryUnavailable("Public Ollama inventory too large")
        result = json.loads(raw)
        entries = result["data"]
        if not isinstance(entries, list) or len(entries) > MAX_MODELS:
            raise ModelInventoryUnavailable("Public Ollama inventory unavailable")
        ids = sorted({
            item["id"] for item in entries if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and MODEL_ID.fullmatch(item["id"])
            and not item["id"].endswith("-cloud")
        })
        if not ids:
            raise ModelInventoryUnavailable("Public Ollama inventory unavailable")
        return ids
    except ModelInventoryUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise ModelInventoryUnavailable("Public Ollama inventory unavailable") from None
