"""Read-only owner Hugging Face catalog; listing is not inference entitlement.

Uses a fixed official HTTPS host, excludes redirected URLs and fails closed on
malformed/oversized responses. Research checkpoints are visible but never
claimed to be available through the hosted text-generation router.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

OWNER = "phera-ra"
OWNER_ID = re.compile(r"phera-ra/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
MAX_BYTES = 320_000
MAX_MODELS = 100


class CatalogUnavailable(RuntimeError):
    """A sanitized read-only inventory failure."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        raise CatalogUnavailable("Hugging Face catalog redirect refused")


def fetch_owner_models(*, opener=None) -> dict:
    """List the public HF user's published model IDs, never private resources.

    Text-generation + Transformers metadata is only a *candidate* for router
    serving, not proof of compatibility, account access or successful inference.
    """
    url = "https://huggingface.co/api/models?" + urllib.parse.urlencode(
        {"author": OWNER, "limit": MAX_MODELS, "full": "false"}
    )
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    client = opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect()
    )
    try:
        with client.open(request, timeout=6) as response:
            if response.status != 200:
                raise CatalogUnavailable("Hugging Face owner inventory unavailable")
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CatalogUnavailable("Hugging Face owner inventory too large")
        payload = json.loads(raw)
    except CatalogUnavailable:
        raise
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CatalogUnavailable("Hugging Face owner inventory unavailable") from None
    if not isinstance(payload, list) or len(payload) > MAX_MODELS:
        raise CatalogUnavailable("Invalid Hugging Face inventory")
    records: list[dict[str, object]] = []
    used: set[str] = set()
    for row in payload:
        if not isinstance(row, dict):
            raise CatalogUnavailable("Invalid Hugging Face inventory")
        model_id = row.get("id")
        if not isinstance(model_id, str) or OWNER_ID.fullmatch(model_id) is None:
            raise CatalogUnavailable("Unexpected model owner or identifier")
        if model_id in used:
            continue
        used.add(model_id)
        task = row.get("pipeline_tag")
        library = row.get("library_name")
        task = task if isinstance(task, str) and len(task) < 80 else "unspecified"
        library = library if isinstance(library, str) and len(library) < 80 else "unspecified"
        # Do not conflate a model-card task tag with an actual routable endpoint.
        candidate = task == "text-generation" and library == "transformers"
        records.append({
            "id": model_id, "task": task, "library": library,
            "router_candidate": candidate,
            "selection_state": "CANDIDATE_UNVERIFIED" if candidate else "RESEARCH_OR_UNSUPPORTED",
        })
    records.sort(key=lambda record: str(record["id"]).lower())
    return {
        "provider": "huggingface", "owner": OWNER, "models": records,
        "status": "PUBLIC_OWNER_CATALOG_ONLY", "account_access_verified": False,
        "inference_attested": False, "model_invoked": False,
        "private_models_included": False,
    }
