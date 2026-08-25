import inspect
import json
from pathlib import Path

import pytest

from beastbox.cst12_physics_probe_004 import build_parameterized_template
from scripts.run_cst12_physics_probe_005_ibm import (
    BLOCKS_PER_JOB,
    BLOCKS_PER_STAGE,
    JOBS_PER_STAGE,
    PLANNED_PUBS,
    PLANNED_SHOTS,
    PUBS_PER_BLOCK,
    SHOTS_PER_PUB,
    balanced_block_plan,
    bind_compiled_slot,
    chunk_block_plan,
    compile_template_cache,
    compile_template_for_layout,
    native_fingerprint,
    validate_hardware_approval,
)


FROZEN_SEEDS = {
    "chaos_permutation": 8032230230896211285,
    "hebbian_permutation": 2311865949987907916,
    "pair_permutation": 10661387436821034376,
    "randomization": 7431857563000781786,
    "synthetic": 3191325276912663137,
}


def _packet():
    return json.loads(
        Path("experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json").read_text()
    )["bridge_packet"]


def test_compile_api_cannot_receive_arm_or_slot():
    params = inspect.signature(compile_template_for_layout).parameters
    assert "arm" not in params
    assert "slot" not in params
    assert "logical_slot" not in params


def test_compile_cache_calls_compiler_once_per_layout_basis():
    calls = []

    def fake_compiler(backend, basis, layout, *, transpile_seed):
        calls.append((basis, tuple(layout), transpile_seed))
        return (basis, tuple(layout), transpile_seed)

    layouts = [(0, 1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12, 13)]
    cache = compile_template_cache(object(), layouts, transpile_seed_root=123, compiler=fake_compiler)
    assert len(cache) == 4
    assert len(calls) == 4
    assert len(set((basis, layout) for basis, layout, _ in calls)) == 4


def test_binding_preserves_symbolic_template_native_fingerprint_for_all_slot_types():
    packet = _packet()
    for basis in ("X", "Y"):
        template = build_parameterized_template(basis, measure=True)
        before = native_fingerprint(template)
        for slot in (
            "PRE_REF_0",
            "PRE_MIRROR_PM",
            "FULL_CST",
            "PAIR_SWAP",
            "MID_REF_HOLDOUT",
            "POST_MIRROR_MP",
            "POST_REF_0",
        ):
            bound = bind_compiled_slot(template, packet, slot, FROZEN_SEEDS)
            assert not bound.parameters
            assert native_fingerprint(bound) == before


def test_balanced_stage_schedule_has_40_pubs_per_block_adjacent_basis_pairs_and_eight_jobs():
    layouts = [
        (0, 1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12, 13),
        (14, 15, 16, 17, 18, 19, 20),
        (21, 22, 23, 24, 25, 26, 27),
    ]
    plan = balanced_block_plan("discovery", layouts, arm_order_seed=777)
    assert len(plan) == BLOCKS_PER_STAGE == 32
    for block in plan:
        pubs = block["pub_order"]
        assert len(pubs) == PUBS_PER_BLOCK == 40
        for pair_index in range(20):
            a, b = pubs[2 * pair_index : 2 * pair_index + 2]
            assert a["logical_slot"] == b["logical_slot"]
            assert a["slot_pair_index"] == b["slot_pair_index"] == pair_index
            assert {a["basis"], b["basis"]} == {"X", "Y"}
            assert a["time_coordinate"] == pytest.approx(pair_index / 19.0)
            assert b["time_coordinate"] == pytest.approx(pair_index / 19.0)
        expected_basis = ("X", "Y") if block["block_id"] % 2 == 0 else ("Y", "X")
        assert tuple(pubs[0]["basis"] for _ in [0]) + (pubs[1]["basis"],) == expected_basis

    chunks = chunk_block_plan(plan)
    assert BLOCKS_PER_JOB == 4
    assert JOBS_PER_STAGE == 8
    assert len(chunks) == 8
    assert all(len(chunk) == 4 for chunk in chunks)
    assert SHOTS_PER_PUB == 4096
    assert PLANNED_PUBS == 2560
    assert PLANNED_SHOTS == 10485760


def test_hardware_approval_is_bound_to_exact_prereg_and_freeze_hashes():
    prereg = "a" * 64
    freeze = "b" * 40
    receipt = {
        "schema": "cst12-physics-probe-005-hardware-approval-v1",
        "approved": True,
        "preregistration_sha256": prereg,
        "implementation_freeze_commit": freeze,
    }
    validate_hardware_approval(receipt, prereg_sha=prereg, freeze_sha=freeze)
    bad = dict(receipt)
    bad["preregistration_sha256"] = "c" * 64
    with pytest.raises(ValueError):
        validate_hardware_approval(bad, prereg_sha=prereg, freeze_sha=freeze)
