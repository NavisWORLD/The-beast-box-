"""DIRECTIVE 009 — OMEGA wiring into the COSMIC control deck.

Adds real-telemetry routes to CosmicApp without changing existing routes:

/api/omega/recovery  — Directive 001 substrate map (real probe results)
/api/omega/step      — execute one organism step through the real pipeline
/api/omega/operator  — operator snapshot (queues, budgets, traces)
/api/omega/experiments — H1/H2/H3 preregistered results (nulls preserved)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def omega_recovery() -> tuple[int, dict[str, Any]]:
    from .recovery import recover_substrate_map

    return 200, recover_substrate_map(".")


def omega_step(root: str | Path, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    from .loop import OmegaLoop

    text = body.get("text", "")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8192:
        return 400, {"error": "omega step text must contain 1..8192 characters"}
    loop = OmegaLoop(root)
    try:
        trace = loop.step({"schema": "sensor-event-v1", "source": "text", "text": text})
        return 200, {
            "response": trace.response,
            "tool_result": trace.tool_result,
            "stages": trace.stages,
            "state_hash": trace.state_hash,
            "inspection": loop.inspect(),
        }
    finally:
        loop.close()


def omega_experiments(root: str | Path) -> tuple[int, dict[str, Any]]:
    from .experiments import (
        run_h1_model_independence,
        run_h2_adaptive_advantage,
        run_h3_self_correction,
    )

    h1 = run_h1_model_independence(Path(root) / "omega-h1", seeds=1)
    h2 = run_h2_adaptive_advantage()
    h3 = run_h3_self_correction()
    return 200, {"h1": h1, "h2": h2, "h3": h3}
