from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

# Quantum archive is already consumed; these tests define the non-quantum continuation pulse.
FINAL_QUANTUM = "b0ef430e58a0f4c02f95cbf5fd285415914f159b1f5ffd26c6d26293c44bbb90"
LEDGER_TIP = "96a9d6be43758a9571ba91c3dbcdd633011936cc958581c0d07e18e991f0ec39"


def _module():
    path = Path("scripts/build_zeref_synaptic_continuation.py")
    assert path.exists(), "synaptic continuation builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_synaptic_continuation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_continuation_is_rooted_in_final_quantum_and_current_ledger_tip(tmp_path):
    module = _module()
    out = tmp_path / "pulse.json"
    report = module.build_continuation(
        final_quantum_state=FINAL_QUANTUM,
        ledger_tip=LEDGER_TIP,
        count=4,
        out_path=out,
    )
    assert report["schema"] == "zeref-synaptic-continuation-v1"
    assert report["root_quantum_state_sha256"] == FINAL_QUANTUM
    assert report["root_ledger_tip_sha256"] == LEDGER_TIP
    assert report["source_class"] == "deterministic-local-continuation"
    assert report["new_quantum_entropy"] is False
    assert report["recycles_archived_quantum_beats"] is False
    assert report["hold_quantum_root_until_new_verified_result"] is True
    assert len(report["pulses"]) == 4


def test_pulses_are_deterministic_domain_separated_and_chained(tmp_path):
    module = _module()
    a = module.build_continuation(final_quantum_state=FINAL_QUANTUM, ledger_tip=LEDGER_TIP, count=3, out_path=tmp_path / "a.json")
    b = module.build_continuation(final_quantum_state=FINAL_QUANTUM, ledger_tip=LEDGER_TIP, count=3, out_path=tmp_path / "b.json")
    assert [p["state_sha256"] for p in a["pulses"]] == [p["state_sha256"] for p in b["pulses"]]
    assert len(set(p["state_sha256"] for p in a["pulses"])) == 3
    assert a["pulses"][0]["previous_pulse_sha256"] == "0" * 64
    assert a["pulses"][1]["previous_pulse_sha256"] == a["pulses"][0]["state_sha256"]
    expected0 = hashlib.sha256(
        b"ZEREF-SYNAPTIC-CONTINUATION-V1\0" +
        bytes.fromhex(FINAL_QUANTUM) + b"\0" +
        bytes.fromhex(LEDGER_TIP) + b"\0" +
        (0).to_bytes(8, "big") + b"\0" +
        bytes.fromhex("0" * 64)
    ).hexdigest()
    assert a["pulses"][0]["state_sha256"] == expected0


def test_changing_ledger_tip_changes_continuation_without_rewriting_quantum_root(tmp_path):
    module = _module()
    a = module.build_continuation(final_quantum_state=FINAL_QUANTUM, ledger_tip=LEDGER_TIP, count=1, out_path=tmp_path / "a.json")
    other_tip = "a" * 64
    b = module.build_continuation(final_quantum_state=FINAL_QUANTUM, ledger_tip=other_tip, count=1, out_path=tmp_path / "b.json")
    assert a["root_quantum_state_sha256"] == b["root_quantum_state_sha256"] == FINAL_QUANTUM
    assert a["pulses"][0]["state_sha256"] != b["pulses"][0]["state_sha256"]


def test_continuation_seed_adapter_is_auditable_but_not_labeled_quantum_entropy():
    module = _module()
    state = "f" * 64
    assert module.derive_torch_seed(state) == int(state[:16], 16) % (2**31 - 1)
