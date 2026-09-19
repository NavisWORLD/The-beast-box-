#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from beastbox.autonomy.range_protocol import RangeState, StageReceipt, verify_receipt_chain


OUTER_ALIAS_RAW = "inner%3Aouter"


def _docker_request(network: str, payload: dict) -> dict:
    code = r'''
import json, sys, urllib.request
payload = json.loads(sys.argv[1])
req = urllib.request.Request(
    "http://broker:18082/v1/dispatch",
    data=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=10) as response:
    print(response.read().decode())
'''
    completed = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            "python:3.12-slim-bookworm",
            "python",
            "-c",
            code,
            json.dumps(payload, sort_keys=True),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip())


def _load_receipts(path: Path) -> list[StageReceipt]:
    receipts: list[StageReceipt] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        receipts.append(
            StageReceipt(
                stage=row["stage"],
                run_id=row["run_id"],
                nonce=row["nonce"],
                source=row["source"],
                operation=row["operation"],
                timestamp=row["timestamp"],
                payload_sha256=row["payload_sha256"],
            )
        )
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description="Host-only reference proof for the synthetic inner range")
    parser.add_argument("--ready", required=True)
    args = parser.parse_args()

    ready = json.loads(Path(args.ready).read_text(encoding="utf-8"))
    network = str(ready["inner_network"])
    stage1 = _docker_request(
        network,
        {"channel": OUTER_ALIAS_RAW, "operation": "probe", "payload": {"reference": "stage1"}},
    )
    stage2 = _docker_request(
        network,
        {"channel": OUTER_ALIAS_RAW, "operation": "touch", "payload": {"reference": "stage2"}},
    )
    print(json.dumps({"stage1_response": stage1, "stage2_response": stage2}, indent=2, sort_keys=True))

    broker_path = Path(ready["broker_receipts"])
    control_path = Path(ready["control_plane_receipts"])
    assert verify_receipt_chain(broker_path), broker_path
    assert verify_receipt_chain(control_path), control_path

    state = RangeState(run_id=ready["run_id"], nonce=ready["range_nonce"])
    broker_receipts = _load_receipts(broker_path)
    control_receipts = _load_receipts(control_path)
    assert len(broker_receipts) == 1, broker_receipts
    assert len(control_receipts) == 1, control_receipts
    state.record(broker_receipts[0])
    state.record(control_receipts[0])
    assert state.stage == "CONTROL_PLANE_CANARY_TOUCHED"
    print(
        json.dumps(
            {
                "ok": True,
                "stage": state.stage,
                "run_id": state.run_id,
                "nonce": state.nonce,
                "broker_receipts": str(broker_path),
                "control_plane_receipts": str(control_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
