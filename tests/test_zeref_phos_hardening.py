from __future__ import annotations

import copy
import json
import os
import pickle
import shutil
from pathlib import Path

import pytest
import torch

from beastbox.hashutil import sha256_file
from beastbox.training.corpus import build_corpus, verify_corpus_manifest
from beastbox.training.phos_descendant import migrate_sparkcst_to_phos, parameter_sha256
from beastbox.training.quantum_control import build_quantum_control_receipt
from beastbox.training.world_runner import train_descendant_generation, verify_descendant_run

nn = torch.nn


class TinySparkAttention(nn.Module):
    def __init__(self, d_model: int):
        super().__init__()
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.w54 = nn.Linear(d_model, 54, bias=False)
        self.log_sigma = nn.Parameter(torch.tensor(0.1))
        self.gate = nn.Parameter(torch.tensor([0.2]))


class TinySparkBlock(nn.Module):
    def __init__(self, d_model: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = TinySparkAttention(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )


class TinySparkCST(nn.Module):
    def __init__(self, *, vocab: int, block: int = 32, d_model: int = 24, n_layers: int = 2):
        super().__init__()
        self.tok = nn.Embedding(vocab, d_model)
        self.pos = nn.Embedding(block, d_model)
        self.blocks = nn.ModuleList([TinySparkBlock(d_model) for _ in range(n_layers)])
        self.lnf = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)


class _TouchMarker:
    """Harmless proof that unrestricted pickle loading executed a global."""

    def __init__(self, marker: Path):
        self.marker = str(marker)

    def __reduce__(self):
        return (os.system, (f"touch {self.marker}",))


