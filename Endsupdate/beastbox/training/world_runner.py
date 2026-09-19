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
        raise ValueError(
            f"{label} corpus contains characters absent from parent tokenizer: {preview!r}"
        )
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


def _telemetry_row(
    output: Mapping[str, Any],
    *,
    step: int,
    corpus: str,
    loss: torch.Tensor,
) -> dict[str, Any]:
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
    payload = torch.load(path, map_location="cpu", weights_only=True)
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
        raise RuntimeError(
            f"reloaded parameter SHA-256 mismatch: {reloaded_sha} != {final_parameter_sha}"
        )
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
        if (
            name in rows
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ValueError("invalid CHECKSUMS.sha256 row")
        rows[name] = digest
    if set(rows) != _REQUIRED_RUN_FILES:
        raise ValueError("CHECKSUMS.sha256 does not enumerate the sealed run files")
    return rows


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


def _require_recorded_file_hash(
    run_manifest: Mapping[str, Any],
    checksums: Mapping[str, str],
    *,
    field: str,
    filename: str,
    label: str,
) -> None:
    recorded = str(run_manifest.get(field) or "")
    actual = checksums[filename]
    if recorded != actual:
        raise RuntimeError(f"{label} SHA-256 mismatch: {recorded} != {actual}")


def _verify_training_log(path: Path, *, expected_steps: int) -> None:
    raw_rows = path.read_text(encoding="utf-8").splitlines()
    if len(raw_rows) != expected_steps:
        raise RuntimeError("recorded steps do not match training log length")
    for expected_step, raw in enumerate(raw_rows, start=1):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("training log contains invalid JSON") from exc
        if not isinstance(row, Mapping) or row.get("step") != expected_step:
            raise RuntimeError("recorded steps do not match training log sequence")
        if row.get("corpus") not in {"lexical", "world"}:
            raise RuntimeError("training log contains an invalid corpus selector")


def _verify_checkpoint_tokenizer(
    checkpoint: Mapping[str, Any],
    migration_receipt: Mapping[str, Any],
) -> None:
    tokenizer = checkpoint.get("tokenizer")
    if not isinstance(tokenizer, Mapping):
        raise RuntimeError("checkpoint tokenizer is missing")
    for character, index in tokenizer.items():
        if not isinstance(character, str) or len(character) != 1:
            raise RuntimeError("checkpoint tokenizer contains a non-character key")
        if isinstance(index, bool) or not isinstance(index, int):
            raise RuntimeError("checkpoint tokenizer contains a non-integer id")
    migration_tokenizer = migration_receipt.get("tokenizer")
    if not isinstance(migration_tokenizer, Mapping):
        raise RuntimeError("migration tokenizer record is missing")
    expected_vocab = migration_tokenizer.get("vocab_size")
    if isinstance(expected_vocab, bool) or not isinstance(expected_vocab, int):
        raise RuntimeError("migration tokenizer vocab_size is invalid")
    ids = list(tokenizer.values())
    if len(tokenizer) != expected_vocab or set(ids) != set(range(expected_vocab)):
        raise RuntimeError("checkpoint tokenizer ids do not match migration record")
    if sha256_obj(dict(tokenizer)) != migration_tokenizer.get("sha256"):
        raise RuntimeError("checkpoint tokenizer SHA-256 does not match migration record")


def _verify_migration_receipt_integrity(
    migration_receipt: Mapping[str, Any],
    *,
    expected_initial_parameter_sha: str,
) -> str:
    payload = dict(migration_receipt)
    receipt_sha = str(payload.pop("receipt_sha256", ""))
    if sha256_obj(payload) != receipt_sha:
        raise RuntimeError("migration receipt SHA-256 mismatch")
    if payload.get("schema") != "zeref-phos-migration-receipt-v1":
        raise RuntimeError("unsupported PHOS migration receipt schema")
    if payload.get("transform") != "sparkcst-to-phos-v1":
        raise RuntimeError("unsupported PHOS migration transform")
    if payload.get("destination_parameter_sha256") != expected_initial_parameter_sha:
        raise RuntimeError("migration receipt does not bind the initial descendant parameters")
    return receipt_sha


def verify_descendant_run(output_dir: str | Path) -> dict[str, Any]:
    """Verify sealed files and all recorded cross-file lineage bindings."""

    root = Path(output_dir)
    checksums = _read_checksums(root)
    for name in sorted(checksums):
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"sealed run file is missing: {name}")
        actual = sha256_file(path)
        if actual != checksums[name]:
            raise RuntimeError(f"checksum mismatch for {name}: {actual} != {checksums[name]}")

    run_manifest = _read_json_object(root / "run_manifest.json", "run manifest")
    if run_manifest.get("schema") != RUN_SCHEMA:
        raise RuntimeError("unexpected Zeref-PHOS run manifest schema")
    generation = _generation_id(str(run_manifest.get("generation_id") or ""))

    _require_recorded_file_hash(
        run_manifest,
        checksums,
        field="config_sha256",
        filename="config.json",
        label="config",
    )
    _require_recorded_file_hash(
        run_manifest,
        checksums,
        field="training_log_sha256",
        filename="training_log.jsonl",
        label="training log",
    )
    _require_recorded_file_hash(
        run_manifest,
        checksums,
        field="parameter_hashes_sha256",
        filename="parameter_hashes.json",
        label="parameter hashes",
    )
    _require_recorded_file_hash(
        run_manifest,
        checksums,
        field="checkpoint_sha256",
        filename="checkpoint.pt",
        label="checkpoint",
    )

    model, checkpoint = _reload_checkpoint(root / "checkpoint.pt")
    model_config = checkpoint.get("model_config")
    if not isinstance(model_config, Mapping):
        raise RuntimeError("checkpoint model_config is missing")
    block = model_config.get("max_seq_len")
    if isinstance(block, bool) or not isinstance(block, int) or block <= 0:
        raise RuntimeError("checkpoint max_seq_len is invalid")

    config = _read_json_object(root / "config.json", "config")
    normalized_config = _train_config(config, block=block)
    if normalized_config != config:
        raise RuntimeError("config is not canonical")
    steps_completed = run_manifest.get("steps_completed")
    if isinstance(steps_completed, bool) or not isinstance(steps_completed, int):
        raise RuntimeError("recorded steps must be an integer")
    if steps_completed != normalized_config["steps"]:
        raise RuntimeError("recorded steps do not match config")
    _verify_training_log(root / "training_log.jsonl", expected_steps=steps_completed)

    actual_parameter_sha = parameter_sha256(model)
    expected_parameter_sha = str(run_manifest.get("final_parameter_sha256") or "")
    if actual_parameter_sha != expected_parameter_sha:
        raise RuntimeError(
            f"sealed parameter SHA-256 mismatch: {actual_parameter_sha} != {expected_parameter_sha}"
        )
    if checkpoint.get("final_parameter_sha256") != expected_parameter_sha:
        raise RuntimeError("checkpoint final parameter SHA-256 does not match run manifest")
    if checkpoint.get("generation_id") != generation:
        raise RuntimeError("checkpoint generation_id does not match run manifest")

    parameter_hashes = _read_json_object(root / "parameter_hashes.json", "parameter hashes")
    if parameter_hashes.get("schema") != "zeref-phos-parameter-hashes-v1":
        raise RuntimeError("unexpected parameter hashes schema")
    initial_parameter_sha = str(run_manifest.get("initial_parameter_sha256") or "")
    if parameter_hashes.get("initial_parameter_sha256") != initial_parameter_sha:
        raise RuntimeError("initial parameter SHA-256 does not match run manifest")
    if parameter_hashes.get("final_parameter_sha256") != expected_parameter_sha:
        raise RuntimeError("parameter_hashes.json does not match sealed model")
    if parameter_hashes.get("parameter_drift") is not True:
        raise RuntimeError("parameter_hashes.json does not record parameter drift")

    migration_receipt = _read_json_object(root / "migration_receipt.json", "migration receipt")
    migration_sha = _verify_migration_receipt_integrity(
        migration_receipt,
        expected_initial_parameter_sha=initial_parameter_sha,
    )
    if run_manifest.get("migration_receipt_sha256") != migration_sha:
        raise RuntimeError("migration receipt SHA-256 does not match run manifest")
    if checkpoint.get("migration_receipt_sha256") != migration_sha:
        raise RuntimeError("migration receipt SHA-256 does not match checkpoint")
    _verify_checkpoint_tokenizer(checkpoint, migration_receipt)

    run_parent = run_manifest.get("parent")
    migration_parent = migration_receipt.get("parent")
    if not isinstance(run_parent, Mapping) or not isinstance(migration_parent, Mapping):
        raise RuntimeError("parent lineage record is missing")
    for field in ("checkpoint_sha256", "architecture_sha256", "parameter_sha256"):
        if run_parent.get(field) != migration_parent.get(field):
            raise RuntimeError(f"parent lineage {field} mismatch")

    quantum_receipt = _read_json_object(
        root / "quantum_control_receipt.json",
        "quantum control receipt",
    )
    quantum_verified = verify_quantum_control_receipt(quantum_receipt)
    quantum_sha = str(quantum_receipt.get("receipt_sha256") or "")
    run_quantum = run_manifest.get("quantum")
    if not isinstance(run_quantum, Mapping):
        raise RuntimeError("quantum record is missing from run manifest")
    if run_quantum.get("receipt_sha256") != quantum_sha:
        raise RuntimeError("quantum receipt SHA-256 does not match run manifest")
    if checkpoint.get("quantum_control_receipt_sha256") != quantum_sha:
        raise RuntimeError("quantum receipt SHA-256 does not match checkpoint")
    if run_quantum.get("mode") != quantum_verified["mode"]:
        raise RuntimeError("quantum mode does not match verified receipt")
    if run_quantum.get("source_event_sha256") != quantum_verified["source_event_sha256"]:
        raise RuntimeError("quantum source event SHA-256 does not match verified receipt")

    combined_corpus = _read_json_object(root / "corpus_manifest.json", "corpus manifest")
    if combined_corpus.get("schema") != COMBINED_CORPUS_SCHEMA:
        raise RuntimeError("unexpected combined corpus manifest schema")
    run_corpora = run_manifest.get("corpora")
    if not isinstance(run_corpora, Mapping):
        raise RuntimeError("corpus record is missing from run manifest")
    for label in ("lexical", "world"):
        corpus_manifest = combined_corpus.get(label)
        if not isinstance(corpus_manifest, Mapping):
            raise RuntimeError(f"combined corpus manifest is missing {label}")
        if corpus_manifest.get("schema") != "zeref-phos-corpus-manifest-v1":
            raise RuntimeError(f"unexpected {label} corpus manifest schema")
        if corpus_manifest.get("kind") != label:
            raise RuntimeError(f"combined corpus kind mismatch for {label}")
        recorded_dataset_sha = run_corpora.get(f"{label}_dataset_sha256")
        sealed_dataset_sha = corpus_manifest.get("dataset_sha256")
        if recorded_dataset_sha != sealed_dataset_sha:
            raise RuntimeError(
                f"corpus dataset SHA-256 mismatch for {label}: "
                f"{recorded_dataset_sha} != {sealed_dataset_sha}"
            )

    return {
        "verified": True,
        "generation_id": generation,
        "parameter_sha256": actual_parameter_sha,
    }
