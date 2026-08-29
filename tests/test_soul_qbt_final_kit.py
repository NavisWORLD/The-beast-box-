from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from beastbox.soul import SoulToken, bridge_from_soul


KIT_ROOT = Path(__file__).resolve().parents[1] / "kits" / "SOUL_QBT_FINAL_KIT"
PKG_ROOT = KIT_ROOT / "soul_qbt_final_kit"


def _load_core():
    module_path = PKG_ROOT / "core.py"
    spec = importlib.util.spec_from_file_location("soul_qbt_final_kit.core", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_neutral_qbt_vector_is_zero_beast_perturbation() -> None:
    token = SoulToken.from_qbt({"normalized_vector": [0.5, 0.5, 0.5, 0.5]}, source_type="KIT_NEUTRAL")
    bridge = bridge_from_soul(token)
    assert bridge.quantum_spark == [0.0] * 12


def test_recovery_and_condition_generation_are_deterministic(tmp_path: Path) -> None:
    core = _load_core()
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "provider": "ibm",
                "backend": "ibm_test",
                "shots": 1024,
                "normalized_vector": [0.10, 0.25, 0.30, 0.35],
                "result_digest": "fixture-result",
            }
        ),
        encoding="utf-8",
    )
    first = core.recover_sources(source)
    second = core.recover_sources(source)
    assert first == second
    assert len(first) == 1
    assert len(first[0]["record_id"]) == 64
    conditions_a = core.generate_conditions(first[0], seed=67)
    conditions_b = core.generate_conditions(first[0], seed=67)
    assert conditions_a == conditions_b
    assert {item["condition"] for item in conditions_a} == {
        "ORIGINAL", "SHUFFLED", "CLASSICAL_MATCHED", "NEUTRAL"
    }
    neutral = next(item for item in conditions_a if item["condition"] == "NEUTRAL")
    assert neutral["normalized_vector"] == [0.5, 0.5, 0.5, 0.5]


def test_condition_tokens_share_the_same_public_soul_contract(tmp_path: Path) -> None:
    core = _load_core()
    source = {
        "record_id": "a" * 64,
        "provider": "fixture",
        "backend": "fixture",
        "shots": 4,
        "normalized_vector": [0.1, 0.2, 0.3, 0.4],
        "provenance": {},
    }
    conditions = core.generate_conditions(source, seed=9)
    tokens = [core.condition_to_token(item) for item in conditions]
    assert all(isinstance(token, SoulToken) for token in tokens)
    assert all(token.consumers == ("bridge",) for token in tokens)
    assert all(not any(token.authority.values()) for token in tokens)
    assert all(len(bridge_from_soul(token).quantum_spark) == 12 for token in tokens)


def test_counts_import_uses_declared_four_state_basis_only(tmp_path: Path) -> None:
    core = _load_core()
    source = tmp_path / "counts.json"
    source.write_text(
        json.dumps({"provider": "fixture", "counts": {"00": 1, "01": 1, "10": 2, "11": 0}}),
        encoding="utf-8",
    )
    records = core.recover_sources(source)
    assert records[0]["normalized_vector"] == pytest.approx([0.25, 0.25, 0.5, 0.0])
    assert records[0]["state_semantics"] == "four_state_probability_distribution"
    assert records[0]["shannon_entropy_bits"] == pytest.approx(1.5)


def test_hash_material_is_not_mislabeled_as_entropy(tmp_path: Path) -> None:
    core = _load_core()
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"normalized_vector": [0.2, 0.2, 0.2, 0.2]}), encoding="utf-8")
    record = core.recover_sources(source)[0]
    assert record["state_semantics"] == "qbt_normalized_state"
    assert "shannon_entropy_bits" not in record


def test_blinding_and_classification_are_stable() -> None:
    core = _load_core()
    aliases_1 = core.blind_conditions(["ORIGINAL", "SHUFFLED", "CLASSICAL_MATCHED", "NEUTRAL"], seed=42)
    aliases_2 = core.blind_conditions(["ORIGINAL", "SHUFFLED", "CLASSICAL_MATCHED", "NEUTRAL"], seed=42)
    assert aliases_1 == aliases_2
    assert set(aliases_1.values()) == {"A", "B", "C", "D"}
    assert core.classify_metrics({"downstream_difference": False, "control_separation": False})["kit_classification"] == (
        "ENGINEERING_REPLAY_VERIFIED_NO_DOWNSTREAM_DIFFERENCE"
    )
    assert core.classify_metrics({"downstream_difference": True, "control_separation": True})["kit_classification"] == (
        "ENGINEERING_DOWNSTREAM_DIFFERENCE_OBSERVED_CAUSAL_SOURCE_NOT_ESTABLISHED"
    )
    assert core.classify_metrics({"downstream_difference": True, "control_separation": False})["kit_classification"] == (
        "ENGINEERING_CONTROL_INCONCLUSIVE"
    )


def test_checksum_manifest_detects_tampering(tmp_path: Path) -> None:
    core = _load_core()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "report.md").write_text("sealed\n", encoding="utf-8")
    core.write_checksums(run_dir)
    assert core.verify_checksums(run_dir)["ok"] is True
    (run_dir / "report.md").write_text("tampered\n", encoding="utf-8")
    assert core.verify_checksums(run_dir)["ok"] is False


def test_end_to_end_reference_run_emits_complete_verified_kit(tmp_path: Path) -> None:
    core = _load_core()
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps({
            "provider": "synthetic_fixture",
            "backend": "offline_reference",
            "shots": 1024,
            "normalized_vector": [0.11, 0.23, 0.29, 0.37],
            "result_digest": "synthetic-fixture-not-hardware-evidence",
        }),
        encoding="utf-8",
    )
    records = core.recover_sources(source)
    run_dir = core.execute_run(
        records,
        prompt="same preregistered input",
        output_root=tmp_path / "runs",
        seed=67,
        provider_mode="reference",
    )
    expected = {
        "run_manifest.json", "sources.jsonl", "conditions.jsonl", "blind_key.json",
        "receipts.jsonl", "blind_metrics.json", "metrics.json", "classification.json",
        "report.md", "SHA256SUMS",
    }
    assert expected.issubset({path.name for path in run_dir.iterdir()})
    assert core.verify_checksums(run_dir)["ok"] is True
    conditions = [json.loads(line) for line in (run_dir / "conditions.jsonl").read_text(encoding="utf-8").splitlines()]
    receipts = [json.loads(line) for line in (run_dir / "receipts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {row["alias"] for row in conditions} == {"A", "B", "C", "D"}
    assert len(receipts) == 4
    assert all(row["prepared_manifest_sha256"] for row in receipts)
    assert all(row["token_id"].startswith("sdt-") for row in receipts)
    classification = json.loads((run_dir / "classification.json").read_text(encoding="utf-8"))
    assert classification["official_beast_classification"] == core.OFFICIAL_BEAST_CLASSIFICATION
    assert classification["causal_source_established"] is False