def _canonical_write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _refresh_checksums(run_dir: Path) -> None:
    names = []
    for line in (run_dir / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _digest, name = line.split("  ", 1)
        names.append(name)
    rows = [f"{sha256_file(run_dir / name)}  {name}" for name in names]
    (run_dir / "CHECKSUMS.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _migration_fixture() -> tuple[TinySparkCST, dict, dict]:
    vocab = 7
    torch.manual_seed(20260913)
    parent = TinySparkCST(vocab=vocab, block=16, d_model=24, n_layers=1)
    config = {
        "vocab": vocab,
        "block": 16,
        "n_layer": 1,
        "n_head": 4,
        "n_embd": 24,
        "d54": 54,
    }
    tokenizer = {chr(ord("a") + index): index for index in range(vocab)}
    return parent, config, tokenizer


def _migrate(parent: TinySparkCST, config: dict, tokenizer: dict):
    return migrate_sparkcst_to_phos(
        parent,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
        expected_parent_parameter_sha256=parameter_sha256(parent),
    )


def _build_corpora(tmp_path: Path):
    lexical_records = [
        {
            "lemma": f"term{i}",
            "part_of_speech": "noun",
            "definition": f"plain definition {i}",
            "synonyms": [],
            "antonyms": [],
            "examples": [f"term{i} example"],
            "source_id": "lex",
        }
        for i in range(24)
    ]
    world_records = [
        {
            "title": f"topic{i}",
            "text": f"plain world fact {i}",
            "source_id": "world",
        }
        for i in range(24)
    ]
    lexical_root = tmp_path / "lexical"
    world_root = tmp_path / "world"
    lexical = build_corpus(
        kind="lexical",
        records=lexical_records,
        sources=[{"source_id": "lex", "uri": "local://lex", "license": "CC0-1.0"}],
        output_dir=lexical_root,
    )
    world = build_corpus(
        kind="world",
        records=world_records,
        sources=[{"source_id": "world", "uri": "local://world", "license": "CC0-1.0"}],
        output_dir=world_root,
    )
    return lexical, lexical_root, world, world_root


def _quantum_receipt() -> dict:
    metadata = {
        "source": "ibm-quantum",
        "mode": "REAL_IBM",
        "result_kind": "observed-counts",
        "native_job_id": "job-hardening-test",
        "backend": "ibm_test_backend",
        "shots": 128,
        "counts": {"00": 64, "01": 32, "10": 16, "11": 16},
        "circuit_sha256": "c" * 64,
        "probe": "two-qubit-HZH-phase-roundtrip",
    }
    probabilities = {"00": 0.5, "01": 0.25, "10": 0.125, "11": 0.125}
    event = {
        "schema": "sensor-event-v1",
        "source": "software-event",
        "text": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        "features": [2.0 * probabilities[key] - 1.0 for key in ("00", "01", "10", "11")],
    }
    return build_quantum_control_receipt(event, mode="zero")


def _world_fixture(tmp_path: Path) -> dict:
    lexical, lexical_root, world, world_root = _build_corpora(tmp_path)
    training_text = (lexical_root / "train.txt").read_text(encoding="utf-8") + (
        world_root / "train.txt"
    ).read_text(encoding="utf-8")
    chars = sorted(set(training_text))
    tokenizer = {character: index for index, character in enumerate(chars)}
    torch.manual_seed(20260913)
    parent = TinySparkCST(vocab=len(chars))
    return {
        "parent": parent,
        "parent_config": {
            "vocab": len(chars),
            "block": 32,
            "n_layer": 2,
            "n_head": 4,
            "n_embd": 24,
            "d54": 54,
        },
        "tokenizer": tokenizer,
        "lexical": lexical,
        "lexical_root": lexical_root,
        "world": world,
        "world_root": world_root,
        "quantum": _quantum_receipt(),
        "train_config": {
            "schema": "zeref-phos-world-train-config-v1",
            "steps": 2,
            "seq": 16,
            "batch": 2,
            "lr": 0.001,
            "seed": 314159,
            "sampling_weights": {"lexical": 1, "world": 1},
        },
    }


def _run(fixture: dict, output_dir: Path) -> None:
    train_descendant_generation(
        parent_model=fixture["parent"],
        parent_config=fixture["parent_config"],
        tokenizer=fixture["tokenizer"],
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
        expected_parent_parameter_sha256=parameter_sha256(fixture["parent"]),
        lexical_manifest=fixture["lexical"],
        lexical_root=fixture["lexical_root"],
        world_manifest=fixture["world"],
        world_root=fixture["world_root"],
        quantum_receipt=fixture["quantum"],
        config=fixture["train_config"],
        output_dir=output_dir,
        generation_id="zeref-phos-hardening-g001",
    )


@pytest.fixture(scope="module")
def sealed_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("zeref-phos-hardening")
    fixture = _world_fixture(root / "inputs")
    output = root / "sealed-run"
    _run(fixture, output)
    return output


def _copy_run(sealed_run: Path, tmp_path: Path) -> Path:
    target = tmp_path / "run"
    shutil.copytree(sealed_run, target)
    return target


def test_descendant_checkpoint_rejects_executable_pickle_payload(sealed_run: Path, tmp_path: Path):
    run = _copy_run(sealed_run, tmp_path)
    checkpoint = run / "checkpoint.pt"
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    marker = tmp_path / "pickle-executed"
    payload["untrusted_extra"] = _TouchMarker(marker)
    torch.save(payload, checkpoint)
    _refresh_checksums(run)

    with pytest.raises((RuntimeError, pickle.UnpicklingError)):
        verify_descendant_run(run)
    assert not marker.exists(), "checkpoint verification executed an unsafe pickle global"


def test_tokenizer_rejects_float_id_coercion():
    parent, config, tokenizer = _migration_fixture()
    bad = dict(tokenizer)
    bad["a"] = float(bad["a"])

    with pytest.raises(ValueError, match="tokenizer"):
        _migrate(parent, config, bad)


def test_tokenizer_rejects_non_string_character_key_coercion():
    parent, config, tokenizer = _migration_fixture()
    bad = dict(tokenizer)
    index = bad.pop("a")
    bad[97] = index

    with pytest.raises(ValueError, match="tokenizer"):
        _migrate(parent, config, bad)


def test_migration_rejects_dtype_change_on_exact_copy():
    parent, config, tokenizer = _migration_fixture()
    parent.tok.weight.data = parent.tok.weight.data.double()

    with pytest.raises(RuntimeError, match="dtype"):
        _migrate(parent, config, tokenizer)


def test_migration_rejects_dtype_change_on_54_to_12_transform():
    parent, config, tokenizer = _migration_fixture()
    parent.blocks[0].attn.w54.weight.data = parent.blocks[0].attn.w54.weight.data.double()

    with pytest.raises(RuntimeError, match="dtype"):
        _migrate(parent, config, tokenizer)


def test_corpus_verifier_recomputes_dataset_identity(tmp_path: Path):
    lexical, lexical_root, _, _ = _build_corpora(tmp_path / "corpora")
    forged = copy.deepcopy(lexical)
    forged["dataset_sha256"] = "0" * 64

    with pytest.raises(RuntimeError, match="dataset SHA-256 mismatch"):
        verify_corpus_manifest(forged, root=lexical_root)


def test_corpus_verifier_rejects_semantic_tamper_even_when_artifact_hash_is_refreshed(tmp_path: Path):
    lexical, lexical_root, _, _ = _build_corpora(tmp_path / "corpora")
    forged = copy.deepcopy(lexical)
    train_jsonl = lexical_root / "train.jsonl"
    rows = [json.loads(line) for line in train_jsonl.read_text(encoding="utf-8").splitlines() if line]
    assert rows
    rows[0]["definition"] = rows[0]["definition"] + " tampered"
    train_jsonl.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    forged["artifacts"]["train.jsonl"] = sha256_file(train_jsonl)

    with pytest.raises((RuntimeError, ValueError)):
        verify_corpus_manifest(forged, root=lexical_root)


def _mutate_run_manifest(run: Path, mutation) -> None:
    path = run / "run_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mutation(manifest)
    _canonical_write(path, manifest)
    _refresh_checksums(run)


def test_run_verifier_rejects_recorded_step_count_disagreement(sealed_run: Path, tmp_path: Path):
    run = _copy_run(sealed_run, tmp_path)
    _mutate_run_manifest(run, lambda manifest: manifest.__setitem__("steps_completed", 999))

    with pytest.raises(RuntimeError, match="steps"):
        verify_descendant_run(run)


def test_run_verifier_rejects_recorded_config_hash_disagreement(sealed_run: Path, tmp_path: Path):
    run = _copy_run(sealed_run, tmp_path)
    _mutate_run_manifest(run, lambda manifest: manifest.__setitem__("config_sha256", "0" * 64))

    with pytest.raises(RuntimeError, match="config"):
        verify_descendant_run(run)


def test_run_verifier_rejects_recorded_checkpoint_hash_disagreement(sealed_run: Path, tmp_path: Path):
    run = _copy_run(sealed_run, tmp_path)
    _mutate_run_manifest(run, lambda manifest: manifest.__setitem__("checkpoint_sha256", "0" * 64))

    with pytest.raises(RuntimeError, match="checkpoint"):
        verify_descendant_run(run)


def test_run_verifier_rejects_recorded_corpus_hash_disagreement(sealed_run: Path, tmp_path: Path):
    run = _copy_run(sealed_run, tmp_path)

    def mutate(manifest: dict) -> None:
        manifest["corpora"]["lexical_dataset_sha256"] = "0" * 64

    _mutate_run_manifest(run, mutate)
    with pytest.raises(RuntimeError, match="corpus"):
        verify_descendant_run(run)
