"""Explicit, bounded read-only Azure Blob retrieval for one authenticated owner.

This module never lists a container, writes objects, selects a model, stores
memory or submits a quantum job. The owner must supply one exact blob name.
Source content is untrusted data; approval to share with a model is separate.
"""
from __future__ import annotations

import hashlib
import re

MAX_CONTEXT_BYTES = 12_000
SAFE_BLOB = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,179}\Z")
TEXT_EXTENSIONS = (".txt", ".md", ".json", ".csv")


class AzureReadError(ValueError):
    """Sanitized only. Do not attach SDK exception contents."""


def read_owner_text(record: dict, blob_name: str, *, service=None) -> dict:
    """Read precisely one owner-selected textual Blob, at most 12 KB.

    Caller must enforce authenticated single-owner access and explicit consent.
    The record is read from the server-side encrypted vault, never from the
    request or browser. This method does not persist or share returned data.
    """
    if (not isinstance(blob_name, str) or not SAFE_BLOB.fullmatch(blob_name)
            or any(segment in ("", ".", "..") for segment in blob_name.split("/"))
            or not blob_name.lower().endswith(TEXT_EXTENSIONS)):
        raise AzureReadError("Select one exact .txt, .md, .json or .csv blob name")
    if not isinstance(record, dict) or set(record) != {"config", "secret"}:
        raise AzureReadError("Azure credential unavailable")
    config = record["config"]
    if config.get("auth_mode", "container_sas") not in ("container_sas", "account_key"):
        raise AzureReadError("Azure credential mode unavailable")
    if service is None:
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise AzureReadError("Azure SDK unavailable on the durable host") from None
        service = BlobServiceClient(
            account_url="https://" + config["account"] + ".blob.core.windows.net",
            credential=record["secret"],
        )
    try:
        blob = service.get_blob_client(container=config["container"], blob=blob_name)
        props = blob.get_blob_properties(timeout=5, retry_total=0)
        size = props.size
        if type(size) is not int or size < 1 or size > MAX_CONTEXT_BYTES:
            raise AzureReadError("Azure document exceeds the 12 KB read-only limit")
        content_type = getattr(getattr(props, "content_settings", None), "content_type", "")
        if content_type not in ("text/plain", "text/markdown", "application/json",
                                "text/csv", "application/octet-stream", ""):
            raise AzureReadError("Azure document is not an allowed text type")
        raw = blob.download_blob(offset=0, length=MAX_CONTEXT_BYTES + 1,
                                 timeout=5, max_concurrency=1, retry_total=0).readall()
        if not isinstance(raw, bytes) or len(raw) != size:
            raise AzureReadError("Azure document size verification failed")
        text = raw.decode("utf-8")
        if not text.strip():
            raise AzureReadError("Azure document is empty")
        return {
            "source": "AZURE_BLOB_EXPLICIT_READ", "blob_name": blob_name,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "text": text, "retrieval_verified": True,
            "persisted": False, "model_invoked": False,
            "source_claims_verified": False,
        }
    except AzureReadError:
        raise
    except UnicodeDecodeError:
        raise AzureReadError("Azure document is not UTF-8 text") from None
    except Exception:
        # SDK messages often contain signed URLs, account names and request IDs.
        raise AzureReadError("Azure document read unavailable or denied") from None
