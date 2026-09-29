from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from ..providers import _assert_loopback, _local_opener

Message = dict[str, str]


class LocalChatModel(Protocol):
    def chat(self, messages: Sequence[Message]) -> str: ...
    def complete(self, prompt: str) -> str: ...


@dataclass
class ModelSpec:
    alias: str
    backend: str
    model: str
    base_url: str | None = None
    context: int = 8192
    temperature: float = 0.2
    max_tokens: int = 2048
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelSpec":
        return cls(alias=str(value["alias"]), backend=str(value["backend"]), model=str(value["model"]), base_url=value.get("base_url"), context=int(value.get("context", 8192)), temperature=float(value.get("temperature", 0.2)), max_tokens=int(value.get("max_tokens", 2048)), options=dict(value.get("options") or {}))


def assert_loopback(url: str) -> None:
    _assert_loopback(url)


def _post_json(url: str, payload: dict[str, Any], timeout: float = 180.0,
               *, bearer: str | None = None) -> dict[str, Any]:
    assert_loopback(url)
    headers = {"Content-Type": "application/json"}
    if bearer is not None:
        if len(bearer) < 32 or any(ch in bearer for ch in (chr(10), chr(13))):
            raise ValueError("invalid host-only local model credential")
        if url != "http://127.0.0.1:8771/v1/chat/completions":
            raise ValueError("host-only bearer restricted to original QC67 loopback")
        headers["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    with _local_opener().open(req, timeout=timeout) as response:
        raw = response.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("local model response exceeds one MiB")
    body = json.loads(raw.decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("local model response must be an object")
    return body


@dataclass
class OllamaChatModel:
    spec: ModelSpec

    def __post_init__(self) -> None:
        self.base_url = self.spec.base_url or "http://127.0.0.1:11434"
        assert_loopback(self.base_url)

    def chat(self, messages: Sequence[Message]) -> str:
        body = _post_json(self.base_url.rstrip("/") + "/api/chat", {"model": self.spec.model, "messages": list(messages), "stream": False, "options": {"temperature": self.spec.temperature, "num_ctx": self.spec.context, **dict(self.spec.options.get("ollama_options") or {})}})
        message = body.get("message") or {}
        return str(message.get("content", ""))

    def complete(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])


@dataclass
class OpenAICompatibleLocalModel:
    """Local OpenAI-compatible adapter for llama.cpp server, LM Studio and similar servers."""
    spec: ModelSpec

    def __post_init__(self) -> None:
        self.base_url = self.spec.base_url or "http://127.0.0.1:8080"
        assert_loopback(self.base_url)

    def _endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        return base + "/chat/completions" if base.endswith("/v1") else base + "/v1/chat/completions"

    def chat(self, messages: Sequence[Message]) -> str:
        body = _post_json(self._endpoint(), {"model": self.spec.model, "messages": list(messages), "temperature": self.spec.temperature, "max_tokens": self.spec.max_tokens, **dict(self.spec.options.get("request") or {})})
        choices = body.get("choices") or []
        if not choices:
            return ""
        return str((choices[0].get("message") or {}).get("content", ""))

    def complete(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])


@dataclass
class QC67OriginalChatModel:
    """Owner-only original native model for COSMIC.CYPHER; tool JSON not guaranteed."""
    spec: ModelSpec

    def __post_init__(self) -> None:
        self.base_url = self.spec.base_url or "http://127.0.0.1:8771/v1"
        if (self.base_url.rstrip("/") != "http://127.0.0.1:8771/v1"
                or self.spec.model not in {"qc67-phos", "qc67-samgo"}):
            raise ValueError("QC67 coder requires the exact original model and loopback")

    def chat(self, messages: Sequence[Message]) -> str:
        if not messages or any(m.get("role") not in {"system", "user", "assistant"}
                               or not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("invalid coding session")
        key = os.environ.get("RAWRPHOS_API_KEY", "")
        prompt = "\n".join(m["role"].upper() + ": " + m["content"] for m in messages)
        data = _post_json(self.base_url + "/chat/completions",
                          {"model": self.spec.model,
                           "messages": [{"role": "user", "content": prompt}],
                           "stream": False, "temperature": 0,
                           "max_tokens": min(24 if self.spec.model == "qc67-phos" else 32,
                                             max(1, self.spec.max_tokens))},
                          bearer=key, timeout=120.0)
        return str(data["choices"][0]["message"]["content"])

    def complete(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])


class LlamaCppPythonModel:
    """Direct GGUF inference through optional llama-cpp-python."""
    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec
        path = Path(spec.model).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeError("Direct GGUF mode requires llama-cpp-python. Install with: pip install -e '.[local-llm]'") from exc
        kwargs: dict[str, Any] = {"model_path": str(path), "n_ctx": spec.context, "n_gpu_layers": int(spec.options.get("n_gpu_layers", 0)), "verbose": bool(spec.options.get("verbose", False))}
        if spec.options.get("chat_format"):
            kwargs["chat_format"] = str(spec.options["chat_format"])
        if "seed" in spec.options:
            kwargs["seed"] = int(spec.options["seed"])
        self._llama = Llama(**kwargs)

    def chat(self, messages: Sequence[Message]) -> str:
        result = self._llama.create_chat_completion(messages=list(messages), temperature=self.spec.temperature, max_tokens=self.spec.max_tokens)
        choices = result.get("choices") or []
        if not choices:
            return ""
        return str((choices[0].get("message") or {}).get("content", ""))

    def complete(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])


def create_model(spec: ModelSpec) -> LocalChatModel:
    backend = spec.backend.strip().lower().replace("_", "-")
    if backend == "ollama":
        return OllamaChatModel(spec)
    if backend == "qc67-original":
        return QC67OriginalChatModel(spec)
    if backend in {"openai-compatible", "llama.cpp-server", "llama-server", "lm-studio"}:
        return OpenAICompatibleLocalModel(spec)
    if backend in {"llama-cpp-python", "gguf", "llama-cpp"}:
        return LlamaCppPythonModel(spec)
    raise ValueError(f"unsupported local backend {spec.backend!r}; expected ollama, llama-cpp-python/gguf, llama.cpp-server, lm-studio, or openai-compatible or qc67-original")


def list_ollama_models(base_url: str = "http://127.0.0.1:11434", timeout: float = 4.0) -> list[str]:
    assert_loopback(base_url)
    with _local_opener().open(base_url.rstrip("/") + "/api/tags", timeout=timeout) as response:
        raw = response.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("local model list exceeds one MiB")
    data = json.loads(raw.decode("utf-8"))
    out: list[str] = []
    for item in data.get("models") or []:
        name = item.get("name") or item.get("model")
        if name:
            out.append(str(name))
    return sorted(set(out))
