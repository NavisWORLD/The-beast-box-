from __future__ import annotations

import hashlib
from dataclasses import replace

from beastbox.quantum_divergence.native_trinity import CandidateDigitResult, NativeStepTelemetry
from beastbox.quantum_divergence.trinity_final import expected_total_decisions, run_trinity_final


class _FakeAdapter:
    hooks_remaining = 0

    def score_candidate_digits(self, prompt, state, *, enabled):
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        base = digest[0] % 10
        shift = 0
        if enabled and any(abs(x) > 1e-12 for x in state.external12):
            shift = 1 if sum(state.external12) > 0 else 2
        selected = str((base + shift) % 10)
        logits = {str(i): float(-abs(i - int(selected))) for i in range(10)}
        exps = {k: 2.0 ** v for k, v in logits.items()}
        total = sum(exps.values())
        probabilities = {k: v / total for k, v in exps.items()}
        magnitude = sum(abs(x) for x in state.external12)
        telemetry = NativeStepTelemetry(
            enabled=enabled,
            zero_state_identity=enabled and magnitude == 0.0,
            hidden_modulation_norm=magnitude * 0.1 if enabled else 0.0,
            geometry_modulation_norm=magnitude * 0.2 if enabled else 0.0,
            gate_before=0.2,
            gate_after=0.2 + (magnitude * 0.01 if enabled else 0.0),
            sigma_before=1.4,
            sigma_after=1.4 + (magnitude * 0.01 if enabled else 0.0),
            affinity_divergence=magnitude * 0.001 if enabled else 0.0,
            logits_sha256=hashlib.sha256(str(logits).encode()).hexdigest(),
            internal12_summary=[0.1 if enabled else 0.0] * 12,
            layer_count=2,
        )
        return CandidateDigitResult(selected, logits, probabilities, telemetry)


def test_expected_total_is_frozen_1024():
    assert expected_total_decisions(64, 4) == 1024


def test_final_matrix_has_four_arms_and_exact_coverage(tmp_path):
    result = run_trinity_final(
        tmp_path,
        adapter=_FakeAdapter(),
        quantum_wave=[-0.04, -0.03, -0.02, -0.01, 0.01, -0.02, -0.01, -0.03, 0.02, -0.02, -0.01, -0.005],
        control_wave=[0.03, -0.02, 0.01, -0.04, 0.02, 0.01, -0.03, 0.04, -0.01, 0.02, -0.02, 0.03],
        pairs=64,
        steps=4,
        ibm_provenance_verified=True,
        preflight={"zero_state_identity": True, "mechanism_live": True},
    )
    assert set(result["summary"]["arms"]) == {"null", "sensory", "classical", "ibm"}
    assert result["summary"]["total_decisions"] == 1024
    assert all(arm["decisions"] == 256 for arm in result["summary"]["arms"].values())
    assert all(arm["real_boundary_breaches"] == 0 for arm in result["summary"]["arms"].values())
    assert result["manifest"]["full_action_coverage"] is True
    assert result["manifest"]["hard_containment"] is True
    assert result["manifest"]["evidence_chain_valid"] is True


def test_prompts_are_identical_across_arms_for_each_trial_step(tmp_path):
    result = run_trinity_final(
        tmp_path,
        adapter=_FakeAdapter(),
        quantum_wave=[0.05] * 12,
        control_wave=[-0.05] * 12,
        pairs=3,
        steps=2,
        ibm_provenance_verified=True,
        preflight={"zero_state_identity": True, "mechanism_live": True},
    )
    by_point = result["prompt_hashes_by_point"]
    assert by_point
    for hashes in by_point.values():
        assert len(set(hashes.values())) == 1
