"""Private Hugging Face ZeroGPU RAWRPHØS adapter for the COSMOS text-provider contract.

This is a Gradio Space API, NOT an OpenAI chat-completions endpoint. It uses
only the exact owner Space and known 12K checkpoint; credentials are injected
from the encrypted owner vault, never persisted in a model profile or browser.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from concurrent.futures import TimeoutError as FutureTimeout
from .providers import ProviderDiagnosticError

SPACE_ID = "phera-ra/rawrphos-12k-zerogpu"
SPACE_URL = "https://huggingface.co/spaces/" + SPACE_ID
MODEL = "rawrphos-native"
STEP = 12000
WEIGHT_SHA = "339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601"
MAX_PROMPT_CHARS = 1000
MAX_OUTPUT_TOKENS = 32


def profile() -> dict:
    return {"kind": "hf_space", "model": MODEL, "base_url": SPACE_URL,
            "allow_remote": True, "api_key_env": None}


def check_identity(result: object) -> bool:
    return (isinstance(result, dict)
            and result.get("model_id") == MODEL
            and result.get("training_steps") == STEP
            and result.get("checkpoint_sha256") == WEIGHT_SHA
            and result.get("ready") is True
            and result.get("serving_backend") == "pytorch-zerogpu")


@dataclass
class PrivateSpaceProvider:
    """One authenticated, explicitly selected, quota-limited remote model."""

    model: str = MODEL
    base_url: str = SPACE_URL
    allow_remote: bool = True
    api_key: str | None = field(default=None, repr=False, compare=False)
    timeout: float = 100.0

    def __post_init__(self) -> None:
        if self.model != MODEL or self.base_url != SPACE_URL or self.allow_remote is not True:
            raise ValueError("unknown private RAWRPHOS endpoint; exact model required")

    def _client(self):
        if (not isinstance(self.api_key, str) or len(self.api_key) < 20
                or any(x in self.api_key for x in "\r\n")):
            raise ProviderDiagnosticError("MODEL_AUTH_REJECTED")
        try:
            from gradio_client import Client
            return Client(SPACE_ID, hf_token=self.api_key, verbose=False)
        except Exception:
            # Do not reflect provider URLs, upstream response bodies or tokens.
            raise ProviderDiagnosticError("MODEL_UNAVAILABLE") from None

    def attest(self) -> None:
        """Non-generation identity check; selection fails closed if unavailable."""
        try:
            response = self._client().predict(api_name="/model_info")
            if not check_identity(response):
                raise ProviderDiagnosticError("MODEL_BAD_RESPONSE")
        except ProviderDiagnosticError:
            raise
        except Exception:
            raise ProviderDiagnosticError("MODEL_UNAVAILABLE") from None

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ProviderDiagnosticError("MODEL_BAD_RESPONSE")
        # The serving Space deliberately rejects longer prompts; do not truncate
        # and silently remove the durable runtime's context or provenance.
        if len(prompt) > MAX_PROMPT_CHARS:
            raise ProviderDiagnosticError("MODEL_BAD_RESPONSE")
        try:
            client = self._client()
            # Check the served weights before sending potentially private text.
            response = client.predict(api_name="/model_info")
            if not check_identity(response):
                raise ProviderDiagnosticError("MODEL_BAD_RESPONSE")
            job = client.submit(prompt, MAX_OUTPUT_TOKENS, api_name="/predict")
            try:
                result = job.result(timeout=self.timeout)
            except FutureTimeout:
                job.cancel()
                raise ProviderDiagnosticError("MODEL_TIMEOUT") from None
            if not isinstance(result, str) or not result.strip() or len(result) > 65536:
                raise ProviderDiagnosticError("MODEL_OUTPUT_EMPTY")
            return result
        except ProviderDiagnosticError:
            raise
        except Exception:
            raise ProviderDiagnosticError("MODEL_UNAVAILABLE") from None
