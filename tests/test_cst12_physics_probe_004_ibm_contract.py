from __future__ import annotations

import inspect
from types import SimpleNamespace

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


def test_compiler_api_has_no_arm_argument_and_binds_after_transpile():
    pytest.importorskip("qiskit")
    from qiskit.providers.fake_provider import GenericBackendV2

    from beastbox.cst12_physics_probe_004 import ALL_ARMS
    from scripts.run_cst12_physics_probe_004_ibm import (
        bind_compiled_template,
        compile_template_for_layout,
        native_fingerprint,
    )

    assert "arm" not in inspect.signature(compile_template_for_layout).parameters
    backend = GenericBackendV2(
        num_qubits=7,
        basis_gates=["id", "rz", "sx", "x", "cz"],
        coupling_map=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 5), (5, 4), (4, 3), (3, 2), (2, 1), (1, 0)],
        seed=1234,
    )
    compiled = compile_template_for_layout(backend, "X", list(range(7)), transpile_seed=918273)
    assert compiled.parameters
    frozen = native_fingerprint(compiled)
    assert frozen["two_qubit_sequence"]

    for arm in ALL_ARMS:
        bound = bind_compiled_template(compiled, sample_packet(), arm, seeds())
        assert not bound.parameters
        assert native_fingerprint(bound) == frozen


def test_x_and_y_templates_each_have_one_stable_native_fingerprint():
    pytest.importorskip("qiskit")
    from qiskit.providers.fake_provider import GenericBackendV2

    from beastbox.cst12_physics_probe_004 import ALL_ARMS
    from scripts.run_cst12_physics_probe_004_ibm import bind_compiled_template, compile_template_for_layout, native_fingerprint

    backend = GenericBackendV2(num_qubits=7, seed=99)
    for basis in ("X", "Y"):
        compiled = compile_template_for_layout(backend, basis, list(range(7)), transpile_seed=7)
        expected = native_fingerprint(compiled)
        got = {
            str(native_fingerprint(bind_compiled_template(compiled, sample_packet(), arm, seeds())))
            for arm in ALL_ARMS
        }
        assert got == {str(expected)}


class TinyBackend:
    def __init__(self, name: str, pending: int, operational: bool = True, qubits: int = 7):
        self.name = name
        self.num_qubits = qubits
        self.simulator = False
        self._pending = pending
        self._operational = operational

    def status(self):
        return SimpleNamespace(pending_jobs=self._pending, operational=self._operational)


def test_backend_selection_requires_two_distinct_real_backends():
    from scripts.run_cst12_physics_probe_004_ibm import select_stage_backends

    chosen = select_stage_backends([TinyBackend("b", 5), TinyBackend("a", 2), TinyBackend("off", 0, operational=False)])
    assert chosen["discovery"].name == "a"
    assert chosen["replication"].name == "b"
    assert chosen["discovery"].name != chosen["replication"].name

    with pytest.raises(RuntimeError, match="two distinct"):
        select_stage_backends([TinyBackend("only", 0)])


def test_hardware_approval_must_match_frozen_prereg_and_implementation():
    from scripts.run_cst12_physics_probe_004_ibm import validate_hardware_approval

    prereg = "a" * 64
    freeze = "b" * 40
    receipt = {
        "schema": "cst12-physics-probe-004-hardware-approval-v1",
        "approved": True,
        "preregistration_sha256": prereg,
        "implementation_freeze_commit": freeze,
    }
    validate_hardware_approval(receipt, prereg_sha=prereg, freeze_sha=freeze)

    broken = dict(receipt, preregistration_sha256="c" * 64)
    with pytest.raises(ValueError, match="preregistration"):
        validate_hardware_approval(broken, prereg_sha=prereg, freeze_sha=freeze)

    broken = dict(receipt, approved=False)
    with pytest.raises(ValueError, match="approved"):
        validate_hardware_approval(broken, prereg_sha=prereg, freeze_sha=freeze)


def test_balanced_plan_contains_every_arm_and_basis_once_per_block():
    from beastbox.cst12_physics_probe_004 import ALL_ARMS
    from scripts.run_cst12_physics_probe_004_ibm import balanced_block_plan, chunk_block_plan

    layouts = [list(range(i, i + 7)) for i in range(4)]
    plan = balanced_block_plan("discovery", layouts, arm_order_seed=7788)
    assert len(plan) == 32
    expected = {(arm, basis) for arm in ALL_ARMS for basis in ("X", "Y")}
    for block in plan:
        got = {(row["arm"], row["basis"]) for row in block["pub_order"]}
        assert got == expected
        assert len(block["pub_order"]) == 26
    chunks = chunk_block_plan(plan)
    assert len(chunks) == 8
    assert all(len(chunk) == 4 for chunk in chunks)


def test_template_cache_compiles_exactly_once_per_layout_basis(monkeypatch):
    import scripts.run_cst12_physics_probe_004_ibm as runner

    calls = []

    class FakeCircuit:
        num_qubits = 7
        num_clbits = 1
        parameters = {"p"}
        data = []
        def depth(self): return 1
        def size(self): return 1

    def fake_compile(backend, basis, layout, *, transpile_seed):
        calls.append((basis, tuple(layout), transpile_seed))
        return FakeCircuit()

    monkeypatch.setattr(runner, "compile_template_for_layout", fake_compile)
    monkeypatch.setattr(runner, "native_fingerprint", lambda qc: {
        "num_qubits": 7, "num_clbits": 1, "depth": 1, "size": 1,
        "operation_sequence": [], "two_qubit_sequence": [{"name": "cz", "qubits": [0, 1]}],
    })
    layouts = [list(range(i, i + 7)) for i in range(4)]
    cache, audit = runner.build_template_cache(object(), "discovery", layouts, prereg_sha="a" * 64)
    assert len(calls) == 8
    assert len(cache) == 8
    assert len(audit) == 8
    assert len({(basis, layout) for basis, layout, _seed in calls}) == 8


def test_workload_arithmetic_is_frozen():
    import scripts.run_cst12_physics_probe_004_ibm as runner

    assert runner.PUBS_PER_BLOCK == 26
    assert runner.BLOCKS_PER_STAGE == 32
    assert runner.JOBS_PER_STAGE == 8
    assert 2 * runner.BLOCKS_PER_STAGE * runner.PUBS_PER_BLOCK == 1664
    assert 1664 * runner.SHOTS_PER_PUB == 6_815_744
