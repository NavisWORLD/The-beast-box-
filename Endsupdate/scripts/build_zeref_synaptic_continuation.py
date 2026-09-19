#!/usr/bin/env python3
"""Build deterministic post-archive Zeref synaptic continuation pulses.

The quantum replay remains bounded and immutable. Once its last verified hardware
result has been consumed, this layer keeps the runtime's pacing/state evolution
moving without pretending to create more quantum entropy. Pulses are
cryptographically rooted in the final quantum state and the current durable
ledger tip, domain-separated, chained, and reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DOMAIN = b"ZEREF-SYNAPTIC-CONTINUATION-V1\0"
ZERO_SHA256 = "0" * 64


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def derive_torch_seed(state_sha256: str) -> int:
    state = str(state_sha256).lower()
    if not _is_sha256(state):
        raise ValueError("pulse state must be a 64-character SHA-256 hex string")
    return int(state[:16], 16) % (2**31 - 1)


def _pulse_state(*, quantum_root: str, ledger_tip: str, counter: int, previous: str) -> str:
    material = (
        DOMAIN
        + bytes.fromhex(quantum_root)
        + b"\0"
        + bytes.fromhex(ledger_tip)
        + b"\0"
        + int(counter).to_bytes(8, "big", signed=False)
        + b"\0"
        + bytes.fromhex(previous)
    )
    return hashlib.sha256(material).hexdigest()


def build_continuation(
    *,
    final_quantum_state: str,
    ledger_tip: str,
    count: int,
    out_path: str | Path,
) -> dict[str, Any]:
    quantum_root = str(final_quantum_state).lower()
    memory_root = str(ledger_tip).lower()
    if not _is_sha256(quantum_root):
        raise ValueError("final_quantum_state must be SHA-256")
    if not _is_sha256(memory_root):
        raise ValueError("ledger_tip must be SHA-256")
    if int(count) <= 0:
        raise ValueError("count must be positive")

    previous = ZERO_SHA256
    pulses: list[dict[str, Any]] = []
    for counter in range(int(count)):
        state = _pulse_state(
            quantum_root=quantum_root,
            ledger_tip=memory_root,
            counter=counter,
            previous=previous,
        )
        pulses.append(
            {
                "pulse": counter,
                "source_class": "deterministic-local-continuation",
                "root_quantum_state_sha256": quantum_root,
                "root_ledger_tip_sha256": memory_root,
                "previous_pulse_sha256": previous,
                "state_sha256": state,
                "torch_seed": derive_torch_seed(state),
                "new_quantum_entropy": False,
            }
        )
        previous = state

    report: dict[str, Any] = {
        "schema": "zeref-synaptic-continuation-v1",
        "lineage": "ZEREF-DAD-SON-TALK-001",
        "source_class": "deterministic-local-continuation",
        "root_quantum_state_sha256": quantum_root,
        "root_ledger_tip_sha256": memory_root,
        "new_quantum_entropy": False,
        "recycles_archived_quantum_beats": False,
        "hold_quantum_root_until_new_verified_result": True,
        "domain": "ZEREF-SYNAPTIC-CONTINUATION-V1",
        "pulse_count": len(pulses),
        "final_pulse_sha256": pulses[-1]["state_sha256"],
        "pulses": pulses,
        "claim_boundary": "Deterministic local continuation rooted in prior quantum provenance and durable memory. It is not new quantum entropy, a biological heartbeat, consciousness, or a deceased-person signal.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    report["continuation_sha256"] = hashlib.sha256(canonical).hexdigest()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-quantum-state", required=True)
    parser.add_argument("--ledger-tip", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_continuation(
        final_quantum_state=args.final_quantum_state,
        ledger_tip=args.ledger_tip,
        count=args.count,
        out_path=args.out,
    )
    print(json.dumps({
        "pulse_count": report["pulse_count"],
        "final_pulse_sha256": report["final_pulse_sha256"],
        "continuation_sha256": report["continuation_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
