"""Native arm sharding and aggregation cannot turn fixtures into claimed evidence."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from beastbox.quantum_buddy.operators import QuantumStateOperator
from beastbox.quantum_buddy.shadow import (
    FrozenPhase8Config,
    generate_synthetic_cohort,
    run_phase8,
)
from scripts.aggregate_quantum_buddy_phase8 import assemble

PREREG = json.loads(
    (Path(__file__).resolve().parents[1] /
     "docs/quantum-buddy/phase8/preregistration.json").read_text()
)


class FakeModel:
    """Synthetic test double; never pass this through native aggregation."""
    def __call__(self, prompt, seed, dyn12, qstate12, mode):
        return {
            "logit_l2": 0.0,
            "duration_ms": 0.5,
            "response_ordinary": "fixture ordinary",
            "response_buddy": "fixture buddy",
            "checkpoint_sha256": "a" * 64,
            "model_weights_changed": False,
            "fresh_hardware_used": False,
            "quantum_advantage_proven": False,
        }


def test_real_sampling_settings_frozen_before_first_native_holdout():
    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a" * 64)
    assert config.prereg["native_generation_temperature"] == 0.8
    assert config.prereg["native_generation_top_k"] == 40
    assert config.prereg["native_generation_max_tokens"] == 24
    wrong = {**PREREG, "native_generation_temperature": 0}
    with pytest.raises(ValueError, match="sampling"):
        FrozenPhase8Config.from_dict(wrong, model_checkpoint_sha256="a" * 64)


def test_single_arm_requires_explicit_partial_and_never_claims_full_run():
    cohort = generate_synthetic_cohort(32, 4, seed=PREREG["cohort_seed"])
    config = FrozenPhase8Config.from_dict(PREREG, model_checkpoint_sha256="a" * 64)
    operator = QuantumStateOperator()
    report = run_phase8(
        cohort, PREREG["prompt_bank"][:1], PREREG["sampling_seeds"][:1],
        operator, FakeModel(), config, arms=["off"], partial_shard=True,
    )
    assert report["partial_shard"] is True
    assert set(report["arms"]) == {"off"}
    assert report["preregistered_arms"] == PREREG["arms"]
    assert report["arms"]["off"]["generation_trials"] == 32
    assert report["arms"]["off"]["identity"]["queries"] == 128
    assert report["fresh_hardware_used"] is False
    with pytest.raises(ValueError, match="all frozen"):
        run_phase8(
            cohort, PREREG["prompt_bank"][:1], PREREG["sampling_seeds"][:1],
            operator, FakeModel(), config, arms=["off"],
        )
    with pytest.raises(ValueError, match="exactly one"):
        run_phase8(
            cohort, PREREG["prompt_bank"][:1], PREREG["sampling_seeds"][:1],
            operator, FakeModel(), config, arms=["off", "replay"], partial_shard=True,
        )


def test_native_arm_cli_rejects_unpinned_release_before_checkpoint_load(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/run_quantum_buddy_phase8_shadow.py"),
         "--arm", "off", "--checkpoint", str(tmp_path),
         "--expected-sha256", "a" * 64,
         "--confirm-cpu-intensive", "--output", str(tmp_path / "results")],
        cwd=root, capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode != 0
    assert "immutable release" in result.stderr
    assert not (tmp_path / "results" / "report.json").exists()


def test_aggregate_refuses_partial_or_synthetic_placeholder_reports(tmp_path):
    for mode in PREREG["arms"][:-1]:
        (tmp_path / ("phase8-14k-" + mode)).mkdir()
    with pytest.raises(ValueError, match="five"):
        assemble(tmp_path, PREREG)
    (tmp_path / "phase8-14k-replay").mkdir()
    with pytest.raises(ValueError, match="incomplete"):
        assemble(tmp_path, PREREG)
