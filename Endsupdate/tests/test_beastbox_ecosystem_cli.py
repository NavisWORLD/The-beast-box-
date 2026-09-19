from __future__ import annotations

from beastbox.ecosystem import build_ecosystem_parser, ecosystem_status


def test_parser_exposes_public_ecosystem_commands():
    parser = build_ecosystem_parser()
    actions = [a for a in parser._actions if getattr(a, "choices", None)]
    choices = set().union(*(set(a.choices) for a in actions))
    assert {"r12", "zeref", "coder", "verify", "kit"}.issubset(choices)


def test_ecosystem_status_pins_active_lineage():
    status = ecosystem_status()
    assert status["active_lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert status["active_checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert status["durable_memory_record_count"] == 352
    assert status["r12_state"]["sequence"] == 4
