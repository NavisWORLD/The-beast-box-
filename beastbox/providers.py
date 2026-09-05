from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Protocol


class TextProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


def _assert_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username is not None or parsed.password is not None or parsed.fragment or parsed.query:
        raise ValueError("local provider requires HTTP(S) without credentials, query or fragment")
    host = parsed.hostname or ""
    if host == "localhost":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ValueError("local provider URL must resolve syntactically to localhost/loopback")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "local provider redirects are forbidden", headers, fp)


def _local_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


@dataclass
class LocalOllamaProvider:
    """Local-only Ollama text provider. Arbitrary remote model URLs are rejected."""

    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    timeout: float = 120.0

    def __post_init__(self) -> None:
        _assert_loopback(self.base_url)

    def generate(self, prompt: str) -> str:
        endpoint = self.base_url.rstrip("/") + "/api/generate"
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with _local_opener().open(req, timeout=self.timeout) as response:
            raw = response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("local provider response exceeds one MiB")
        body = json.loads(raw.decode("utf-8"))
        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            raise ValueError("local provider response field is missing or invalid")
        return body["response"]


@dataclass
class ReferenceTextProvider:
    prefix: str = "COSMOS reference"

    def generate(self, prompt: str) -> str:
        compact = " ".join(prompt.split())
        return f"{self.prefix}: {compact[-700:]}"
