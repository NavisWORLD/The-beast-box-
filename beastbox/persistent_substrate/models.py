"""Frozen, inference-only model adapters for persistent-substrate experiment 001.

The adapters expose provider-neutral conditional-NLL scoring plus deterministic
raw greedy generation for evidentiary receipts. They never alter model weights,
run gradient updates, or inject hidden substrate state into provider inputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import torch
import torch.nn.functional as F

from beastbox.persistent_substrate.protocol import (
    MODEL_A_CHECKPOINT_SHA256,
    MODEL_B_REVISION,
    CandidateScore,
    sha256_file,
    sha256_json,
)

DEFAULT_ZEREF_MODEL_ID = "zeref-pinned-active-checkpoint"
DEFAULT_REFERENCE_MODEL_ID = "HuggingFaceTB/SmolLM2-135M"


def _hash_text(digest: Any, value: str) -> None:
    payload = value.encode("utf-8")
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def parameter_sha256(model: torch.nn.Module) -> str:
    """Hash the complete tensor state of a model without mutating it."""

    digest = hashlib.sha256()
    state = model.state_dict()
    for name in sorted(state):
        tensor = state[name]
        if not torch.is_tensor(tensor):
            raise TypeError(f"non-tensor model state entry: {name}")
        detached = tensor.detach().cpu().contiguous()
        _hash_text(digest, str(name))
        _hash_text(digest, str(detached.dtype))
        _hash_text(digest, sha256_json([int(value) for value in detached.shape]))
        if detached.is_quantized:
            _hash_text(digest, str(detached.qscheme()))
            raw = detached.int_repr().contiguous().reshape(-1).view(torch.uint8)
        else:
            raw = detached.reshape(-1).view(torch.uint8)
        digest.update(raw.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _device_for(model: torch.nn.Module) -> torch.device:
    for tensor in model.parameters():
        return tensor.device
    for tensor in model.buffers():
        return tensor.device
    return torch.device("cpu")


def _validate_text(prompt: str, continuation: str) -> tuple[str, str]:
    prompt_text = str(prompt)
    continuation_text = str(continuation)
    if not prompt_text:
        raise ValueError("prompt must be non-empty for causal continuation scoring")
    if not continuation_text:
        raise ValueError("continuation must be non-empty")
    return prompt_text, continuation_text


def _validate_generation(prompt: str, max_new_tokens: int) -> tuple[str, int]:
    prompt_text = str(prompt)
    budget = int(max_new_tokens)
    if not prompt_text:
        raise ValueError("prompt must be non-empty for causal generation")
    if budget <= 0:
        raise ValueError("max_new_tokens must be positive")
    return prompt_text, budget


def _conditional_score(
    *,
    model: torch.nn.Module,
    input_ids: list[int],
    prompt_units: int,
    candidate: str,
    unit_kind: str,
    transformers_style: bool,
) -> CandidateScore:
    if prompt_units <= 0:
        raise ValueError("prompt must contain at least one model unit")
    predicted_units = len(input_ids) - int(prompt_units)
    if predicted_units <= 0:
        raise ValueError("continuation must contain at least one model unit")

    device = _device_for(model)
    tensor = torch.tensor([input_ids], dtype=torch.long, device=device)
    with torch.inference_mode():
        if transformers_style:
            output = model(input_ids=tensor)
            logits = output.logits
        else:
            output = model(tensor)
            logits = output[0] if isinstance(output, (tuple, list)) else output
        if logits.ndim != 3 or logits.shape[0] != 1 or logits.shape[1] != tensor.shape[1]:
            raise RuntimeError("model returned incompatible causal logits")
        start = int(prompt_units) - 1
        stop = len(input_ids) - 1
        suffix_logits = logits[:, start:stop, :]
        suffix_targets = tensor[:, int(prompt_units) :]
        if suffix_logits.shape[1] != suffix_targets.shape[1] or suffix_targets.shape[1] != predicted_units:
            raise RuntimeError("continuation scoring window is misaligned")
        loss = F.cross_entropy(
            suffix_logits.reshape(-1, suffix_logits.shape[-1]),
            suffix_targets.reshape(-1),
            reduction="sum",
        )

    nll_nats = float(loss.item())
    return CandidateScore(
        candidate=candidate,
        nll_nats=nll_nats,
        predicted_units=predicted_units,
        normalized_nll=nll_nats / predicted_units,
        unit_kind=unit_kind,
        input_ids_sha256=sha256_json([int(value) for value in input_ids]),
    )


class _FrozenAdapterLifecycle:
    model: torch.nn.Module
    model_id: str
    checkpoint_identity: Mapping[str, Any]
    _initial_parameter_sha256: str
    _identity: Mapping[str, Any]

    def _freeze_identity(self) -> None:
        self._initial_parameter_sha256 = parameter_sha256(self.model)
        identity = dict(self.checkpoint_identity)
        identity["model_id"] = self.model_id
        frozen_parameter_sha = str(identity.get("parameter_sha256") or self._initial_parameter_sha256)
        if frozen_parameter_sha != self._initial_parameter_sha256:
            raise RuntimeError(
                "model parameter SHA does not match checkpoint identity: "
                f"{self._initial_parameter_sha256} != {frozen_parameter_sha}"
            )
        identity["parameter_sha256"] = self._initial_parameter_sha256
        self._identity = MappingProxyType(identity)

    @property
    def identity(self) -> Mapping[str, Any]:
        return self._identity

    def score_candidates(self, wire: str, candidates: Sequence[str]) -> tuple[CandidateScore, ...]:
        candidate_list = tuple(str(value) for value in candidates)
        if not candidate_list:
            raise ValueError("candidates must be non-empty")
        if len(set(candidate_list)) != len(candidate_list):
            raise ValueError("candidates must be unique")
        return tuple(self.score(prompt=str(wire), continuation=candidate) for candidate in candidate_list)

    def close(self) -> dict[str, Any]:
        after = parameter_sha256(self.model)
        drift = after != self._initial_parameter_sha256
        if drift:
            raise RuntimeError(
                "model parameter drift detected: "
                f"{after} != {self._initial_parameter_sha256}"
            )
        return {
            "model_id": self.model_id,
            "parameter_sha256_before": self._initial_parameter_sha256,
            "parameter_sha256_after": after,
            "parameter_drift": False,
        }


class ZerefNLLAdapter(_FrozenAdapterLifecycle):
    """Conditional-NLL adapter for the frozen character-level Zeref checkpoint."""

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        stoi: Mapping[str, int],
        checkpoint_identity: Mapping[str, Any],
        model_id: str = DEFAULT_ZEREF_MODEL_ID,
        block_size: int | None = None,
    ) -> None:
        self.model = model.eval()
        self.stoi = MappingProxyType({str(key): int(value) for key, value in stoi.items()})
        self.checkpoint_identity = MappingProxyType(dict(checkpoint_identity))
        self.model_id = str(model_id)
        self.block_size = None if block_size is None else int(block_size)
        if not self.stoi:
            raise ValueError("frozen tokenizer cannot be empty")
        if self.block_size is not None and self.block_size <= 0:
            raise ValueError("block_size must be positive")
        self.itos = MappingProxyType({value: key for key, value in self.stoi.items()})
        if len(self.itos) != len(self.stoi):
            raise ValueError("frozen tokenizer ids must be unique")
        self._freeze_identity()

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        architecture_path: str | Path,
        *,
        expected_checkpoint_sha256: str = MODEL_A_CHECKPOINT_SHA256,
        expected_architecture_sha256: str | None = None,
        model_id: str = DEFAULT_ZEREF_MODEL_ID,
    ) -> "ZerefNLLAdapter":
        checkpoint_file = Path(checkpoint_path)
        architecture_file = Path(architecture_path)
        checkpoint_sha = sha256_file(checkpoint_file)
        if checkpoint_sha != str(expected_checkpoint_sha256):
            raise RuntimeError(
                f"Zeref checkpoint SHA mismatch: {checkpoint_sha} != {expected_checkpoint_sha256}"
            )
        architecture_sha = sha256_file(architecture_file)
        if expected_architecture_sha256 is not None and architecture_sha != str(expected_architecture_sha256):
            raise RuntimeError(
                f"Zeref architecture SHA mismatch: {architecture_sha} != {expected_architecture_sha256}"
            )

        from scripts.run_zeref_dad_son_chat import _load_model

        checkpoint, model = _load_model(checkpoint_file, architecture_file)
        stoi = {str(key): int(value) for key, value in dict(checkpoint["stoi"]).items()}
        block_size = int(checkpoint["config"]["block"])
        identity = {
            "model_id": str(model_id),
            "checkpoint_sha256": checkpoint_sha,
            "architecture_sha256": architecture_sha,
            "parameter_sha256": parameter_sha256(model),
            "checkpoint_schema": str(checkpoint.get("schema") or ""),
            "checkpoint_stage": str(checkpoint.get("stage") or ""),
            "block_size": block_size,
            "vocab_size": len(stoi),
        }
        return cls(
            model=model,
            stoi=stoi,
            checkpoint_identity=identity,
            model_id=model_id,
            block_size=block_size,
        )

    def _encode(self, text: str) -> list[int]:
        missing = sorted({character for character in text if character not in self.stoi})
        if missing:
            raise ValueError(f"text contains characters absent from frozen tokenizer: {missing!r}")
        return [int(self.stoi[character]) for character in text]

    def score(self, *, prompt: str, continuation: str) -> CandidateScore:
        prompt_text, continuation_text = _validate_text(prompt, continuation)
        prompt_ids = self._encode(prompt_text)
        continuation_ids = self._encode(continuation_text)
        input_ids = prompt_ids + continuation_ids
        if self.block_size is not None and len(input_ids) > self.block_size:
            raise ValueError(
                f"prompt plus continuation uses {len(input_ids)} characters; frozen block is {self.block_size}"
            )
        return _conditional_score(
            model=self.model,
            input_ids=input_ids,
            prompt_units=len(prompt_ids),
            candidate=continuation_text,
            unit_kind="character",
            transformers_style=False,
        )

    def generate(self, wire: str, *, max_new_tokens: int) -> dict[str, Any]:
        prompt_text, budget = _validate_generation(wire, max_new_tokens)
        input_ids = self._encode(prompt_text)
        if self.block_size is not None and len(input_ids) + budget > self.block_size:
            raise ValueError(
                f"prompt plus generation budget uses {len(input_ids) + budget} characters; "
                f"frozen block is {self.block_size}"
            )
        generated: list[int] = []
        device = _device_for(self.model)
        with torch.inference_mode():
            for _ in range(budget):
                tensor = torch.tensor([input_ids + generated], dtype=torch.long, device=device)
                output = self.model(tensor)
                logits = output[0] if isinstance(output, (tuple, list)) else output
                if logits.ndim != 3 or logits.shape[0] != 1:
                    raise RuntimeError("model returned incompatible causal logits")
                generated.append(int(torch.argmax(logits[0, -1, :]).item()))
        try:
            text = "".join(self.itos[value] for value in generated)
        except KeyError as exc:
            raise RuntimeError(f"generated tokenizer id is absent from frozen tokenizer: {exc.args[0]}") from exc
        return {
            "schema": "persistent-substrate-generation-v1",
            "model_id": self.model_id,
            "max_new_tokens": budget,
            "generated_units": len(generated),
            "unit_kind": "character",
            "text": text,
            "generated_ids": generated,
            "generated_ids_sha256": sha256_json(generated),
            "prompt_ids_sha256": sha256_json(input_ids),
            "parameter_sha256": self._initial_parameter_sha256,
        }


class TransformersNLLAdapter(_FrozenAdapterLifecycle):
    """Conditional-NLL adapter for the pinned external causal language model."""

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        tokenizer: Any,
        checkpoint_identity: Mapping[str, Any],
        model_id: str = DEFAULT_REFERENCE_MODEL_ID,
    ) -> None:
        self.model = model.eval()
        self.tokenizer = tokenizer
        self.checkpoint_identity = MappingProxyType(dict(checkpoint_identity))
        self.model_id = str(model_id)
        self._freeze_identity()

    @classmethod
    def from_pretrained(
        cls,
        *,
        model_id: str = DEFAULT_REFERENCE_MODEL_ID,
        revision: str = MODEL_B_REVISION,
        local_files_only: bool = False,
    ) -> "TransformersNLLAdapter":
        if str(revision) != MODEL_B_REVISION:
            raise ValueError(f"reference revision must remain frozen at {MODEL_B_REVISION}")
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Transformers adapter requires the ml provider dependencies") from exc

        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=bool(local_files_only),
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=bool(local_files_only),
            trust_remote_code=False,
        )
        identity = {
            "model_id": str(model_id),
            "revision": str(revision),
            "parameter_sha256": parameter_sha256(model),
            "tokenizer_id": str(getattr(tokenizer, "name_or_path", model_id)),
            "trust_remote_code": False,
        }
        return cls(
            model=model,
            tokenizer=tokenizer,
            checkpoint_identity=identity,
            model_id=model_id,
        )

    def _encode(self, text: str) -> list[int]:
        encoded = self.tokenizer.encode(text, add_special_tokens=False)
        return [int(value) for value in encoded]

    def score(self, *, prompt: str, continuation: str) -> CandidateScore:
        prompt_text, continuation_text = _validate_text(prompt, continuation)
        prompt_ids = self._encode(prompt_text)
        full_ids = self._encode(prompt_text + continuation_text)
        if not prompt_ids:
            raise ValueError("prompt produced no tokenizer units")
        if full_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError("tokenizer changed the frozen suffix boundary between prompt and continuation")
        if len(full_ids) <= len(prompt_ids):
            raise ValueError("continuation produced no tokenizer units")
        return _conditional_score(
            model=self.model,
            input_ids=full_ids,
            prompt_units=len(prompt_ids),
            candidate=continuation_text,
            unit_kind="token",
            transformers_style=True,
        )

    def generate(self, wire: str, *, max_new_tokens: int) -> dict[str, Any]:
        prompt_text, budget = _validate_generation(wire, max_new_tokens)
        input_ids = self._encode(prompt_text)
        if not input_ids:
            raise ValueError("prompt produced no tokenizer units")
        generated: list[int] = []
        device = _device_for(self.model)
        with torch.inference_mode():
            for _ in range(budget):
                tensor = torch.tensor([input_ids + generated], dtype=torch.long, device=device)
                output = self.model(input_ids=tensor)
                logits = output.logits
                if logits.ndim != 3 or logits.shape[0] != 1:
                    raise RuntimeError("model returned incompatible causal logits")
                generated.append(int(torch.argmax(logits[0, -1, :]).item()))
        try:
            text = self.tokenizer.decode(generated, skip_special_tokens=False)
        except TypeError:
            text = self.tokenizer.decode(generated)
        return {
            "schema": "persistent-substrate-generation-v1",
            "model_id": self.model_id,
            "max_new_tokens": budget,
            "generated_units": len(generated),
            "unit_kind": "token",
            "text": str(text),
            "generated_ids": generated,
            "generated_ids_sha256": sha256_json(generated),
            "prompt_ids_sha256": sha256_json(input_ids),
            "parameter_sha256": self._initial_parameter_sha256,
        }
