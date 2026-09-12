from __future__ import annotations

import copy
import math

import pytest


def sample_packet() -> dict[str, list[float]]:
    return {
        "phase12": [0.12, 0.91, -0.21, 0.74, 0.33, 0.62, -0.44, 0.53, 0.25, 0.48, -0.17, 0.39],
        "dynamic12": [0.18, 0.72, -0.15, 0.66, 0.29, 0.57, -0.35, 0.49, 0.21, 0.43, -0.11, 0.36],
        "hebbian24": [0.03 * (i - 11) for i in range(24)],
        "chaos18": [0.07 * (i - 8) for i in range(18)],
    }


def seeds() -> dict[str, int]:
    return {
        "pair_permutation": 1103,
        "hebbian_permutation": 2207,
        "chaos_permutation": 3301,
        "randomization": 4409,
    }


def test_bridge_packet_exact_lengths():
    from beastbox.cst12_physics_probe_003 import validate_bridge_packet

    validate_bridge_packet(sample_packet())
    broken = sample_packet()
    broken["dynamic12"] = broken["dynamic12"][:-1]
    with pytest.raises(ValueError):
        validate_bridge_packet(broken)


def test_bridge_rejects_nonfinite():
    from beastbox.cst12_physics_probe_003 import validate_bridge_packet

    broken = sample_packet()
    broken["phase12"][2] = float("nan")
    with pytest.raises(ValueError):
        validate_bridge_packet(broken)


def test_circular_boundary():
    from beastbox.cst12_physics_probe_003 import circular_mean, wrap_phase

    assert abs(abs(circular_mean([3.13, -3.13])) - math.pi) < 0.02
    assert -math.pi <= wrap_phase(9.0) <= math.pi


@pytest.mark.parametrize(
    "family,index",
    [("phase12", 0), ("dynamic12", 0), ("hebbian24", 0), ("chaos18", 0)],
)
def test_full_arm_uses_every_component_family(family: str, index: int):
    from beastbox.cst12_physics_probe_003 import compile_arm_parameters

    base = sample_packet()
    p0 = compile_arm_parameters(base, "FULL_CST", seeds())
    changed = copy.deepcopy(base)
    changed[family][index] += 0.123
    p1 = compile_arm_parameters(changed, "FULL_CST", seeds())
    assert p0 != p1


def test_unknown_arm_and_missing_seed_fail_closed():
    from beastbox.cst12_physics_probe_003 import compile_arm_parameters

    with pytest.raises(ValueError):
        compile_arm_parameters(sample_packet(), "NOT_AN_ARM", seeds())
    with pytest.raises(ValueError):
        compile_arm_parameters(sample_packet(), "PAIR_PERMUTE", {})


def test_mirror_uses_same_preparation_and_inverse_readout():
    from beastbox.cst12_physics_probe_003 import compile_arm_parameters

    full = compile_arm_parameters(sample_packet(), "FULL_CST", seeds())
    mirror = compile_arm_parameters(sample_packet(), "MIRROR_CAL", seeds())
    for key in ("alpha", "theta", "chaos_xyz", "lambda_rzz"):
        assert mirror[key] == full[key]
    assert mirror["readout_layer_1"] == full["alpha"]
    assert mirror["readout_layer_2"] == [-v for v in full["alpha"]]


def test_block_effect_uses_six_ablations_and_not_mirror():
    from beastbox.cst12_physics_probe_003 import block_effect

    residuals = {
        "FULL_CST": 0.2,
        "PAIR_SWAP": 0.0,
        "PAIR_PERMUTE": 0.0,
        "HEBBIAN_SHUFFLE": 0.0,
        "CHAOS_SHUFFLE": 0.0,
        "PHI_ABLATE": 0.0,
        "DYNAMIC_FREEZE": 0.0,
        "MIRROR_CAL": 2.9,
    }
    assert abs(block_effect(residuals) - 0.2) < 1e-12


def test_stage_randomization_is_deterministic():
    from beastbox.cst12_physics_probe_003 import analyze_stage

    blocks = []
    for i in range(12):
        eps = {
            "FULL_CST": 0.02 + i * 1e-4,
            "PAIR_SWAP": 0.0,
            "PAIR_PERMUTE": 0.001,
            "HEBBIAN_SHUFFLE": -0.001,
            "CHAOS_SHUFFLE": 0.0005,
            "PHI_ABLATE": -0.0005,
            "DYNAMIC_FREEZE": 0.0002,
            "MIRROR_CAL": 0.0,
        }
        blocks.append({"epsilon": eps})
    a = analyze_stage(blocks, seed=991, randomizations=1000)
    b = analyze_stage(blocks, seed=991, randomizations=1000)
    assert a == b
    assert a["randomizations"] == 1000
    assert a["effect"] > 0


def test_qiskit_topology_and_exact_hadamard_contract():
    pytest.importorskip("qiskit")
    from qiskit.quantum_info import Statevector
    from beastbox.cst12_physics_probe_003 import (
        ARM_ORDER,
        build_probe_circuit,
        exact_qm_prediction,
    )

    packet = sample_packet()
    sd = seeds()
    fingerprints = []
    for arm in ARM_ORDER:
        qc_x = build_probe_circuit(packet, arm, "X", sd, measure=False)
        qc_y = build_probe_circuit(packet, arm, "Y", sd, measure=False)
        assert qc_x.num_qubits == 7
        assert qc_y.num_qubits == 7
        fingerprints.append(tuple(sorted(qc_x.count_ops().items())))
        z = exact_qm_prediction(packet, arm, sd)
        assert math.isfinite(z.real) and math.isfinite(z.imag)
        assert abs(z) <= 1.0 + 1e-12

        sx = Statevector.from_instruction(qc_x)
        sy = Statevector.from_instruction(qc_y)
        px = sx.probabilities([6])
        py = sy.probabilities([6])
        ex = float(px[0] - px[1])
        ey = float(py[0] - py[1])
        assert abs(ex - z.real) < 1e-10
        assert abs(ey - z.imag) < 1e-10

    assert len(set(fingerprints)) == 1
    mirror = exact_qm_prediction(packet, "MIRROR_CAL", sd)
    assert abs(math.atan2(mirror.imag, mirror.real)) < 1e-12
