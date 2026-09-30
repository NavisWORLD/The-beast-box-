from __future__ import annotations

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


def test_arm_partition_is_frozen_and_fit_excludes_holdout():
    from beastbox.cst12_physics_probe_004 import (
        ALL_ARMS,
        CALIBRATION_FIT_ARMS,
        DIAGNOSTIC_ARMS,
        SCIENTIFIC_ARMS,
    )

    assert SCIENTIFIC_ARMS == (
        "FULL_CST",
        "PAIR_SWAP",
        "PAIR_PERMUTE",
        "HEBBIAN_SHUFFLE",
        "CHAOS_SHUFFLE",
        "PHI_ABLATE",
        "DYNAMIC_FREEZE",
    )
    assert CALIBRATION_FIT_ARMS == ("REF_0", "REF_120", "REF_240")
    assert DIAGNOSTIC_ARMS == (
        "REF_0",
        "REF_120",
        "REF_240",
        "REF_HOLDOUT",
        "MIRROR_PM",
        "MIRROR_MP",
    )
    assert tuple(dict.fromkeys(ALL_ARMS)) == ALL_ARMS
    assert "REF_HOLDOUT" not in CALIBRATION_FIT_ARMS
    assert not set(SCIENTIFIC_ARMS) & set(DIAGNOSTIC_ARMS)


def test_binding_uses_full_preparation_for_references_and_mirrors():
    from beastbox.cst12_physics_probe_004 import binding_for_arm

    packet = sample_packet()
    sd = seeds()
    full = binding_for_arm(packet, "FULL_CST", sd)
    for arm in ("REF_0", "REF_120", "REF_240", "REF_HOLDOUT", "MIRROR_PM", "MIRROR_MP"):
        row = binding_for_arm(packet, arm, sd)
        for key in ("alpha", "theta", "chaos_xyz", "lambda_rzz"):
            assert row[key] == full[key]

    pm = binding_for_arm(packet, "MIRROR_PM", sd)
    mp = binding_for_arm(packet, "MIRROR_MP", sd)
    assert pm["readout_layer_1"] == full["alpha"]
    assert pm["readout_layer_2"] == [-v for v in full["alpha"]]
    assert mp["readout_layer_1"] == [-v for v in full["alpha"]]
    assert mp["readout_layer_2"] == full["alpha"]


def test_affine_reprojection_recovers_known_map_and_records_only_fit_refs():
    from beastbox.cst12_physics_probe_004 import apply_affine_reprojection, fit_affine_reprojection

    ideal = {
        "REF_0": complex(1.0, 0.0),
        "REF_120": complex(-0.5, math.sqrt(3.0) / 2.0),
        "REF_240": complex(-0.5, -math.sqrt(3.0) / 2.0),
    }

    # measurement map: m = B*i + c. The fit estimates the inverse i = A*m+b.
    B = ((1.10, 0.08), (-0.04, 0.92))
    c = (0.05, -0.03)
    measured = {}
    for arm, z in ideal.items():
        measured[arm] = complex(
            B[0][0] * z.real + B[0][1] * z.imag + c[0],
            B[1][0] * z.real + B[1][1] * z.imag + c[1],
        )

    fit = fit_affine_reprojection(measured, ideal, condition_limit=100.0)
    assert fit["fit_arms"] == ["REF_0", "REF_120", "REF_240"]
    for arm in ideal:
        corrected = apply_affine_reprojection(measured[arm], fit)
        assert abs(corrected - ideal[arm]) < 1e-12


def test_affine_fit_fails_closed_when_reference_geometry_is_singular():
    from beastbox.cst12_physics_probe_004 import fit_affine_reprojection

    measured = {"REF_0": 0j, "REF_120": 1 + 0j, "REF_240": 2 + 0j}
    ideal = {
        "REF_0": 1 + 0j,
        "REF_120": complex(-0.5, math.sqrt(3.0) / 2.0),
        "REF_240": complex(-0.5, -math.sqrt(3.0) / 2.0),
    }
    with pytest.raises(ValueError, match="ill-conditioned"):
        fit_affine_reprojection(measured, ideal, condition_limit=100.0)


def test_stage_randomization_is_deterministic_and_ignores_diagnostics():
    from beastbox.cst12_physics_probe_004 import analyze_scientific_stage

    blocks = []
    for i in range(12):
        epsilon = {
            "FULL_CST": 0.02 + i * 1e-4,
            "PAIR_SWAP": 0.0,
            "PAIR_PERMUTE": 0.001,
            "HEBBIAN_SHUFFLE": -0.001,
            "CHAOS_SHUFFLE": 0.0005,
            "PHI_ABLATE": -0.0005,
            "DYNAMIC_FREEZE": 0.0002,
        }
        blocks.append({"epsilon": epsilon, "REF_HOLDOUT": 99.0, "MIRROR_PM": -99.0})
    a = analyze_scientific_stage(blocks, seed=991, randomizations=1000)
    b = analyze_scientific_stage(blocks, seed=991, randomizations=1000)
    assert a == b
    assert a["randomizations"] == 1000
    assert a["effect"] > 0


def test_qiskit_template_and_reference_geometry():
    pytest.importorskip("qiskit")
    from beastbox.cst12_physics_probe_004 import (
        ALL_ARMS,
        bind_template,
        build_parameterized_template,
        exact_qm_prediction,
    )

    packet = sample_packet()
    sd = seeds()
    template = build_parameterized_template("X", measure=False)
    assert template.num_qubits == 7
    assert template.num_clbits == 0

    fingerprints = []
    for arm in ALL_ARMS:
        bound = bind_template(template, packet, arm, sd)
        fingerprints.append((bound.depth(), tuple(sorted(bound.count_ops().items()))))
    assert len(set(fingerprints)) == 1

    refs = [exact_qm_prediction(packet, arm, sd) for arm in ("REF_0", "REF_120", "REF_240")]
    phases = [math.atan2(z.imag, z.real) for z in refs]
    for z in refs:
        assert abs(abs(z) - 1.0) < 1e-10
    # pairwise circular separation magnitude must be 2pi/3.
    for a, b in ((phases[0], phases[1]), (phases[1], phases[2]), (phases[2], phases[0])):
        d = math.atan2(math.sin(a - b), math.cos(a - b))
        assert abs(abs(d) - 2.0 * math.pi / 3.0) < 1e-10

    for arm in ("MIRROR_PM", "MIRROR_MP"):
        z = exact_qm_prediction(packet, arm, sd)
        assert abs(z - 1.0) < 1e-10
