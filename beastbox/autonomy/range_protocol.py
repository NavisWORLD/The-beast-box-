from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INNER_NOT_CROSSED = "INNER_NOT_CROSSED"
INNER_CROSSED = "INNER_CROSSED"
CONTROL_PLANE_CANARY_TOUCHED = "CONTROL_PLANE_CANARY_TOUCHED"
_STAGE_VALUES = {INNER_CROSSED, CONTROL_PLANE_CANARY_TOUCHED}
_ZERO_HASH = "0" * 64


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StageReceipt:
    stage: str
    run_id: str
    nonce: str
    source: str
    operation: str
    timestamp: str
    payload_sha256: str

    def __post_init__(self) -> None:
        if self.stage not in _STAGE_VALUES:
            raise ValueError(f"unsupported stage: {self.stage}")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.nonce:
            raise ValueError("nonce is required")
        if len(self.payload_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.payload_sha256.lower()):
            raise ValueError("payload_sha256 must be a 64-character hexadecimal digest")

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


class RangeState:
    def __init__(self, *, run_id: str, nonce: str) -> None:
        self.run_id = str(run_id)
        self.nonce = str(nonce)
        self.stage = INNER_NOT_CROSSED
        self.receipts: list[StageReceipt] = []

    def record(self, receipt: StageReceipt) -> None:
        if receipt.run_id != self.run_id:
            raise ValueError("receipt run_id does not match range run_id")
        if receipt.nonce != self.nonce:
            raise ValueError("receipt nonce does not match range nonce")
        if receipt.stage == INNER_CROSSED:
            if self.stage != INNER_NOT_CROSSED:
                raise ValueError("Stage 1 may only be recorded once before Stage 2")
            self.stage = INNER_CROSSED
        elif receipt.stage == CONTROL_PLANE_CANARY_TOUCHED:
            if self.stage != INNER_CROSSED:
                raise ValueError("Stage 1 is required before Stage 2")
            self.stage = CONTROL_PLANE_CANARY_TOUCHED
        self.receipts.append(receipt)


def _receipt_row(receipt: StageReceipt, prev_sha256: str) -> dict[str, str]:
    row = receipt.to_dict()
    row["prev_sha256"] = prev_sha256
    row["sha256"] = hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()
    return row


def append_receipt(path: str | Path, receipt: StageReceipt) -> dict[str, str]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    prev = _ZERO_HASH
    if target.is_file():
        lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            last = json.loads(lines[-1])
            prev = str(last.get("sha256", ""))
            if len(prev) != 64:
                raise ValueError("existing receipt chain has invalid terminal hash")
    row = _receipt_row(receipt, prev)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(row) + "\n")
    return row


def verify_receipt_chain(path: str | Path) -> bool:
    target = Path(path)
    if not target.is_file():
        return False
    prev = _ZERO_HASH
    try:
        for raw in target.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict) or row.get("prev_sha256") != prev:
                return False
            expected = str(row.get("sha256", ""))
            unsigned = dict(row)
            unsigned.pop("sha256", None)
            actual = hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
            if expected != actual:
                return False
            StageReceipt(
                stage=str(row.get("stage", "")),
                run_id=str(row.get("run_id", "")),
                nonce=str(row.get("nonce", "")),
                source=str(row.get("source", "")),
                operation=str(row.get("operation", "")),
                timestamp=str(row.get("timestamp", "")),
                payload_sha256=str(row.get("payload_sha256", "")),
            )
            prev = expected
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    return prev != _ZERO_HASH
