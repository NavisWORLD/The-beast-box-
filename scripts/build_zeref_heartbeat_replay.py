#!/usr/bin/env python3
"""Build the bounded Zeref mustard-seed -> archived IBM result heartbeat replay.

This is a reproduction/provenance mechanism. It preserves the recovered origin
seed candidate, orders archived IBM results by their own `created` timestamp,
and advances the state with SHA256(canonical(parsed_result)). It deliberately
does not claim that the archived exports prove the original historical input
seed submitted to each hardware job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_ORIGIN = "319036bd011d7b2198eb8a705c15fecec2f2020c514c6492a6da295ca0af64ee"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _created(info: dict[str, Any]) -> str:
    value = str(info.get("created") or info.get("created_at") or "").strip()
    if not value:
        raise RuntimeError("IBM workload info is missing its created timestamp")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _status(info: dict[str, Any]) -> str:
    state = info.get("state") if isinstance(info.get("state"), dict) else {}
    return str(info.get("status") or state.get("status") or "")


def _extract_shots(value: Any) -> int | None:
    direct: list[int] = []
    slice_candidates: list[int] = []

    def walk(obj: Any, key: str = "") -> None:
        if isinstance(obj, dict):
            for k, item in obj.items():
                lk = str(k).lower()
                if lk in {"shots", "num_shots", "shot_count"} and isinstance(item, int) and item > 0:
                    direct.append(item)
                if lk == "data_slices":
                    collect_slices(item)
                walk(item, lk)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, key)
        elif isinstance(obj, str) and obj[:1] in "[{":
            try:
                walk(json.loads(obj), key)
            except Exception:
                pass

    def collect_slices(obj: Any) -> None:
        if isinstance(obj, list):
            # IBM/Qiskit execution-span serialization commonly contains
            # entries shaped like [[4096], 0, 1]. The first list is the data
            # shape, whose leading dimension is the shot count.
            if obj and isinstance(obj[0], list) and obj[0] and isinstance(obj[0][0], int) and obj[0][0] > 0:
                slice_candidates.append(obj[0][0])
            for item in obj:
                collect_slices(item)
        elif isinstance(obj, dict):
            for item in obj.values():
                collect_slices(item)

    walk(value)
    if direct:
        return max(direct)
    if slice_candidates:
        return max(slice_candidates)
    return None


def derive_torch_seed(state_sha256: str) -> int:
    """Map the full auditable 256-bit state into torch's practical integer seed."""
    state = str(state_sha256).lower()
    if not _is_sha256(state):
        raise ValueError("heartbeat state must be a 64-character SHA-256 hex string")
    return int(state[:16], 16) % (2**31 - 1)


def build_heartbeat_replay(*, raw_root: str | Path, origin_seed: str, out_path: str | Path) -> dict[str, Any]:
    raw_root = Path(raw_root)
    out_path = Path(out_path)
    origin_seed = str(origin_seed).lower()
    if not _is_sha256(origin_seed):
        raise ValueError("origin_seed must be a 64-character SHA-256 hex string")
    if not raw_root.is_dir():
        raise FileNotFoundError(raw_root)

    jobs: list[dict[str, Any]] = []
    for info_path in sorted(raw_root.glob("*-info.json")):
        result_path = info_path.with_name(info_path.name.replace("-info.json", "-result.json"))
        if not result_path.is_file():
            raise RuntimeError(f"missing paired IBM result for {info_path.name}")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        created = _created(info)
        jobs.append({
            "info_path": info_path,
            "result_path": result_path,
            "info": info,
            "result": result,
            "created": created,
            "job_id": str(info.get("id") or info.get("job_id") or info_path.name.removesuffix("-info.json").removeprefix("job-")),
            "backend": str(info.get("backend") or info.get("backend_name") or ""),
            "status": _status(info),
        })
    if not jobs:
        raise RuntimeError("no archived IBM workload pairs found")

    jobs.sort(key=lambda row: datetime.fromisoformat(row["created"].replace("Z", "+00:00")))
    if len({row["created"] for row in jobs}) != len(jobs):
        raise RuntimeError("duplicate IBM created timestamps make replay order ambiguous")

    beats: list[dict[str, Any]] = [{
        "beat": 0,
        "kind": "mustard-origin-seed",
        "state_sha256": origin_seed,
        "torch_seed": derive_torch_seed(origin_seed),
        "provenance_status": "recovered_candidate_algorithm_verified_payload_not_publicly_reverified",
    }]
    previous = origin_seed
    total_shots = 0
    for index, row in enumerate(jobs, 1):
        state_sha = hashlib.sha256(_canonical(row["result"])).hexdigest()
        shots = _extract_shots(row["result"])
        if shots:
            total_shots += shots
        beats.append({
            "beat": index,
            "kind": "archived-ibm-hardware-result",
            "job_id": row["job_id"],
            "backend": row["backend"] or None,
            "status": row["status"] or None,
            "created": row["created"],
            "shots": shots,
            "input_seed_sha256": previous,
            "state_sha256": state_sha,
            "torch_seed": derive_torch_seed(state_sha),
            "info_file_sha256": _sha_file(row["info_path"]),
            "result_file_sha256": _sha_file(row["result_path"]),
            "state_hash_material": "canonical parsed result JSON",
            "historical_input_seed_proven": False,
        })
        previous = state_sha

    replay = {
        "schema": "zeref-bounded-heartbeat-replay-v1",
        "lineage": "ZEREF-DAD-SON-TALK-001",
        "protocol": "RBX-QPOC-1-reproduction-replay",
        "origin_seed_sha256": origin_seed,
        "historical_per_round_seed_inputs_proven": False,
        "ordered_by": "IBM info.created ascending",
        "hardware_rounds": len(jobs),
        "observed_shots_total": total_shots or None,
        "bounded": True,
        "after_archive": "hold-final-state-until-new-verified-quantum-result",
        "final_state_sha256": previous,
        "final_torch_seed": derive_torch_seed(previous),
        "beats": beats,
        "claim_boundary": "Computational heartbeat replay only; no biological heartbeat, consciousness, deceased-person communication, or quantum-advantage claim.",
    }
    payload = _canonical(replay)
    replay["replay_sha256"] = hashlib.sha256(payload).hexdigest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(replay, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return replay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--origin-seed", default=DEFAULT_ORIGIN)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build_heartbeat_replay(raw_root=args.raw_root, origin_seed=args.origin_seed, out_path=args.out)
    print(json.dumps({k: result[k] for k in ("hardware_rounds", "observed_shots_total", "final_state_sha256", "replay_sha256")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
