"""Offline deterministic training and sealing for Zeref-PHOS descendants."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

try:
    import torch
    import torch.nn as nn
except ImportError as exc:  # pragma: no cover - optional ML installation
    raise RuntimeError("Install ML extra: pip install 'cosmos-beast-box[ml]'") from exc

from beastbox.hashutil import canonical_json, sha256_obj
from beastbox.models.phos_reference import PHOSReferenceLM

from .corpus import verify_corpus_manifest
from .lineage import sha256_file, write_canonical_json
from .phos_descendant import (
    migrate_sparkcst_to_phos,
    parameter_sha256,
    verify_phos_migration_receipt,
)
from .quantum_control import verify_quantum_control_receipt

RUN_SCHEMA = "zeref-phos-world-run-manifest-v1"
CONFIG_SCHEMA = "zeref-phos-world-train-config-v1"
CHECKPOINT_SCHEMA = "zeref-phos-descendant-checkpoint-v1"
COMBINED_CORPUS_SCHEMA = "zeref-phos-combined-corpus-manifest-v1"
_GENERATION_RE = re.compile(r"[A-Za-z0-9_.-]{1,128}")
_CONFIG_KEYS = {"schema", "steps", "seq", "batch", "lr", "seed", "sampling_weights"}
_REQUIRED_RUN_FILES = {
    "run_manifest.json",
    "corpus_manifest.json",
    "quantum_control_receipt.json",
    "migration_receipt.json",
    "config.json",
    "training_log.jsonl",
    "parameter_hashes.json",
    "checkpoint.pt",
}


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _train_config(config: Mapping[str, Any], *, block: int) -> dict[str, Any]:
    if set(config) != _CONFIG_KEYS:
        raise ValueError("training config fields do not match zeref-phos-world-train-config-v1")
    if config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("unexpected Zeref-PHOS training config schema")
    steps = _positive_int(config.get("steps"), "steps")
    seq = _positive_int(config.get("seq"), "seq")
    batch = _positive_int(config.get("batch"), "batch")
    seed = config.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    lr = config.get("lr")
    if isinstance(lr, bool) or not isinstance(lr, (int, float)):
        raise ValueError("lr must be a finite positive number")
    learning_rate = float(lr)
    if not math.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("lr must be a finite positive number")
    if seq > block:
        raise ValueError("seq cannot exceed the parent native block")

    raw_weights = config.get("sampling_weights")
    if not isinstance(raw_weights, Mapping) or set(raw_weights) != {"lexical", "world"}:
        raise ValueError("sampling_weights must contain lexical and world")
    weights = {
        "lexical": _positive_int(raw_weights.get("lexical"), "sampling_weights.lexical"),
        "world": _positive_int(raw_weights.get("world"), "sampling_weights.world"),
    }
    return {
        "schema": CONFIG_SCHEMA,
        "steps": steps,
        "seq": seq,
        "batch": batch,
        "lr": learning_rate,
        "seed": seed,
        "sampling_weights": weights,
    }


def _generation_id(value: str) -> str:
    generation = str(value)
    if _GENERATION_RE.fullmatch(generation) is None:
        raise ValueError("generation_id must contain only letters, numbers, '.', '_' or '-'")
    return generation


def _training_text(root: str | Path) -> str:
    path = Path(root) / "train.txt"
    text = path.read_text(encoding="utf-8")
    if not text:
        raise ValueError(f"training corpus is empty: {path}")
    return text


def _encode_text(text: str, tokenizer: Mapping[str, int], *, label: str) -> torch.Tensor:
    missing = sorted({character for character in text if character not in tokenizer})
    if missing:
        preview = missing[:12]
        raise ValueError(f"{label} corpus contains characters absent from parent tokenizer: {preview!r}")
    return torch.tensor([int(tokenizer[character]) for character in text], dtype=torch.long)


def _batch(
    data: torch.Tensor,
    *,
    seq: int,
    batch: int,
    generator: torch.Generator,
) -> tuple[torch.Tensor, torch.Tensor]:
    available = int(data.numel()) - seq - 1
    if available <= 0:
        raise ValueError("training corpus is too short for configured sequence length")
    starts = torch.randint(0, available + 1, (batch,), generator=generator)
    x = torch.stack([data[int(start) : int(start) + seq] for start in starts])
    y = torch.stack([data[int(start) + 1 : int(start) + seq + 1] for start in starts])
    return x, y


def _telemetry_row(output: Mapping[str, Any], *, step: int, corpus: str, loss: torch.Tensor) -> dict[str, Any]:
    loss_value = float(loss.detach().cpu().item())
    if not math.isfinite(loss_value):
        raise RuntimeError("non-finite training loss")
    gates: list[float] = []
    sigmas: list[float] = []
    state_rms: list[float] = []
    telemetry = output.get("telemetry")
    if not isinstance(telemetry, list) or not telemetry:
        raise RuntimeError("PHOS telemetry is missing")
    for layer in telemetry:
        gate = float(layer["gate"].detach().cpu().item())
        sigma = float(layer["sigma"].detach().cpu().item())
        state = layer["state"]
        rms = float(torch.sqrt(torch.mean(state.detach() * state.detach())).cpu().item())
        if not all(math.isfinite(value) for value in (gate, sigma, rms)):
            raise RuntimeError("non-finite PHOS state/gate/sigma telemetry")
        gates.append(gate)
        sigmas.append(sigma)
        state_rms.append(rms)
    return {
        "step": step,
        "corpus": corpus,
        "loss": loss_value,
        "gates": gates,
        "sigmas": sigmas,
        "state_rms": state_rms,
    }


def _finite_gradients(model: nn.Module) -> None:
    for name, parameter in model.named_parameters():
        gradient = parameter.grad
        if gradient is not None and not torch.isfinite(gradient).all():
            raise RuntimeError(f"non-finite gradient: {name}")


def _model_config(parent_config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "vocab_size": int(parent_config["vocab"]),
        "d_model": int(parent_config["n_embd"]),
        "n_heads": int(parent_config["n_head"]),
        "n_layers": int(parent_config["n_layer"]),
        "max_seq_len": int(parent_config["block"]),
        "enable_external_state": True,
        "tie_embeddings": False,
    }


def _reload_checkpoint(path: Path) -> tuple[PHOSReferenceLM, Mapping[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, Mapping) or payload.get("schema") != CHECKPOINT_SCHEMA:
        raise RuntimeError("unexpected Zeref-PHOS checkpoint schema")
    model_config = payload.get("model_config")
    if not isinstance(model_config, Mapping):
        raise RuntimeError("checkpoint model_config is missing")
    model = PHOSReferenceLM(**dict(model_config))
    state = payload.get("model")
    if not isinstance(state, Mapping):
        raise RuntimeError("checkpoint model state is missing")
    model.load_state_dict(state, strict=True)
    return model, payload


def _write_checksums(root: Path, names: set[str]) -> None:
    rows = [f"{sha256_file(root / name)}  {name}\n" for name in sorted(names)]
    (root / "CHECKSUMS.sha256").write_text("".join(rows), encoding="utf-8")


def train_descendant_generation(
    *,
    parent_model: nn.Module,
    parent_config: Mapping[str, Any],
    tokenizer: Mapping[str, int],
    parent_checkpoint_sha256: str,
    parent_architecture_sha256: str,
    expected_parent_parameter_sha256: str,
    lexical_manifest: Mapping[str, Any],
    lexical_root: str | Path,
    world_manifest: Mapping[str, Any],
    world_root: str | Path,
    quantum_receipt: Mapping[str, Any],
    config: Mapping[str, Any],
    output_dir: str | Path,
    generation_id: str,
) -> dict[str, Any]:
    """Train one deterministic descendant from already-loaded frozen parent weights.

    This function performs no network access and submits no quantum/cloud work.
    Every input is verified before an output directory is created.
    """

    generation = _generation_id(generation_id)
    target = Path(output_dir)
    if target.exists():
        raise FileExistsError(f"generation output already exists: {target}")

    lexical_verified = verify_corpus_manifest(lexical_manifest, root=lexical_root)
    world_verified = verify_corpus_manifest(world_manifest, root=world_root)
    if lexical_verified["kind"] != "lexical" or world_verified["kind"] != "world":
        raise ValueError("runner requires one lexical and one world corpus manifest")
    quantum_verified = verify_quantum_control_receipt(quantum_receipt)

    block = int(parent_config.get("block", 0))
    normalized_config = _train_config(config, block=block)
    lexical_text = _training_text(lexical_root)
    world_text = _training_text(world_root)
    lexical_data = _encode_text(lexical_text, tokenizer, label="lexical")
    world_data = _encode_text(world_text, tokenizer, label="world")
    seq = int(normalized_config["seq"])
    if int(lexical_data.numel()) <= seq + 1 or int(world_data.numel()) <= seq + 1:
        raise ValueError("training corpus is too short for configured sequence length")

    torch.manual_seed(int(normalized_config["seed"]))
    model, migration_receipt = migrate_sparkcst_to_phos(
        parent_model,
        parent_config=parent_config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256=parent_checkpoint_sha256,
        parent_architecture_sha256=parent_architecture_sha256,
        expected_parent_parameter_sha256=expected_parent_parameter_sha256,
    )
    verify_phos_migration_receipt(migration_receipt, model=model)
    initial_parameter_sha = parameter_sha256(model)

    control_vector = torch.tensor(list(quantum_receipt["vector"]), dtype=torch.float32)
    generator = torch.Generator().manual_seed(int(normalized_config["seed"]))
    schedule = ["lexical"] * int(normalized_config["sampling_weights"]["lexical"])
    schedule += ["world"] * int(normalized_config["sampling_weights"]["world"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(normalized_config["lr"]))
    model.train()
    log_rows: list[dict[str, Any]] = []

    for step in range(1, int(normalized_config["steps"]) + 1):
        arm = schedule[(step - 1) % len(schedule)]
        data = lexical_data if arm == "lexical" else world_data
        x, y = _batch(
            data,
            seq=seq,
            batch=int(normalized_config["batch"]),
            generator=generator,
        )
        output = model(x, targets=y, control_vector=control_vector)
        loss = output.get("loss")
        if not torch.is_tensor(loss):
            raise RuntimeError("PHOS training loss is missing")
        row = _telemetry_row(output, step=step, corpus=arm, loss=loss)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        _finite_gradients(model)
        optimizer.step()
        log_rows.append(row)

    final_parameter_sha = parameter_sha256(model)
    if final_parameter_sha == initial_parameter_sha:
        raise RuntimeError("training completed without any parameter change")

    target.mkdir(parents=True, exist_ok=False)
    combined_corpus = {
        "schema": COMBINED_CORPUS_SCHEMA,
        "lexical": dict(lexical_manifest),
        "world": dict(world_manifest),
    }
    write_canonical_json(target / "corpus_manifest.json", combined_corpus)
    write_canonical_json(target / "quantum_control_receipt.json", dict(quantum_receipt))
    write_canonical_json(target / "migration_receipt.json", migration_receipt)
    config_sha = write_canonical_json(target / "config.json", normalized_config)

    log_path = target / "training_log.jsonl"
    log_path.write_text("".join(canonical_json(row) + "\n" for row in log_rows), encoding="utf-8")
    training_log_sha = sha256_file(log_path)
    parameter_hashes = {
        "schema": "zeref-phos-parameter-hashes-v1",
        "initial_parameter_sha256": initial_parameter_sha,
        "final_parameter_sha256": final_parameter_sha,
        "parameter_drift": True,
    }
    parameter_hashes_sha = write_canonical_json(target / "parameter_hashes.json", parameter_hashes)

    checkpoint_path = target / "checkpoint.pt"
    checkpoint_payload = {
        "schema": CHECKPOINT_SCHEMA,
        "generation_id": generation,
        "model": model.state_dict(),
        "model_config": _model_config(parent_config),
        "tokenizer": dict(tokenizer),
        "final_parameter_sha256": final_parameter_sha,
        "migration_receipt_sha256": migration_receipt["receipt_sha256"],
        "quantum_control_receipt_sha256": quantum_receipt["receipt_sha256"],
    }
    torch.save(checkpoint_payload, checkpoint_path)
    checkpoint_sha = sha256_file(checkpoint_path)

    reloaded, reloaded_payload = _reload_checkpoint(checkpoint_path)
    reloaded_sha = parameter_sha256(reloaded)
    if reloaded_sha != final_parameter_sha:
        raise RuntimeError(f"reloaded parameter SHA-256 mismatch: {reloaded_sha} != {final_parameter_sha}")
    if reloaded_payload.get("generation_id") != generation:
        raise RuntimeError("reloaded checkpoint generation_id mismatch")

    run_manifest: dict[str, Any] = {
        "schema": RUN_SCHEMA,
        "generation_id": generation,
        "steps_completed": int(normalized_config["steps"]),
        "initial_parameter_sha256": initial_parameter_sha,
        "final_parameter_sha256": final_parameter_sha,
        "training_log_sha256": training_log_sha,
        "checkpoint_sha256": checkpoint_sha,
        "config_sha256": config_sha,
        "parameter_hashes_sha256": parameter_hashes_sha,
        "parent": {
            "checkpoint_sha256": str(parent_checkpoint_sha256).lower(),
            "architecture_sha256": str(parent_architecture_sha256).lower(),
            "parameter_sha256": str(expected_parent_parameter_sha256).lower(),
        },
        "corpora": {
            "lexical_dataset_sha256": lexical_verified["dataset_sha256"],
            "world_dataset_sha256": world_verified["dataset_sha256"],
        },
        "quantum": {
            "mode": quantum_verified["mode"],
            "source_event_sha256": quantum_verified["source_event_sha256"],
            "receipt_sha256": quantum_receipt["receipt_sha256"],
        },
        "migration_receipt_sha256": migration_receipt["receipt_sha256"],
        "claim_boundary": {
            "architecture_migration_not_parameter_equivalence": True,
            "model_is_not_memory": True,
            "authority_not_transferred": True,
            "quantum_advantage_established": False,
            "no_consciousness_claim": True,
        },
    }
    write_canonical_json(target / "run_manifest.json", run_manifest)
    _write_checksums(target, _REQUIRED_RUN_FILES)
    verification = verify_descendant_run(target)
    if not verification["verified"]:
        raise RuntimeError("sealed descendant verification failed")
    return run_manifest


def _read_checksums(root: Path) -> dict[str, str]:
    path = root / "CHECKSUMS.sha256"
    if not path.is_file():
        raise FileNotFoundError("CHECKSUMS.sha256 is missing")
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split("  ", 1)
        if len(parts) != 2:
            raise ValueError("invalid CHECKSUMS.sha256 row")
        digest, name = parts
        if name in rows or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("invalid CHECKSUMS.sha256 row")
        rows[name] = digest
    if set(rows) != _REQUIRED_RUN_FILES:
        raise ValueError("CHECKSUMS.sha256 does not enumerate the sealed run files")
    return rows


def verify_descendant_run(output_dir: str | Path) -> dict[str, Any]:
    """Verify sealed file checksums, reload the checkpoint, and re-hash parameters."""

    root = Path(output_dir)
    checksums = _read_checksums(root)
    for name in sorted(checksums):
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"sealed run file is missing: {name}")
        actual = sha256_file(path)
        if actual != checksums[name]:
            raise RuntimeError(f"checksum mismatch for {name}: {actual} != {checksums[name]}")

    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(run_manifest, dict) or run_manifest.get("schema") != RUN_SCHEMA:
        raise RuntimeError("unexpected Zeref-PHOS run manifest schema")
    quantum_receipt = json.loads((root / "quantum_control_receipt.json").read_text(encoding="utf-8"))
    verify_quantum_control_receipt(quantum_receipt)

    model, checkpoint = _reload_checkpoint(root / "checkpoint.pt")
    actual_parameter_sha = parameter_sha256(model)
    expected_parameter_sha = str(run_manifest.get("final_parameter_sha256") or "")
    if actual_parameter_sha != expected_parameter_sha:
        raise RuntimeError(
            f"sealed parameter SHA-256 mismatch: {actual_parameter_sha} != {expected_parameter_sha}"
        )
    if checkpoint.get("final_parameter_sha256") != expected_parameter_sha:
        raise RuntimeError("checkpoint final parameter SHA-256 does not match run manifest")
    generation = str(run_manifest.get("generation_id") or "")
    if checkpoint.get("generation_id") != generation:
        raise RuntimeError("checkpoint generation_id does not match run manifest")

    parameter_hashes = json.loads((root / "parameter_hashes.json").read_text(encoding="utf-8"))
    if parameter_hashes.get("final_parameter_sha256") != expected_parameter_sha:
        raise RuntimeError("parameter_hashes.json does not match sealed model")
    return {
        "verified": True,
        "generation_id": generation,
        "parameter_sha256": actual_parameter_sha,
    }
