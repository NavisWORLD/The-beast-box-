#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, Sequence

from beastbox.cst12_physics_probe_004 import _parameter_values
from beastbox.cst12_physics_probe_005 import (
    basis_order_for_block,
    binding_for_slot,
    block_slot_plan,
    slot_source_arm,
)
from scripts.run_cst12_physics_probe_004_ibm import (
    compile_template_for_layout,
    native_fingerprint,
    select_connected_layouts,
    select_stage_backends,
)

BLOCKS_PER_STAGE = 32
SHOTS_PER_PUB = 4096
LOGICAL_SLOTS_PER_BLOCK = 20
PUBS_PER_BLOCK = LOGICAL_SLOTS_PER_BLOCK * 2
BLOCKS_PER_JOB = 4
JOBS_PER_STAGE = 8
MIN_LAYOUTS = 4
PLANNED_PUBS = PUBS_PER_BLOCK * BLOCKS_PER_STAGE * 2
PLANNED_SHOTS = PLANNED_PUBS * SHOTS_PER_PUB


def _domain_seed(seed: int, text: str) -> int:
    return int(hashlib.sha256(f"cst12-probe005|{int(seed)}|{text}".encode()).hexdigest()[:16], 16)


def bind_compiled_slot(
    compiled_template: Any,
    packet: Mapping[str, Sequence[float]],
    logical_slot: str,
    seeds: Mapping[str, int],
):
    before = native_fingerprint(compiled_template)
    binding = binding_for_slot(packet, logical_slot, seeds)
    values = _parameter_values(binding)
    missing = sorted(p.name for p in compiled_template.parameters if p.name not in values)
    if missing:
        raise ValueError(f"Probe 005 compiled template has unknown parameters: {missing}")
    bound = compiled_template.assign_parameters(
        {p: values[p.name] for p in compiled_template.parameters}, inplace=False
    )
    if bound.parameters:
        raise RuntimeError("Probe 005 slot binding left unresolved parameters")
    after = native_fingerprint(bound)
    if after != before:
        raise RuntimeError("Probe 005 parameter binding changed native topology")
    return bound


def compile_template_cache(
    backend: Any,
    layouts: Sequence[Sequence[int]],
    *,
    transpile_seed_root: int,
    compiler: Callable[..., Any] = compile_template_for_layout,
) -> dict[tuple[tuple[int, ...], str], Any]:
    cache: dict[tuple[tuple[int, ...], str], Any] = {}
    for raw_layout in layouts:
        layout = tuple(int(q) for q in raw_layout)
        if len(layout) != 7 or len(set(layout)) != 7:
            raise ValueError("Probe 005 layout must contain seven distinct qubits")
        for basis in ("X", "Y"):
            key = (layout, basis)
            if key in cache:
                continue
            seed = _domain_seed(int(transpile_seed_root), f"compile:{','.join(map(str, layout))}:{basis}")
            cache[key] = compiler(backend, basis, layout, transpile_seed=seed)
    return cache


def balanced_block_plan(
    stage: str,
    layouts: Sequence[Sequence[int]],
    *,
    arm_order_seed: int,
) -> list[dict[str, Any]]:
    if stage not in {"discovery", "replication"}:
        raise ValueError("unknown Probe 005 stage")
    if len(layouts) < MIN_LAYOUTS:
        raise ValueError("Probe 005 requires at least four layouts")

    plan: list[dict[str, Any]] = []
    for block_id in range(BLOCKS_PER_STAGE):
        slots = block_slot_plan(block_id, int(arm_order_seed))
        basis_order = basis_order_for_block(block_id)
        pubs: list[dict[str, Any]] = []
        for pair_index, slot in enumerate(slots):
            time_coordinate = pair_index / float(LOGICAL_SLOTS_PER_BLOCK - 1)
            for basis in basis_order:
                pubs.append(
                    {
                        "logical_slot": slot,
                        "source_arm": slot_source_arm(slot),
                        "basis": basis,
                        "slot_pair_index": pair_index,
                        "time_coordinate": time_coordinate,
                    }
                )
        if len(pubs) != PUBS_PER_BLOCK:
            raise AssertionError("Probe 005 block schedule has wrong PUB count")
        layout_index = block_id % len(layouts)
        plan.append(
            {
                "stage": stage,
                "block_id": block_id,
                "layout": [int(q) for q in layouts[layout_index]],
                "layout_index": layout_index,
                "basis_pair_order": list(basis_order),
                "pub_order": pubs,
            }
        )
    return plan


def chunk_block_plan(
    plan: Sequence[Mapping[str, Any]], *, blocks_per_job: int = BLOCKS_PER_JOB
) -> list[list[dict[str, Any]]]:
    if int(blocks_per_job) <= 0:
        raise ValueError("blocks_per_job must be positive")
    chunks = [
        [dict(row) for row in plan[i : i + int(blocks_per_job)]]
        for i in range(0, len(plan), int(blocks_per_job))
    ]
    if len(plan) == BLOCKS_PER_STAGE and int(blocks_per_job) == BLOCKS_PER_JOB:
        if len(chunks) != JOBS_PER_STAGE or any(len(chunk) != BLOCKS_PER_JOB for chunk in chunks):
            raise AssertionError("Probe 005 schedule must contain eight four-block jobs per stage")
    return chunks


def validate_hardware_approval(
    receipt: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str
) -> None:
    if str(receipt.get("schema", "")) != "cst12-physics-probe-005-hardware-approval-v1":
        raise ValueError("Probe 005 hardware approval schema mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("Probe 005 hardware approval is not approved")
    expected_prereg = str(prereg_sha)
    expected_freeze = str(freeze_sha)
    if len(expected_prereg) != 64 or len(expected_freeze) != 40:
        raise ValueError("Probe 005 protected hash lengths are invalid")
    try:
        int(expected_prereg, 16)
        int(expected_freeze, 16)
    except ValueError as exc:
        raise ValueError("Probe 005 protected hashes must be hexadecimal") from exc
    if str(receipt.get("preregistration_sha256", "")) != expected_prereg:
        raise ValueError("Probe 005 hardware approval preregistration hash mismatch")
    if str(receipt.get("implementation_freeze_commit", "")) != expected_freeze:
        raise ValueError("Probe 005 hardware approval implementation-freeze hash mismatch")
