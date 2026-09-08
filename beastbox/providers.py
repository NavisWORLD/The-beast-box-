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
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 256}}).encode("utf-8")
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


@dataclass
class CompatibleChatProvider:
    """Chat Completions adapter; remote context delivery needs explicit HTTPS opt-in."""

    model: str
    base_url: str = 'http://127.0.0.1:1234/v1'
    allow_remote: bool = False
    api_key_env: str | None = None
    timeout: float = 120.0

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if not self.model.strip() or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
            raise ValueError('provider requires a model and URL without embedded credentials, query or fragment')
        try:
            _assert_loopback(self.base_url)
        except ValueError:
            if self.allow_remote is not True or parsed.scheme != 'https' or not parsed.hostname:
                raise ValueError('remote provider requires explicit --allow-remote and HTTPS') from None

    def generate(self, prompt: str) -> str:
        import os
        headers = {'Content-Type': 'application/json'}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key or any(c in key for c in '\r\n'):
                raise ValueError('configured API key environment variable is missing or invalid')
            headers['Authorization'] = 'Bearer ' + key
        payload = {'model': self.model, 'messages': [{'role': 'user', 'content': prompt}],
                   'stream': False, 'temperature': 0, 'max_tokens': 256}
        request = urllib.request.Request(self.base_url.rstrip('/') + '/chat/completions',
                                         data=json.dumps(payload).encode(), headers=headers, method='POST')
        try:
            with _local_opener().open(request, timeout=self.timeout) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError('oversized response')
            content = json.loads(raw)['choices'][0]['message']['content']
            if not isinstance(content, str):
                raise ValueError('non-text response')
            return content
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            raise ValueError('compatible model backend unavailable or returned invalid text; no fallback') from None
