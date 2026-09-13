"""Audited SparkCST -> PHOS architecture migration for Zeref descendants.

The historical SparkCST checkpoint and architecture remain immutable. This
module constructs a new PHOSReferenceLM and accounts for every parent parameter
as either an exact copy or an explicitly versioned transform. The resulting
model is a weight-derived descendant, not an assertion of parameter or identity
equivalence with the historical parent.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping

try:
    import torch
    import torch.nn as nn
except ImportError as exc:  # pragma: no cover - optional ML installation
    raise RuntimeError("Install ML extra: pip install 'cosmos-beast-box[ml]'") from exc

from beastbox.hashutil import sha256_obj
from beastbox.models.phos_reference import PHOSReferenceLM

MIGRATION_SCHEMA = "zeref-phos-migration-receipt-v1"
MIGRATION_TRANSFORM = "sparkcst-to-phos-v1"
STATE_FOLD_TRANSFORM = "modulo-fold-mean-54-to-12-v1"
GATE_TRANSFORM = "clamp-0.01-0.99-then-logit-v1"


def _hash_text(digest: Any, value: str) -> None:
    payload = value.encode("utf-8")
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def parameter_sha256(model: nn.Module) -> str:
    """Hash exact named model parameters without mutating the model."""

    digest = hashlib.sha256()
    found = False
    for name, parameter in sorted(model.named_parameters(), key=lambda item: item[0]):
        found = True
        tensor = parameter.detach().cpu().contiguous()
        _hash_text(digest, str(name))
        _hash_text(digest, str(tensor.dtype))
        _hash_text(digest, sha256_obj([int(value) for value in tensor.shape]))
        digest.update(tensor.reshape(-1).view(torch.uint8).numpy().tobytes(order="C"))
    if not found:
        raise ValueError("model exposes no parameters to hash")
    return digest.hexdigest()


def _require_sha256(value: str, *, name: str) -> str:
    text = str(value).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be a lowercase-compatible SHA-256 hex digest")
    return text


def _config_int(config: Mapping[str, Any], name: str) -> int:
    value = config.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"parent config {name} must be an integer")
    if value <= 0:
        raise ValueError(f"parent config {name} must be positive")
    return value


def _validate_tokenizer(tokenizer: Mapping[str, int], *, vocab_size: int) -> dict[str, int]:
    normalized = {str(character): int(index) for character, index in tokenizer.items()}
    if len(normalized) != vocab_size:
        raise ValueError("tokenizer size does not match parent vocab")
    ids = list(normalized.values())
    if len(set(ids)) != len(ids) or set(ids) != set(range(vocab_size)):
        raise ValueError("tokenizer ids must be unique and contiguous from zero")
    return normalized


def _expected_parent_parameter_names(n_layers: int) -> set[str]:
    names = {
        "tok.weight",
        "pos.weight",
        "lnf.weight",
        "lnf.bias",
        "head.weight",
    }
    for index in range(n_layers):
        prefix = f"blocks.{index}."
        names.update(
            {
                f"{prefix}ln1.weight",
                f"{prefix}ln1.bias",
                f"{prefix}attn.qkv.weight",
                f"{prefix}attn.qkv.bias",
                f"{prefix}attn.proj.weight",
                f"{prefix}attn.proj.bias",
                f"{prefix}attn.w54.weight",
                f"{prefix}attn.log_sigma",
                f"{prefix}attn.gate",
                f"{prefix}ln2.weight",
                f"{prefix}ln2.bias",
                f"{prefix}mlp.0.weight",
                f"{prefix}mlp.0.bias",
                f"{prefix}mlp.2.weight",
                f"{prefix}mlp.2.bias",
            }
        )
    return names


def _copy_exact(
    *,
    source_name: str,
    destination_name: str,
    source: Mapping[str, nn.Parameter],
    destination: Mapping[str, nn.Parameter],
    copied: list[dict[str, str]],
) -> None:
    source_tensor = source[source_name]
    destination_tensor = destination[destination_name]
    if tuple(source_tensor.shape) != tuple(destination_tensor.shape):
        raise RuntimeError(
            f"shape mismatch for {source_name} -> {destination_name}: "
            f"{tuple(source_tensor.shape)} != {tuple(destination_tensor.shape)}"
        )
    with torch.no_grad():
        destination_tensor.copy_(source_tensor)
    copied.append(
        {
            "source": source_name,
            "destination": destination_name,
            "transform": "exact-copy",
        }
    )


def _fold_54_to_12(weight: torch.Tensor) -> torch.Tensor:
    if weight.ndim != 2 or weight.shape[0] != 54:
        raise RuntimeError("SparkCST w54 weight must have shape [54, d_model]")
    return torch.stack([weight[index::12].mean(dim=0) for index in range(12)], dim=0)


def migrate_sparkcst_to_phos(
    parent_model: nn.Module,
    *,
    parent_config: Mapping[str, Any],
    tokenizer: Mapping[str, int],
    parent_checkpoint_sha256: str,
    parent_architecture_sha256: str,
    expected_parent_parameter_sha256: str | None = None,
) -> tuple[PHOSReferenceLM, dict[str, Any]]:
    """Construct a receipt-backed PHOS descendant from a frozen SparkCST model."""

    checkpoint_sha = _require_sha256(parent_checkpoint_sha256, name="parent checkpoint SHA-256")
    architecture_sha = _require_sha256(parent_architecture_sha256, name="parent architecture SHA-256")
    vocab_size = _config_int(parent_config, "vocab")
    block = _config_int(parent_config, "block")
    n_layers = _config_int(parent_config, "n_layer")
    n_heads = _config_int(parent_config, "n_head")
    d_model = _config_int(parent_config, "n_embd")
    d54 = _config_int(parent_config, "d54")
    if d54 != 54:
        raise ValueError("sparkcst-to-phos-v1 requires parent d54 == 54")
    if d_model % n_heads:
        raise ValueError("parent n_embd must be divisible by n_head")
    normalized_tokenizer = _validate_tokenizer(tokenizer, vocab_size=vocab_size)

    parent_parameters = dict(parent_model.named_parameters())
    expected_parent_names = _expected_parent_parameter_names(n_layers)
    extras = sorted(set(parent_parameters) - expected_parent_names)
    if extras:
        raise RuntimeError(f"unmapped parent parameter(s): {extras}")
    missing = sorted(expected_parent_names - set(parent_parameters))
    if missing:
        raise RuntimeError(f"missing parent parameter(s): {missing}")

    parent_parameter_sha = parameter_sha256(parent_model)
    if expected_parent_parameter_sha256 is not None:
        expected_sha = _require_sha256(
            expected_parent_parameter_sha256,
            name="expected parent parameter SHA-256",
        )
        if parent_parameter_sha != expected_sha:
            raise RuntimeError(
                "parent parameter SHA-256 mismatch: "
                f"{parent_parameter_sha} != {expected_sha}"
            )

    model = PHOSReferenceLM(
        vocab_size=vocab_size,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        max_seq_len=block,
        enable_external_state=True,
        tie_embeddings=False,
    )
    destination_parameters = dict(model.named_parameters())
    copied: list[dict[str, str]] = []
    transformed: list[dict[str, Any]] = []
    new_tensors: list[dict[str, str]] = []

    _copy_exact(
        source_name="tok.weight",
        destination_name="token.weight",
        source=parent_parameters,
        destination=destination_parameters,
        copied=copied,
    )
    _copy_exact(
        source_name="pos.weight",
        destination_name="pos.weight",
        source=parent_parameters,
        destination=destination_parameters,
        copied=copied,
    )
    _copy_exact(
        source_name="lnf.weight",
        destination_name="norm.weight",
        source=parent_parameters,
        destination=destination_parameters,
        copied=copied,
    )
    _copy_exact(
        source_name="lnf.bias",
        destination_name="norm.bias",
        source=parent_parameters,
        destination=destination_parameters,
        copied=copied,
    )
    _copy_exact(
        source_name="head.weight",
        destination_name="head.weight",
        source=parent_parameters,
        destination=destination_parameters,
        copied=copied,
    )

    for index in range(n_layers):
        source_prefix = f"blocks.{index}."
        exact_pairs = (
            ("ln1.weight", "n1.weight"),
            ("ln1.bias", "n1.bias"),
            ("attn.qkv.weight", "attn.qkv.weight"),
            ("attn.qkv.bias", "attn.qkv.bias"),
            ("attn.proj.weight", "attn.out.weight"),
            ("attn.proj.bias", "attn.out.bias"),
            ("attn.log_sigma", "attn.log_sigma"),
            ("ln2.weight", "n2.weight"),
            ("ln2.bias", "n2.bias"),
            ("mlp.0.weight", "mlp.0.weight"),
            ("mlp.0.bias", "mlp.0.bias"),
            ("mlp.2.weight", "mlp.2.weight"),
            ("mlp.2.bias", "mlp.2.bias"),
        )
        for source_suffix, destination_suffix in exact_pairs:
            _copy_exact(
                source_name=f"{source_prefix}{source_suffix}",
                destination_name=f"{source_prefix}{destination_suffix}",
                source=parent_parameters,
                destination=destination_parameters,
                copied=copied,
            )

        w54_name = f"{source_prefix}attn.w54.weight"
        state_name = f"{source_prefix}attn.state_proj.weight"
        folded = _fold_54_to_12(parent_parameters[w54_name].detach())
        destination_state = destination_parameters[state_name]
        if tuple(folded.shape) != tuple(destination_state.shape):
            raise RuntimeError(
                f"shape mismatch after 54D fold for {state_name}: "
                f"{tuple(folded.shape)} != {tuple(destination_state.shape)}"
            )
        with torch.no_grad():
            destination_state.copy_(folded)
            destination_parameters[f"{source_prefix}attn.state_proj.bias"].zero_()
        transformed.append(
            {
                "source": w54_name,
                "destination": state_name,
                "transform": STATE_FOLD_TRANSFORM,
            }
        )
        new_tensors.append(
            {
                "destination": f"{source_prefix}attn.state_proj.bias",
                "initialization": "zeros-12",
            }
        )

        gate_name = f"{source_prefix}attn.gate"
        destination_gate_name = f"{source_prefix}attn.gate_logit"
        gate_tensor = parent_parameters[gate_name]
        if gate_tensor.numel() != 1:
            raise RuntimeError(f"SparkCST gate must contain one value: {gate_name}")
        raw_gate = float(gate_tensor.detach().reshape(-1)[0].item())
        if not math.isfinite(raw_gate):
            raise RuntimeError(f"SparkCST gate must be finite: {gate_name}")
        bounded_gate = min(max(raw_gate, 0.01), 0.99)
        gate_logit = math.log(bounded_gate / (1.0 - bounded_gate))
        with torch.no_grad():
            destination_parameters[destination_gate_name].fill_(gate_logit)
        transformed.append(
            {
                "source": gate_name,
                "destination": destination_gate_name,
                "transform": GATE_TRANSFORM,
                "bounded_gate": bounded_gate,
            }
        )

    with torch.no_grad():
        destination_parameters["q_to_state.weight"].copy_(torch.eye(12))
        destination_parameters["q_to_state.bias"].zero_()
    new_tensors.extend(
        [
            {"destination": "q_to_state.weight", "initialization": "identity-12x12"},
            {"destination": "q_to_state.bias", "initialization": "zeros-12"},
        ]
    )

    accounted_sources = [row["source"] for row in copied] + [
        str(row["source"]) for row in transformed if row.get("source") is not None
    ]
    if len(accounted_sources) != len(set(accounted_sources)) or set(accounted_sources) != set(parent_parameters):
        raise RuntimeError("parent parameter accounting is incomplete or duplicated")

    accounted_destinations = {row["destination"] for row in copied}
    accounted_destinations.update(str(row["destination"]) for row in transformed)
    accounted_destinations.update(row["destination"] for row in new_tensors)
    destination_names = set(destination_parameters)
    if accounted_destinations != destination_names:
        missing_destination = sorted(destination_names - accounted_destinations)
        extra_destination = sorted(accounted_destinations - destination_names)
        raise RuntimeError(
            "destination parameter accounting mismatch: "
            f"missing={missing_destination} extra={extra_destination}"
        )

    destination_parameter_sha = parameter_sha256(model)
    receipt: dict[str, Any] = {
        "schema": MIGRATION_SCHEMA,
        "transform": MIGRATION_TRANSFORM,
        "parent": {
            "checkpoint_sha256": checkpoint_sha,
            "architecture_sha256": architecture_sha,
            "parameter_sha256": parent_parameter_sha,
        },
        "parent_config": {
            "vocab": vocab_size,
            "block": block,
            "n_layer": n_layers,
            "n_head": n_heads,
            "n_embd": d_model,
            "d54": d54,
        },
        "tokenizer": {
            "kind": "checkpoint-embedded-character-tokenizer",
            "vocab_size": vocab_size,
            "sha256": sha256_obj(normalized_tokenizer),
        },
        "destination": {
            "architecture": "PHOSReferenceLM",
            "state_dim": 12,
            "external_state_enabled": True,
            "embeddings_tied": False,
        },
        "copied": copied,
        "transformed": transformed,
        "new_tensors": new_tensors,
        "destination_parameter_sha256": destination_parameter_sha,
        "claim_boundary": {
            "architecture_migration_not_parameter_equivalence": True,
            "no_consciousness_claim": True,
            "no_quantum_advantage_claim": True,
            "authority_not_transferred": True,
        },
    }
    receipt["receipt_sha256"] = sha256_obj(receipt)
    return model, receipt


def verify_phos_migration_receipt(
    receipt: Mapping[str, Any],
    *,
    model: nn.Module,
) -> dict[str, Any]:
    """Verify receipt integrity and the exact destination parameter identity."""

    payload = dict(receipt)
    expected_receipt_sha = str(payload.pop("receipt_sha256", ""))
    actual_receipt_sha = sha256_obj(payload)
    if actual_receipt_sha != expected_receipt_sha:
        raise RuntimeError("migration receipt SHA-256 mismatch")
    if payload.get("schema") != MIGRATION_SCHEMA or payload.get("transform") != MIGRATION_TRANSFORM:
        raise RuntimeError("unsupported PHOS migration receipt schema or transform")
    actual_destination_sha = parameter_sha256(model)
    expected_destination_sha = str(payload.get("destination_parameter_sha256") or "")
    if actual_destination_sha != expected_destination_sha:
        raise RuntimeError(
            "destination parameter SHA-256 mismatch: "
            f"{actual_destination_sha} != {expected_destination_sha}"
        )
    return {
        "verified": True,
        "transform": MIGRATION_TRANSFORM,
        "destination_parameter_sha256": actual_destination_sha,
    }
