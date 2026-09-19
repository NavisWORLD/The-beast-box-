"""Frozen real-model conditional-NLL adapters for persistent-substrate v2.

This module is measurement-only.  Model objects remain outside
:class:`~beastbox.persistent_substrate.substrate.PersistentSubstrate`; the
substrate carries state and evidence, never model authority.  Nothing here
trains, fine-tunes, generates from, or adapts a model.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:  # Keep the base package importable without the optional ML extra.
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - exercised by non-ML installations.
    torch = None
    F = None


MODEL_A_ID = "zeref-pinned-active-checkpoint"
EXPECTED_MODEL_A_CHECKPOINT_SHA256 = (
    "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
)
EXPECTED_MODEL_B_ID = "HuggingFaceTB/SmolLM2-135M"
EXPECTED_MODEL_B_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"
EXPECTED_MODEL_B_SNAPSHOT_MANIFEST_SHA256 = (
    "f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc"
)
EXPECTED_MODEL_B_WEIGHT_SHA256 = (
    "80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1"
)


@dataclass(frozen=True)
class RealCandidateScore:
    """One frozen conditional continuation score from a real-model adapter."""

    model_id: str
    prompt_id: str
    candidate: str
    conditional_nll: float
    predicted_units: int
    normalized_nll: float
    unit_kind: str
    input_ids_sha256: str
    tokenizer_id: str
    checkpoint_identity: Mapping[str, Any]


def _require_torch() -> None:
    if torch is None or F is None:
        raise ImportError("real-model persistent-substrate scoring requires the 'ml' extra")


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ids_sha256(ids: list[int]) -> str:
    payload = json.dumps(ids, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parameter_sha256(model: Any) -> str:
    """Hash model parameter names, shapes, dtypes, and exact tensor bytes.

    The hash deliberately excludes optimizer state because v2 has no optimizer.
    Parameters are copied to CPU before hashing so a parameter identity receipt
    can be compared across model transitions without mutating the model.
    """

    _require_torch()
    digest = hashlib.sha256()
    found = False
    for name, parameter in sorted(model.named_parameters(), key=lambda item: item[0]):
        found = True
        tensor = parameter.detach().cpu().contiguous()
        header = {
            "name": str(name),
            "shape": [int(value) for value in tensor.shape],
            "dtype": str(tensor.dtype),
        }
        digest.update(json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(tensor.view(torch.uint8).numpy().tobytes(order="C"))
        digest.update(b"\0")
    if not found:
        raise ValueError("model exposes no parameters to hash")
    return digest.hexdigest()


def _validated_text(prompt_id: str, prompt: str, candidate: str) -> tuple[str, str, str]:
    pid = str(prompt_id)
    prefix = str(prompt)
    continuation = str(candidate)
    if not pid:
        raise ValueError("prompt_id must be non-empty")
    if not prefix:
        raise ValueError("prompt must be non-empty so the first continuation unit is scoreable")
    if not continuation:
        raise ValueError("candidate must be non-empty")
    return pid, prefix, continuation


class ZerefConditionalNLLAdapter:
    """Conditional-NLL measurement adapter for the frozen Zeref character LM."""

    def __init__(
        self,
        *,
        model: Any,
        stoi: Mapping[str, int],
        block: int,
        checkpoint_identity: Mapping[str, Any],
        tokenizer_id: str = "checkpoint-embedded-character-tokenizer",
        model_id: str = MODEL_A_ID,
    ) -> None:
        _require_torch()
        if int(block) <= 0:
            raise ValueError("block must be positive")
        if not stoi:
            raise ValueError("stoi must be non-empty")
        self.model = model.eval()
        self.stoi = {str(key): int(value) for key, value in stoi.items()}
        self.block = int(block)
        self.model_id = str(model_id)
        self.tokenizer_id = str(tokenizer_id)
        self._checkpoint_identity = dict(checkpoint_identity)

    @property
    def checkpoint_identity(self) -> dict[str, Any]:
        return dict(self._checkpoint_identity)

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        architecture_path: str | Path,
        *,
        expected_checkpoint_sha256: str = EXPECTED_MODEL_A_CHECKPOINT_SHA256,
    ) -> "ZerefConditionalNLLAdapter":
        """Load exactly the sealed Zeref checkpoint through its historical loader."""

        _require_torch()
        checkpoint_file = Path(checkpoint_path)
        architecture_file = Path(architecture_path)
        checkpoint_sha = _sha256_file(checkpoint_file)
        if checkpoint_sha != str(expected_checkpoint_sha256).lower():
            raise RuntimeError(
                f"Zeref checkpoint SHA mismatch: {checkpoint_sha} != {expected_checkpoint_sha256}"
            )

        from scripts.run_zeref_dad_son_chat import _load_model

        checkpoint, model = _load_model(checkpoint_file, architecture_file)
        stoi = {str(key): int(value) for key, value in dict(checkpoint["stoi"]).items()}
        block = int(checkpoint["config"]["block"])
        identity = {
            "model_id": MODEL_A_ID,
            "checkpoint_sha256": checkpoint_sha,
            "architecture_sha256": _sha256_file(architecture_file),
            "parameter_sha256": parameter_sha256(model),
            "block": block,
            "vocab_size": int(checkpoint["config"]["vocab"]),
            "tokenizer_kind": "checkpoint-embedded character tokenizer",
            "training_performed": False,
        }
        return cls(
            model=model,
            stoi=stoi,
            block=block,
            checkpoint_identity=identity,
            tokenizer_id="checkpoint-embedded-character-tokenizer",
        )

    def _encode_exact(self, text: str) -> list[int]:
        missing = sorted({character for character in text if character not in self.stoi})
        if missing:
            raise ValueError(f"text contains characters absent from frozen tokenizer: {missing!r}")
        return [self.stoi[character] for character in text]

    def score(self, *, prompt_id: str, prompt: str, candidate: str) -> RealCandidateScore:
        pid, prefix, continuation = _validated_text(prompt_id, prompt, candidate)
        prompt_ids = self._encode_exact(prefix)
        candidate_ids = self._encode_exact(continuation)
        combined_ids = prompt_ids + candidate_ids
        if len(combined_ids) > self.block:
            raise ValueError(
                f"prompt plus candidate length {len(combined_ids)} exceeds frozen block {self.block}"
            )

        input_ids = torch.tensor([combined_ids[:-1]], dtype=torch.long)
        targets = torch.tensor([combined_ids[1:]], dtype=torch.long)
        start = len(prompt_ids) - 1
        stop = start + len(candidate_ids)
        with torch.inference_mode():
            logits, _ = self.model(input_ids)
            losses = F.cross_entropy(
                logits.reshape(-1, logits.shape[-1]),
                targets.reshape(-1),
                reduction="none",
            )
            continuation_losses = losses[start:stop]
            nll = float(continuation_losses.sum().item())

        count = int(len(candidate_ids))
        if continuation_losses.numel() != count or count <= 0:
            raise RuntimeError("Zeref continuation mask did not score every candidate character")
        if not math.isfinite(nll):
            raise RuntimeError("Zeref conditional NLL is not finite")
        return RealCandidateScore(
            model_id=self.model_id,
            prompt_id=pid,
            candidate=continuation,
            conditional_nll=nll,
            predicted_units=count,
            normalized_nll=nll / count,
            unit_kind="character",
            input_ids_sha256=_ids_sha256(combined_ids),
            tokenizer_id=self.tokenizer_id,
            checkpoint_identity=self.checkpoint_identity,
        )


class TransformersConditionalNLLAdapter:
    """Conditional-NLL adapter for a frozen Hugging Face causal language model."""

    def __init__(
        self,
        *,
        model: Any,
        tokenizer: Any,
        model_id: str,
        checkpoint_identity: Mapping[str, Any],
        tokenizer_id: str,
    ) -> None:
        _require_torch()
        self.model = model.eval()
        self.tokenizer = tokenizer
        self.model_id = str(model_id)
        self.tokenizer_id = str(tokenizer_id)
        self._checkpoint_identity = dict(checkpoint_identity)

    @property
    def checkpoint_identity(self) -> dict[str, Any]:
        return dict(self._checkpoint_identity)

    @staticmethod
    def _token_ids(tokenizer: Any, text: str) -> list[int]:
        encoded = tokenizer(text, add_special_tokens=False)
        ids = encoded["input_ids"]
        if ids and isinstance(ids[0], list):
            if len(ids) != 1:
                raise ValueError("batched tokenizer output is not allowed")
            ids = ids[0]
        return [int(value) for value in ids]

    @classmethod
    def from_snapshot(
        cls,
        snapshot_path: str | Path,
        *,
        model_id: str = EXPECTED_MODEL_B_ID,
        revision: str = EXPECTED_MODEL_B_REVISION,
        expected_snapshot_manifest_sha256: str = EXPECTED_MODEL_B_SNAPSHOT_MANIFEST_SHA256,
        expected_weight_sha256: str = EXPECTED_MODEL_B_WEIGHT_SHA256,
    ) -> "TransformersConditionalNLLAdapter":
        """Load the exact sealed reference snapshot, locally and read-only."""

        _require_torch()
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - integration environment only.
            raise ImportError("Transformers adapter requires transformers") from exc

        from scripts.final_reality_bridge_reference import _snapshot_manifest

        snapshot = Path(snapshot_path)
        manifest = _snapshot_manifest(snapshot)
        actual_manifest = str(manifest["snapshot_manifest_sha256"])
        if actual_manifest != str(expected_snapshot_manifest_sha256):
            raise RuntimeError(
                "reference snapshot manifest mismatch: "
                f"{actual_manifest} != {expected_snapshot_manifest_sha256}"
            )
        weight_rows = [
            row for row in manifest["weight_files"] if str(row["path"]) == "model.safetensors"
        ]
        if len(weight_rows) != 1 or str(weight_rows[0]["sha256"]) != str(expected_weight_sha256):
            raise RuntimeError("reference model.safetensors identity mismatch")

        tokenizer = AutoTokenizer.from_pretrained(
            snapshot,
            local_files_only=True,
            use_fast=True,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
        )
        tokenizer_name = f"{tokenizer.__class__.__name__}:{getattr(tokenizer, 'vocab_size', 'unknown')}"
        identity = {
            "model_id": str(model_id),
            "revision": str(revision),
            "snapshot_manifest_sha256": actual_manifest,
            "model_safetensors_sha256": str(weight_rows[0]["sha256"]),
            "parameter_sha256": parameter_sha256(model),
            "tokenizer_class": tokenizer.__class__.__name__,
            "vocab_size": int(getattr(tokenizer, "vocab_size", 0) or 0),
            "training_performed": False,
        }
        return cls(
            model=model,
            tokenizer=tokenizer,
            model_id=model_id,
            checkpoint_identity=identity,
            tokenizer_id=tokenizer_name,
        )

    @classmethod
    def from_huggingface_revision(
        cls,
        *,
        repo_id: str = EXPECTED_MODEL_B_ID,
        revision: str = EXPECTED_MODEL_B_REVISION,
    ) -> "TransformersConditionalNLLAdapter":
        """Download only the immutable revision, then enforce the sealed snapshot hashes."""

        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:  # pragma: no cover - integration environment only.
            raise ImportError("reference download requires huggingface_hub") from exc
        if str(repo_id) != EXPECTED_MODEL_B_ID or str(revision) != EXPECTED_MODEL_B_REVISION:
            raise ValueError("v2 only permits the preregistered reference repo and revision")
        snapshot = snapshot_download(repo_id=repo_id, revision=revision, repo_type="model")
        return cls.from_snapshot(snapshot, model_id=repo_id, revision=revision)

    def score(self, *, prompt_id: str, prompt: str, candidate: str) -> RealCandidateScore:
        pid, prefix, continuation = _validated_text(prompt_id, prompt, candidate)
        prompt_ids = self._token_ids(self.tokenizer, prefix)
        combined_ids = self._token_ids(self.tokenizer, prefix + continuation)
        if not prompt_ids:
            raise ValueError("prompt tokenization produced no tokens")
        if combined_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(
                "tokenization prefix drift: prompt tokens are not a stable prefix of prompt+candidate"
            )
        candidate_ids = combined_ids[len(prompt_ids) :]
        if not candidate_ids:
            raise ValueError("candidate tokenization produced no continuation tokens")

        try:
            device = next(self.model.parameters()).device
        except StopIteration:
            device = torch.device("cpu")
        tensor = torch.tensor([combined_ids], dtype=torch.long, device=device)
        attention = torch.ones_like(tensor)
        start = len(prompt_ids) - 1
        stop = start + len(candidate_ids)
        with torch.inference_mode():
            outputs = self.model(input_ids=tensor, attention_mask=attention, use_cache=False)
            logits = outputs.logits[:, :-1, :]
            targets = tensor[:, 1:]
            losses = F.cross_entropy(
                logits.reshape(-1, logits.shape[-1]),
                targets.reshape(-1),
                reduction="none",
            )
            continuation_losses = losses[start:stop]
            nll = float(continuation_losses.sum().item())

        count = int(len(candidate_ids))
        if continuation_losses.numel() != count or count <= 0:
            raise RuntimeError("reference continuation mask did not score every candidate token")
        if not math.isfinite(nll):
            raise RuntimeError("reference conditional NLL is not finite")
        return RealCandidateScore(
            model_id=self.model_id,
            prompt_id=pid,
            candidate=continuation,
            conditional_nll=nll,
            predicted_units=count,
            normalized_nll=nll / count,
            unit_kind="subword_token",
            input_ids_sha256=_ids_sha256(combined_ids),
            tokenizer_id=self.tokenizer_id,
            checkpoint_identity=self.checkpoint_identity,
        )
