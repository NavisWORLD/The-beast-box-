"""Strict single-owner Azure Blob adapter for a separately hosted Beast Box runtime.

Offline source-level implementation; no account is automatically provisioned. The
caller must enforce owner authorization and own the durable metadata/index before
exposing these operations through an HTTP API. Do NOT use from a Vercel function.
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import secrets
from urllib.parse import urlsplit

MAX_FILE_BYTES = 10 * 1024 * 1024
MIME_EXTENSIONS = {
    "image/png": {".png"}, "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"}, "application/pdf": {".pdf"},
    "text/plain": {".txt", ".py", ".js", ".ts", ".tsx", ".csv", ".json"},
    "text/markdown": {".md"},
}


class OwnerStorageError(ValueError):
    pass


def validate_file(name: str, mime: str, data: bytes) -> None:
    if not isinstance(name, str) or not 1 <= len(name.encode("utf-8")) <= 180 or any(c in name for c in "/\\\r\n\x00"):
        raise OwnerStorageError("filename must be a safe basename (up to 180 UTF-8 bytes)")
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_FILE_BYTES:
        raise OwnerStorageError("file must contain 1..10 MiB of bytes")
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if mime not in MIME_EXTENSIONS or suffix not in MIME_EXTENSIONS[mime]:
        raise OwnerStorageError("unsupported MIME type/filename pairing")
    magic = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff",
             "image/webp": b"RIFF", "application/pdf": b"%PDF-"}
    if mime in magic and not data.startswith(magic[mime]):
        raise OwnerStorageError("file signature does not match declared MIME type")
    if mime == "image/webp" and data[8:12] != b"WEBP":
        raise OwnerStorageError("invalid WebP signature")
    if mime.startswith("text/"):
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OwnerStorageError("text file is not valid UTF-8") from exc


class AzureOwnerStore:
    """Storage operations are scoped to a verified private owner prefix."""

    def __init__(self, *, account_url: str, container: str, owner_id: str, service=None, content_settings_factory=None):
        parsed = urlsplit(account_url)
        if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment
                or not re.fullmatch(r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", parsed.hostname or "")):
            raise OwnerStorageError("expected the exact Azure Blob HTTPS account URL")
        if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61})[a-z0-9]", container) is None:
            raise OwnerStorageError("invalid private container name")
        if re.fullmatch(r"[a-f0-9]{32}", owner_id) is None:
            raise OwnerStorageError("owner_id must be 32 lowercase hex characters")
        self.owner_id = owner_id
        self._content_settings_factory = content_settings_factory
        self.prefix = "owners/" + owner_id + "/"
        if service is None:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.storage.blob import BlobServiceClient
            except ImportError as exc:
                raise OwnerStorageError("install azure-identity and azure-storage-blob on the durable host") from exc
            service = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential(exclude_interactive_browser_credential=True))
        self.container = service.get_container_client(container)

    def _blob(self, artifact_id: str):
        if not isinstance(artifact_id, str) or re.fullmatch(r"[a-f0-9]{32}", artifact_id) is None:
            raise OwnerStorageError("invalid object identifier")
        return self.container.get_blob_client(self.prefix + artifact_id)

    def _owned(self, artifact_id: str):
        blob = self._blob(artifact_id)
        properties = blob.get_blob_properties()
        metadata = properties.metadata or {}
        if metadata.get("owner") != self.owner_id:
            raise OwnerStorageError("blob owner verification failed")
        if properties.size > MAX_FILE_BYTES:
            raise OwnerStorageError("stored file exceeds size bound")
        return blob, properties

    def upload(self, *, filename: str, mime: str, content: bytes) -> dict:
        validate_file(filename, mime, content)
        artifact_id = secrets.token_hex(16)
        digest = hashlib.sha256(content).hexdigest()
        metadata = {"owner": self.owner_id, "sha256": digest,
                    "name_b64": base64.urlsafe_b64encode(filename.encode("utf-8")).decode("ascii"),
                    "mime": mime}
        if self._content_settings_factory is None:
            from azure.storage.blob import ContentSettings
            self._content_settings_factory = ContentSettings
        blob = self._blob(artifact_id)
        blob.upload_blob(io.BytesIO(content), overwrite=False,
                         content_settings=self._content_settings_factory(content_type=mime),
                         metadata=metadata, max_concurrency=1)
        return {"id": artifact_id, "filename": filename, "mime": mime,
                "size": len(content), "sha256": digest, "durability": "AZURE_BLOB_WRITE_ACKNOWLEDGED"}

    def download(self, artifact_id: str) -> tuple[bytes, dict]:
        blob, props = self._owned(artifact_id)
        data = blob.download_blob(max_concurrency=1).readall()
        if len(data) != props.size or hashlib.sha256(data).hexdigest() != props.metadata.get("sha256"):
            raise OwnerStorageError("blob content integrity mismatch")
        return data, {"id": artifact_id, "mime": props.metadata.get("mime", "application/octet-stream"),
                      "sha256": props.metadata["sha256"], "size": len(data)}

    def delete(self, artifact_id: str) -> dict:
        blob, _ = self._owned(artifact_id)
        blob.delete_blob()
        return {"deleted": artifact_id, "retention": "BLOB_DELETE_REQUESTED"}


