from __future__ import annotations

import copy
from pathlib import Path

import pytest

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter
from scripts.run_zeref_r12_rho_sweep import (
    FIXED_ROUTER_NOW,
    FROZEN_PROMPT,
    RHO_GRID,
    build_sweep_wire_prompt,
    force_probe_rho,
    rank_with_frozen_clock,
    sanitize_for_frozen_tokenizer,
)

PARENT = "b" * 64


def test_rho_grid_is_fixed_monotonic_and_bounded():
    assert RHO_GRID == (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    assert all(0.0 <= value <= 1.0 for value in RHO_GRID)
    assert list(RHO_GRID) == sorted(set(RHO_GRID))


def test_force_probe_rho_changes_only_coupling_plus_commit_hash():
    base = initial_r12_state()
    probe = force_probe_rho(base, 0.6)

    assert probe["vector"]["reality_coupling"] == 0.6
    assert probe["state_sha256"] != base["state_sha256"]
    assert probe["last_measured_reality_coupling"] == base["last_measured_reality_coupling"]

    left = copy.deepcopy(base)
    right = copy.deepcopy(probe)
    left.pop("state_sha256")
    right.pop("state_sha256")
    left["vector"]["reality_coupling"] = 0.6
    assert left == right

    with pytest.raises(ValueError):
        force_probe_rho(base, -0.01)
    with pytest.raises(ValueError):
        force_probe_rho(base, 1.01)


def test_sweep_harness_freezes_router_wall_clock(tmp_path: Path):
    assert FIXED_ROUTER_NOW == 2_000_000_000.0
    ledger = DadSonLedger(tmp_path / "x.sqlite3", tmp_path / "x.jsonl", parent_sha256=PARENT)
    ledger.append_experience(actor="old", text="preserved evidence memory", kind="dialogue", session_id="s")
    router = RefractiveMemoryRouter(ledger)
    state = initial_r12_state()
    kwargs = dict(query="evidence", sequence=0, dyn12=[0.0] * 12, r12_state=state, limit=1)
    first = rank_with_frozen_clock(router, **kwargs)
    second = rank_with_frozen_clock(router, **kwargs)
    assert first == second
    ledger.close()


def test_supplement_is_sanitized_to_frozen_tokenizer_vocabulary():
    stoi = {"a": 0, "b": 1, " ": 2}
    assert sanitize_for_frozen_tokenizer("a💀b", stoi) == "a b"
    assert sanitize_for_frozen_tokenizer("💀💀", stoi) == ""


def test_frozen_wire_contains_no_rho_or_r12_hash_text():
    live_alias = "LSRC E1 d54=0123456789ab"
    supplement = "old memory about preserved evidence and measurement"
    wire = build_sweep_wire_prompt(
        prompt=FROZEN_PROMPT,
        live_alias=live_alias,
        supplement_text=supplement,
        block=128,
    )
    assert len(wire) <= 128
    assert FROZEN_PROMPT in wire
    assert live_alias in wire
    assert "rho=" not in wire.lower()
    assert "r12=" not in wire.lower()
    assert "0.6" not in wire


def test_same_retrieval_yields_identical_wire_independent_of_probe_rho():
    live_alias = "LSRC E1 d54=0123456789ab"
    supplement = "same selected historical memory"
    wires = [
        build_sweep_wire_prompt(
            prompt=FROZEN_PROMPT,
            live_alias=live_alias,
            supplement_text=supplement,
            block=128,
        )
        for _rho in RHO_GRID
    ]
    assert len(set(wires)) == 1
