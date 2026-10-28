from __future__ import annotations

import pytest

from beastbox.r12_physics_probe import ARM_ORDER
from scripts.run_r12_physics_probe_ibm import (
    _is_payload_size_error,
    balanced_block_plan,
    chunk_block_plan,
    find_connected_paths,
    sanitize_counts,
    select_stage_backends_with_paths,
)


class Status:
    def __init__(self, operational=True, pending_jobs=0):
        self.operational=operational; self.pending_jobs=pending_jobs


class Coupling:
    def __init__(self, edges): self._edges=edges
    def get_edges(self): return self._edges


class Backend:
    def __init__(self,name,pending=0):
        self.name=name; self.num_qubits=20; self.coupling_map=Coupling([(i,i+1) for i in range(19)]); self._pending=pending
    def status(self): return Status(True,self._pending)
    def properties(self): return None


def test_connected_path_finder_returns_twelve_unique_qubits():
    paths=find_connected_paths([(i,i+1) for i in range(20)],length=12,limit=10)
    assert len(paths)>=4
    assert all(len(p)==12 and len(set(p))==12 for p in paths)


def test_balanced_plan_has_24_blocks_four_paths_two_orientations():
    paths=[tuple(range(offset,offset+12)) for offset in range(4)]
    plan=balanced_block_plan("discovery",paths,arm_order_seed=123)
    assert len(plan)==24
    assert set(v["block_id"] for v in plan)==set(range(24))
    assert all(set(v["arm_order"])==set(ARM_ORDER) for v in plan)
    assert sum(v["orientation"]=="forward" for v in plan)==12
    assert sum(v["orientation"]=="reverse" for v in plan)==12


def test_chunking_targets_three_eight_block_jobs():
    paths=[tuple(range(offset,offset+12)) for offset in range(4)]
    chunks=chunk_block_plan(balanced_block_plan("discovery",paths,arm_order_seed=1),blocks_per_job=8)
    assert [len(c) for c in chunks]==[8,8,8]


def test_backend_selection_prefers_second_backend_for_replication():
    selected=select_stage_backends_with_paths([Backend("b",2),Backend("a",1)])
    assert selected["discovery"].name=="a"
    assert selected["replication"].name=="b"
    assert selected["independent_backend_replication"] is True
    assert len(selected["discovery_paths"])==4


def test_counts_require_exact_4096_and_twelve_bits():
    assert sanitize_counts({"0"*12:4096})["0"*12]==4096
    with pytest.raises(ValueError): sanitize_counts({"0"*12:4095})
    with pytest.raises(ValueError): sanitize_counts({"0"*11:4096})


def test_payload_error_classifier_only_supports_operational_rechunking():
    assert _is_payload_size_error(RuntimeError("PUB payload exceeds maximum limit")) is True
    assert _is_payload_size_error(RuntimeError("authentication failed")) is False
