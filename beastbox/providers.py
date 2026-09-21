from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Protocol

# Compatible-provider profiles carry the *name* of a host secret variable rather
# than the credential value. The environment inventory reports this separately
# from fixed Beast configuration; it is not an exemption for ordinary env reads.
__beastbox_dynamic_env_contract__ = "secret-reference-v1"


class TextProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


# Fixed vocabulary only: provider response bodies, tokens, URLs, user prompts,
# and exception strings must not cross the owner-bridge diagnostics boundary.
PROVIDER_FAILURE_CODES = frozenset({
    "MODEL_AUTH_REJECTED", "MODEL_ACCESS_DENIED", "MODEL_NOT_FOUND",
    "MODEL_RATE_LIMITED", "MODEL_TIMEOUT", "MODEL_UNAVAILABLE",
    "MODEL_OUTPUT_EMPTY", "MODEL_BAD_RESPONSE",
})


class ProviderDiagnosticError(ValueError):
    """Provider failure with a bounded, non-sensitive failure code."""

    def __init__(self, code: str):
        if code not in PROVIDER_FAILURE_CODES:
            raise ValueError("unsupported provider failure code")
        self.code = code
        super().__init__("compatible model backend unavailable or returned invalid text; no fallback")


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
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 256:
            raise ValueError("Ollama requires an explicit installed model name (1–256 characters)")
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
    # Injected from an encrypted host-only vault, never serialized to a profile.
    api_key: str | None = field(default=None, repr=False, compare=False)

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
        if self.api_key is not None:
            if not self.api_key or any(c in self.api_key for c in '\r\n'):
                raise ValueError('configured provider credential is invalid')
            headers['Authorization'] = 'Bearer ' + self.api_key
        elif self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key or any(c in key for c in '\r\n'):
                raise ValueError('configured API key environment variable is missing or invalid')
            headers['Authorization'] = 'Bearer ' + key
        payload = {'model': self.model, 'messages': [{'role': 'user', 'content': prompt}],
                   'stream': False, 'temperature': 0, 'max_tokens': 256}
        if self.base_url.rstrip('/') == 'https://ollama.com/v1' and self.model.startswith('gpt-oss:'):
            # GPT-OSS can exhaust a tiny output budget on reasoning before
            # producing user-facing content. Explicitly request low reasoning;
            # maintain the existing 256-token spending bound and no retries.
            payload['reasoning_effort'] = 'low'
        request = urllib.request.Request(self.base_url.rstrip('/') + '/chat/completions',
                                         data=json.dumps(payload).encode(), headers=headers, method='POST')
        try:
            with _local_opener().open(request, timeout=self.timeout) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ProviderDiagnosticError('MODEL_BAD_RESPONSE')
            data = json.loads(raw)
            content = data['choices'][0]['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ProviderDiagnosticError('MODEL_OUTPUT_EMPTY')
            return content
        except urllib.error.HTTPError as exc:
            # Never read/expose upstream body or headers. A 200 from the
            # chat-job status endpoint does not confirm upstream success.
            code = {
                401: 'MODEL_AUTH_REJECTED',
                403: 'MODEL_ACCESS_DENIED',
                404: 'MODEL_NOT_FOUND',
                408: 'MODEL_TIMEOUT',
                429: 'MODEL_RATE_LIMITED',
            }.get(exc.code, 'MODEL_UNAVAILABLE')
            raise ProviderDiagnosticError(code) from None
        except TimeoutError:
            raise ProviderDiagnosticError('MODEL_TIMEOUT') from None
        except ProviderDiagnosticError:
            raise
        except OSError:
            raise ProviderDiagnosticError('MODEL_UNAVAILABLE') from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderDiagnosticError('MODEL_BAD_RESPONSE') from None
