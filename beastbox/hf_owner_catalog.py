"""Read-only owner's Hugging Face repository catalog.

The Hub lists *repositories*, not a guarantee that each saved weight has a
working Chat Completions endpoint. COSMOS historical weights are separately
identified as research artifacts, not silently presented as hosted inference.
No network call here performs inference, downloads weights or incurs model use.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

OWNER = "phera-ra"
API = "https://huggingface.co/api/models?author=phera-ra&limit=100"
ID = re.compile(r"phera-ra/[A-Za-z0-9_.-]{1,150}\\Z", re.I)
MAX_BYTES = 1024 * 1024

# Multiple models and a native engine can share one HF research repository.
# Never claim these weights are individually deployed or compatible with the
# generic HF inference router merely because their repository is accessible.
RESEARCH_ARTIFACTS = (
    {"name": "PHOS / dyn12", "repository": "phera-ra/QC67_cosmo",
     "status": "CUSTOM_WEIGHTS_REQUIRE_PINNED_ADAPTER"},
    {"name": "SAMGO / 54D", "repository": "phera-ra/QC67_cosmo",
     "status": "CUSTOM_WEIGHTS_REQUIRE_PINNED_ADAPTER"},
    {"name": "COSMIC.CYPHER", "repository": "NavisWORLD/The-beast-box-",
     "status": "ENGINE_WORKSPACE_NOT_STANDALONE_CHAT_CHECKPOINT"},
)


class CatalogUnavailable(RuntimeError):
    """Sanitized Hub inventory failure: do not disclose tokens or URLs."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CatalogUnavailable("HF_CATALOG_REDIRECT_REJECTED")


def list_owner_models(token: str | None = None, *, opener=None) -> dict:
    if token is not None and (not isinstance(token, str) or
                              len(token) > 4096 or any(c in token for c in "\\r\\n\\x00")):
        raise CatalogUnavailable("HF_CATALOG_CREDENTIAL_INVALID")
    headers = {"Accept": "application/json", "User-Agent": "BeastBox-Owner-Catalog/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(API, headers=headers, method="GET")
    client = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with client.open(request, timeout=7) as response:
            payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise CatalogUnavailable("HF_CATALOG_TOO_LARGE")
        found = json.loads(payload)
    except CatalogUnavailable:
        raise
    except (ValueError, TypeError, urllib.error.URLError, TimeoutError, OSError):
        raise CatalogUnavailable("HF_CATALOG_UNAVAILABLE") from None
    if not isinstance(found, list) or len(found) > 100:
        raise CatalogUnavailable("HF_CATALOG_INVALID")
    models = []
    seen = set()
    for raw in found:
        if not isinstance(raw, dict):
            raise CatalogUnavailable("HF_CATALOG_INVALID")
        ident = raw.get("id")
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            # Ignore Hub-side inconsistent entries, never allow other users'
            # repo IDs to enter our owner-selection allowlist.
            continue
        if ident in seen:
            continue
        seen.add(ident)
        task = raw.get("pipeline_tag")
        if not isinstance(task, str) or len(task) > 64:
            task = "unspecified"
        research = ident.lower() == "phera-ra/qc67_cosmo"
        selectable = task == "text-generation" and not research
        models.append({
            "id": ident, "task": task, "private": raw.get("private") is True,
            "selectable": selectable,
            "status": ("ROUTER_ACCESS_UNVERIFIED" if selectable else
                       "CUSTOM_RESEARCH_WEIGHTS" if research else "NO_VERIFIED_CHAT_ADAPTER"),
            "url": "https://huggingface.co/" + ident,
        })
    models.sort(key=lambda value: value["id"].lower())
    return {
        "owner": OWNER, "status": "HF_OWNER_REPOSITORY_LIST_ONLY",
        "models": models, "research_artifacts": list(RESEARCH_ARTIFACTS),
        "inference_attested": False, "model_invoked": False,
        "checkpoint_downloaded": False,
    }
