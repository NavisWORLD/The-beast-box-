from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")

from beastbox.training.corpus import build_corpus
from beastbox.training.lineage import build_parent_manifest
from beastbox.training.quantum_control import build_quantum_control_receipt
from beastbox.training.world_runner import verify_descendant_run
from scripts.train_zeref_phos_world import main


_ARCHITECTURE_SOURCE = '''\
import torch
import torch.nn as nn

BLOCK = 32
N_LAYER = 2
N_HEAD = 4
N_EMBD = 24
D54 = 54

class SparkAttention(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.w54 = nn.Linear(d_model, 54, bias=False)
        self.log_sigma = nn.Parameter(torch.tensor(0.1))
        self.gate = nn.Parameter(torch.tensor([0.2]))

class SparkBlock(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = SparkAttention(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )

class SparkCST(nn.Module):
    def __init__(self, vocab, return_debug=False):
        super().__init__()
        self.tok = nn.Embedding(vocab, N_EMBD)
        self.pos = nn.Embedding(BLOCK, N_EMBD)
        self.blocks = nn.ModuleList([SparkBlock(N_EMBD) for _ in range(N_LAYER)])
        self.lnf = nn.LayerNorm(N_EMBD)
        self.head = nn.Linear(N_EMBD, vocab, bias=False)
        self.register_buffer("mask", torch.tril(torch.ones(BLOCK, BLOCK)))
'''


def _build_corpora(tmp_path: Path):
    lexical_root = tmp_path / "lexical"
    world_root = tmp_path / "world"
    lexical = build_corpus(
        kind="lexical",
        records=[
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
        ],
        sources=[{"source_id": "lex", "uri": "local://lex", "license": "CC0-1.0"}],
        output_dir=lexical_root,
    )
    world = build_corpus(
        kind="world",
        records=[
            {"title": f"topic{i}", "text": f"plain world fact {i}", "source_id": "world"}
            for i in range(24)
        ],
        sources=[{"source_id": "world", "uri": "local://world", "license": "CC0-1.0"}],
        output_dir=world_root,
    )
    training_text = (lexical_root / "train.txt").read_text(encoding="utf-8") + (
        world_root / "train.txt"
    ).read_text(encoding="utf-8")
    tokenizer = {character: index for index, character in enumerate(sorted(set(training_text)))}
    return lexical, lexical_root, world, world_root, tokenizer


def _write_parent(parent_root: Path, tokenizer: dict[str, int]):
    parent_root.mkdir(parents=True)
    architecture_path = parent_root / "architecture.py"
    architecture_path.write_text(_ARCHITECTURE_SOURCE, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("tiny_zeref_parent", architecture_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    torch.manual_seed(20260913)
    model = module.SparkCST(len(tokenizer), True)
    state = dict(model.state_dict())
    state.pop("mask")
    checkpoint = {
        "config": {
            "vocab": len(tokenizer),
            "block": 32,
            "n_layer": 2,
            "n_head": 4,
            "n_embd": 24,
            "d54": 54,
        },
        "model": state,
        "stoi": tokenizer,
        "itos": {index: character for character, index in tokenizer.items()},
    }
    checkpoint_path = parent_root / "checkpoint.pt"
    torch.save(checkpoint, checkpoint_path)
    manifest = build_parent_manifest(
        model_id="zeref-cli-test-parent",
        checkpoint_path="checkpoint.pt",
        architecture_path="architecture.py",
        tokenizer_path=None,
        memory_ledger_path=None,
        root=parent_root,
    )
    manifest_path = parent_root / "parent_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest, manifest_path, checkpoint_path


def _quantum_receipt() -> dict:
    metadata = {
        "source": "ibm-quantum",
        "mode": "REAL_IBM",
        "result_kind": "observed-counts",
        "native_job_id": "job-cli-test",
        "backend": "ibm_test_backend",
        "shots": 128,
        "counts": {"00": 64, "01": 32, "10": 16, "11": 16},
        "circuit_sha256": "d" * 64,
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


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path):
    lexical, lexical_root, world, world_root, tokenizer = _build_corpora(tmp_path / "corpora")
    parent_manifest, parent_manifest_path, checkpoint_path = _write_parent(tmp_path / "parent", tokenizer)
    lexical_manifest_path = _write_json(lexical_root / "input_manifest.json", lexical)
    world_manifest_path = _write_json(world_root / "input_manifest.json", world)
    quantum_path = _write_json(tmp_path / "quantum.json", _quantum_receipt())
    config_path = _write_json(
        tmp_path / "config.json",
        {
            "schema": "zeref-phos-world-train-config-v1",
            "steps": 2,
            "seq": 16,
            "batch": 2,
            "lr": 0.001,
            "seed": 314159,
            "sampling_weights": {"lexical": 1, "world": 1},
        },
    )
    return {
        "parent_manifest": parent_manifest,
        "parent_manifest_path": parent_manifest_path,
        "checkpoint_path": checkpoint_path,
        "lexical_root": lexical_root,
        "lexical_manifest_path": lexical_manifest_path,
        "world_root": world_root,
        "world_manifest_path": world_manifest_path,
        "quantum_path": quantum_path,
        "config_path": config_path,
    }


def _argv(inputs: dict, output: Path) -> list[str]:
    return [
        "--parent-manifest",
        str(inputs["parent_manifest_path"]),
        "--parent-root",
        str(inputs["parent_manifest_path"].parent),
        "--lexical-manifest",
        str(inputs["lexical_manifest_path"]),
        "--lexical-root",
        str(inputs["lexical_root"]),
        "--world-manifest",
        str(inputs["world_manifest_path"]),
        "--world-root",
        str(inputs["world_root"]),
        "--quantum-receipt",
        str(inputs["quantum_path"]),
        "--config",
        str(inputs["config_path"]),
        "--out",
        str(output),
        "--generation-id",
        "zeref-phos-cli-test-g001",
    ]


def test_cli_trains_from_verified_parent_with_historical_loader(tmp_path: Path):
    inputs = _inputs(tmp_path / "inputs")
    output = tmp_path / "run"

    assert main(_argv(inputs, output)) == 0

    verification = verify_descendant_run(output)
    assert verification["verified"] is True
    run_manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    artifacts = inputs["parent_manifest"]["artifacts"]
    assert run_manifest["parent"]["checkpoint_sha256"] == artifacts["checkpoint"]["sha256"]
    assert run_manifest["parent"]["architecture_sha256"] == artifacts["architecture"]["sha256"]
    assert run_manifest["claim_boundary"]["authority_not_transferred"] is True
    assert run_manifest["claim_boundary"]["quantum_advantage_established"] is False


def test_cli_rejects_tampered_parent_before_output(tmp_path: Path):
    inputs = _inputs(tmp_path / "inputs")
    output = tmp_path / "run"
    with inputs["checkpoint_path"].open("ab") as handle:
        handle.write(b"tamper")

    with pytest.raises(RuntimeError, match="checkpoint SHA-256 mismatch"):
        main(_argv(inputs, output))
    assert not output.exists()
