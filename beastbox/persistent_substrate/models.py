"""Inference-only conditional-NLL adapters for the real-model swap experiment."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping

import torch
import torch.nn.functional as F

from .protocol import CandidateScore, canonical_json_bytes, sha256_file


def parameter_sha256(model: torch.nn.Module) -> str:
    """Hash model parameters canonically without mutating or serializing the model."""
    digest = hashlib.sha256()
    for name, parameter in sorted(model.named_parameters(), key=lambda item: item[0]):
        value = parameter.detach().cpu().contiguous()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(value.dtype).encode("ascii") + b"\0")
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii") + b"\0")
        digest.update(value.view(torch.uint8).numpy().tobytes(order="C"))
    return digest.hexdigest()


def assert_frozen_model(model: torch.nn.Module) -> None:
    if model.training:
        raise RuntimeError("model must be in eval mode")
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError("model parameters must have requires_grad=False")


def _freeze(model: torch.nn.Module) -> torch.nn.Module:
    model.eval()
    model.requires_grad_(False)
    assert_frozen_model(model)
    return model


def _logits(output: Any) -> torch.Tensor:
    if isinstance(output, torch.Tensor):
        return output
    if hasattr(output, "logits"):
        return output.logits
    if isinstance(output, (tuple, list)) and output and isinstance(output[0], torch.Tensor):
        return output[0]
    raise RuntimeError("causal model output does not expose logits")


def _score_receipt(
    *,
    model_id: str,
    candidate: str,
    unit_kind: str,
    prompt_bytes: bytes,
    input_ids: list[int],
    total_nll: float,
    predicted_units: int,
    checkpoint_identity: Mapping[str, Any],
) -> CandidateScore:
    if predicted_units <= 0 or not math.isfinite(total_nll):
        raise RuntimeError("conditional NLL must contain finite continuation targets")
    normalized = total_nll / predicted_units
    ids_sha = hashlib.sha256(canonical_json_bytes(input_ids)).hexdigest()
    output_sha = hashlib.sha256(
        canonical_json_bytes(
            {
                "candidate": candidate,
                "nll_nats": total_nll,
                "normalized_nll": normalized,
                "predicted_units": predicted_units,
                "unit_kind": unit_kind,
            }
        )
    ).hexdigest()
    return CandidateScore(
        model_id=model_id,
        candidate=candidate,
        nll_nats=float(total_nll),
        normalized_nll=float(normalized),
        predicted_units=int(predicted_units),
        unit_kind=unit_kind,
        input_sha256=hashlib.sha256(prompt_bytes).hexdigest(),
        input_ids_sha256=ids_sha,
        output_sha256=output_sha,
        checkpoint_identity=dict(checkpoint_identity),
    )


class ZerefNLLAdapter:
    """Conditional character-NLL scorer for the frozen Cosmos-Spark-CST checkpoint."""

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        stoi: Mapping[str, int],
        model_id: str,
        checkpoint_identity: Mapping[str, Any],
        block_size: int,
    ) -> None:
        self.model = _freeze(model)
        self.stoi = {str(key): int(value) for key, value in stoi.items()}
        self.model_id = str(model_id)
        self.checkpoint_identity = dict(checkpoint_identity)
        self.block_size = int(block_size)
        if self.block_size < 2:
            raise ValueError("block_size must be at least 2")
        self._parameter_sha256 = parameter_sha256(self.model)

    @classmethod
    def from_checkpoint(
        cls,
        *,
        checkpoint_path: str | Path,
        architecture_path: str | Path,
        expected_checkpoint_sha256: str,
        expected_architecture_sha256: str,
        model_id: str,
        checkpoint_identity: Mapping[str, Any],
    ) -> "ZerefNLLAdapter":
        checkpoint_path = Path(checkpoint_path)
        architecture_path = Path(architecture_path)
        if sha256_file(checkpoint_path) != expected_checkpoint_sha256.lower():
            raise RuntimeError("Zeref checkpoint SHA-256 mismatch")
        if sha256_file(architecture_path) != expected_architecture_sha256.lower():
            raise RuntimeError("Zeref architecture SHA-256 mismatch")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        if not isinstance(checkpoint, dict) or checkpoint.get("arch") != "Cosmos-Spark-CST-D001":
            raise RuntimeError("Zeref checkpoint architecture identity mismatch")
        spec = importlib.util.spec_from_file_location("zeref_real_swap_arch", architecture_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load frozen Zeref architecture")
        architecture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(architecture)
        config = dict(checkpoint.get("config") or {})
        expected_config = {
            "block": architecture.BLOCK,
            "n_layer": architecture.N_LAYER,
            "n_head": architecture.N_HEAD,
            "n_embd": architecture.N_EMBD,
            "d54": architecture.D54,
        }
        for key, value in expected_config.items():
            if int(config.get(key, -1)) != int(value):
                raise RuntimeError(f"Zeref architecture mismatch for {key}")
        model = architecture.SparkCST(int(config["vocab"]), True)
        state = dict(checkpoint.get("model") or {})
        head_bias = state.pop("head.bias", None)
        if head_bias is not None and int(torch.count_nonzero(head_bias).item()) != 0:
            raise RuntimeError("nonzero Zeref head.bias is not represented by frozen architecture")
        missing, unexpected = model.load_state_dict(state, strict=False)
        if set(missing) != {"mask"} or unexpected:
            raise RuntimeError(f"undocumented Zeref state mismatch: missing={missing} unexpected={unexpected}")
        identity = dict(checkpoint_identity)
        identity.update(
            {
                "checkpoint_sha256": expected_checkpoint_sha256.lower(),
                "architecture_sha256": expected_architecture_sha256.lower(),
                "parameter_sha256": parameter_sha256(model),
            }
        )
        return cls(
            model=model,
            stoi=checkpoint["stoi"],
            model_id=model_id,
            checkpoint_identity=identity,
            block_size=int(config["block"]),
        )

    def _encode(self, text: str, *, label: str) -> list[int]:
        missing = sorted({character for character in text if character not in self.stoi})
        if missing:
            preview = "".join(missing[:8])
            raise ValueError(f"unsupported {label} character(s): {preview!r}")
        return [self.stoi[character] for character in text]

    def score(self, prompt: str, continuation: str) -> CandidateScore:
        assert_frozen_model(self.model)
        before = parameter_sha256(self.model)
        if before != self._parameter_sha256:
            raise RuntimeError("Zeref parameters changed before scoring")
        prompt_ids = self._encode(str(prompt), label="prompt")
        candidate_ids = self._encode(str(continuation), label="candidate")
        if not candidate_ids:
            raise ValueError("candidate continuation must be non-empty")
        if len(candidate_ids) >= self.block_size:
            raise ValueError("candidate continuation exceeds Zeref block size")
        # Preserve the entire continuation and as much of the prompt suffix as fits.
        max_prompt = self.block_size + 1 - len(candidate_ids)
        if max_prompt < 1:
            raise ValueError("Zeref scoring requires at least one prompt character")
        kept_prompt = prompt_ids[-max_prompt:]
        if not kept_prompt:
            raise ValueError("Zeref scoring prompt must be non-empty")
        combined = kept_prompt + candidate_ids
        x_ids = combined[:-1]
        target_ids = combined[1:]
        continuation_start = len(kept_prompt) - 1
        device = next(self.model.parameters()).device
        x = torch.tensor([x_ids], dtype=torch.long, device=device)
        y = torch.tensor(target_ids[continuation_start:], dtype=torch.long, device=device)
        with torch.inference_mode():
            logits = _logits(self.model(x))[0, continuation_start:, :]
            total_nll = float(F.cross_entropy(logits, y, reduction="sum").detach().cpu())
        after = parameter_sha256(self.model)
        if after != before:
            raise RuntimeError("Zeref parameters changed during scoring")
        return _score_receipt(
            model_id=self.model_id,
            candidate=str(continuation),
            unit_kind="character",
            prompt_bytes=str(prompt).encode("utf-8"),
            input_ids=x_ids,
            total_nll=total_nll,
            predicted_units=len(candidate_ids),
            checkpoint_identity=self.checkpoint_identity,
        )


class TransformersNLLAdapter:
    """Conditional token-NLL scorer for a frozen local Transformers causal LM."""

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        tokenizer: Any,
        model_id: str,
        checkpoint_identity: Mapping[str, Any],
    ) -> None:
        self.model = _freeze(model)
        self.tokenizer = tokenizer
        self.model_id = str(model_id)
        self.checkpoint_identity = dict(checkpoint_identity)
        self._parameter_sha256 = parameter_sha256(self.model)

    @classmethod
    def from_local_snapshot(
        cls,
        *,
        snapshot_path: str | Path,
        model_id: str,
        checkpoint_identity: Mapping[str, Any],
    ) -> "TransformersNLLAdapter":
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("transformers is required for the real Model B adapter") from exc
        snapshot = str(Path(snapshot_path).resolve())
        tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True)
        return cls(
            model=model,
            tokenizer=tokenizer,
            model_id=model_id,
            checkpoint_identity=checkpoint_identity,
        )

    def score(self, prompt: str, continuation: str) -> CandidateScore:
        assert_frozen_model(self.model)
        before = parameter_sha256(self.model)
        if before != self._parameter_sha256:
            raise RuntimeError("Transformers parameters changed before scoring")
        prompt_ids = list(self.tokenizer.encode(str(prompt), add_special_tokens=True))
        candidate_ids = list(self.tokenizer.encode(str(continuation), add_special_tokens=False))
        if not prompt_ids:
            raise ValueError("tokenizer produced an empty prompt")
        if not candidate_ids:
            raise ValueError("tokenizer produced an empty continuation")
        combined = prompt_ids + candidate_ids
        x_ids = combined[:-1]
        continuation_start = len(prompt_ids) - 1
        device = next(self.model.parameters()).device
        x = torch.tensor([x_ids], dtype=torch.long, device=device)
        y = torch.tensor(candidate_ids, dtype=torch.long, device=device)
        with torch.inference_mode():
            logits = _logits(self.model(x))[0, continuation_start:, :]
            total_nll = float(F.cross_entropy(logits, y, reduction="sum").detach().cpu())
        after = parameter_sha256(self.model)
        if after != before:
            raise RuntimeError("Transformers parameters changed during scoring")
        return _score_receipt(
            model_id=self.model_id,
            candidate=str(continuation),
            unit_kind="token",
            prompt_bytes=str(prompt).encode("utf-8"),
            input_ids=x_ids,
            total_nll=total_nll,
            predicted_units=len(candidate_ids),
            checkpoint_identity=self.checkpoint_identity,
        )
