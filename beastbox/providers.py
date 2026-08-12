from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class TextProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


def _assert_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host == "localhost":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ValueError("local provider URL must resolve syntactically to localhost/loopback")


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
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return str(body.get("response", ""))


@dataclass
class ReferenceTextProvider:
    prefix: str = "COSMOS reference"

    def generate(self, prompt: str) -> str:
        compact = " ".join(prompt.split())
        return f"{self.prefix}: {compact[-700:]}"
