from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path("scripts/run_zeref_origin_seed_chat.py")
ORIGIN_SEED_SHA = "a" * 64
LEDGER_TIP = "b" * 64


def load_module():
    assert SCRIPT.is_file(), "hardware Origin Seed chat runner is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_origin_seed_chat", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_turn_seed_is_deterministic_and_domain_separated():
    module = load_module()
    one = module.derive_turn_seed(ORIGIN_SEED_SHA, LEDGER_TIP, 1)
    assert one == module.derive_turn_seed(ORIGIN_SEED_SHA, LEDGER_TIP, 1)
    assert one != module.derive_turn_seed(ORIGIN_SEED_SHA, LEDGER_TIP, 2)
    assert one != module.derive_turn_seed(ORIGIN_SEED_SHA, "c" * 64, 1)
    assert 0 <= one < 2**63


def test_wire_prompt_is_native_context_bounded_and_contains_origin_state():
    module = load_module()
    recalled = [{"text": "Dad and Zeref remember the ledger together."}]
    wire = module.build_wire_prompt(
        dad_text="Tell me what the new hardware seed means to you.",
        recalled=recalled,
        origin_seed_sha256=ORIGIN_SEED_SHA,
        block=128,
    )
    assert len(wire) <= 128
    assert "OH:" + ORIGIN_SEED_SHA[:12] in wire
    assert "Dad:" in wire and wire.endswith("Zeref:")


def test_runner_is_inference_only_and_appends_verified_hardware_provenance():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22" in text
    assert "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6" in text
    assert "DadSonLedger" in text and "restore_snapshot" in text
    assert "origin_seed_sha256" in text and "source_audio_sha256" in text
    assert "ibm_quantum_hardware_measurement" in text
    assert "zerefs-heartbeat-mustard-seed" in text
    assert '"raw_model_output_promoted_to_training": False' in text
    assert "run_d001_stage.py" not in text
    assert "optimizer" not in text.lower()
    assert "proxy_generated_by" in text and "Luna" in text
    assert "output_preserved_verbatim" in text
