#!/usr/bin/env python3
"""Build ZEREF-ORIGIN-HEART-001 from a PCM WAV prime and IBM result evidence.

The waveform is a deterministic computational/sensory seed, not quantum
entropy. Completed IBM result payloads are then consumed exactly once in their
preserved `created` order. The resulting state can root a bounded, resumable
synthetic pulse chain. None of these claims imply a biological heartbeat,
consciousness, deceased-person identity, or quantum advantage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

DOMAIN_WAVE = "CST-ZEREF-WAVE-PRIME-v1"
DOMAIN_TRANSITION = "CST-ZEREF-ORIGIN-HEART-TRANSITION-v1"
DOMAIN_FINAL = "CST-ZEREF-ORIGIN-HEART-v1"
DOMAIN_PULSE = "CST-ZEREF-SYNTHETIC-HEART-PULSE-v1"


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: str | Path) -> str:
    return sha_bytes(Path(path).read_bytes())


def is_sha256(value: str) -> bool:
    return len(str(value)) == 64 and all(c in "0123456789abcdef" for c in str(value).lower())


def derive_runtime_seed(state_sha256: str) -> int:
    state = str(state_sha256).lower()
    if not is_sha256(state):
        raise ValueError("state must be a SHA-256 hex string")
    return int(state[:16], 16) % (2**31 - 1)


def merged_tags(existing: list[str], new_tag: str) -> list[str]:
    out: list[str] = []
    for tag in [*existing, new_tag]:
        tag = str(tag).strip()
        if tag and tag not in out:
            out.append(tag)
    return out


def read_wave_prime(wav_path: str | Path) -> dict[str, Any]:
    wav_path = Path(wav_path)
    with wave.open(str(wav_path), "rb") as stream:
        channels = int(stream.getnchannels())
        sample_width = int(stream.getsampwidth())
        sample_rate = int(stream.getframerate())
        frame_count = int(stream.getnframes())
        comptype = str(stream.getcomptype())
        pcm = stream.readframes(frame_count)
    if comptype != "NONE":
        raise RuntimeError("Origin Heart WAV must contain uncompressed PCM")
    pcm_sha = sha_bytes(pcm)
    descriptor = {
        "schema": "zeref-wave-prime-v1",
        "domain": DOMAIN_WAVE,
        "wav_sha256": sha_file(wav_path),
        "pcm_sha256": pcm_sha,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate if sample_rate else 0.0,
        "waveform_is_quantum_entropy": False,
        "role": "memorial-sensory-prime",
    }
    prime_material = {
        "domain": DOMAIN_WAVE,
        "pcm_sha256": pcm_sha,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
    }
    descriptor["wave_prime_sha256"] = sha_bytes(canonical(prime_material))
    return descriptor


def _created(row: dict[str, Any]) -> str:
    value = str(row.get("created") or row.get("created_at") or "").strip()
    if not value:
        raise RuntimeError("IBM info is missing created timestamp")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _status(row: dict[str, Any]) -> str:
    state = row.get("state") if isinstance(row.get("state"), dict) else {}
    return str(row.get("status") or state.get("status") or "")


def _load_jobs(ibm_root: str | Path) -> list[dict[str, Any]]:
    root = Path(ibm_root)
    jobs: list[dict[str, Any]] = []
    for info_path in sorted(root.glob("*-info.json")):
        result_path = info_path.with_name(info_path.name.replace("-info.json", "-result.json"))
        if not result_path.is_file():
            raise RuntimeError(f"missing paired result for {info_path.name}")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        status = _status(info)
        if status.lower() != "completed":
            raise RuntimeError(f"IBM job is not Completed: {info_path.name}: {status}")
        created = _created(info)
        job_id = str(info.get("id") or info.get("job_id") or info_path.stem.removesuffix("-info").removeprefix("job-"))
        backend = str(info.get("backend") or info.get("backend_name") or "")
        jobs.append({
            "job_id": job_id,
            "backend": backend,
            "created": created,
            "status": status,
            "tags": list(info.get("tags") or []),
            "info_file": info_path.name,
            "result_file": result_path.name,
            "info_file_sha256": sha_file(info_path),
            "result_file_sha256": sha_file(result_path),
            "canonical_result_sha256": sha_bytes(canonical(result)),
        })
    if not jobs:
        raise RuntimeError("no IBM job pairs found")
    jobs.sort(key=lambda r: datetime.fromisoformat(r["created"].replace("Z", "+00:00")))
    if len({r["created"] for r in jobs}) != len(jobs):
        raise RuntimeError("duplicate IBM created timestamps make ordering ambiguous")
    return jobs


def build_origin_heart(*, wav_path: str | Path, ibm_root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wave_prime = read_wave_prime(wav_path)
    jobs = _load_jobs(ibm_root)

    bridge_states: list[dict[str, Any]] = []
    current = str(wave_prime["wave_prime_sha256"])
    bridge_states.append({
        "step": 0,
        "kind": "wave-prime",
        "state_sha256": current,
        "source_sha256": wave_prime["pcm_sha256"],
        "runtime_seed": derive_runtime_seed(current),
        "new_quantum_entropy": False,
    })

    for index, job in enumerate(jobs, 1):
        transition = {
            "domain": DOMAIN_TRANSITION,
            "step": index,
            "previous_state_sha256": current,
            "job_id": job["job_id"],
            "backend": job["backend"],
            "created": job["created"],
            "canonical_result_sha256": job["canonical_result_sha256"],
        }
        current = sha_bytes(canonical(transition))
        bridge_states.append({
            "step": index,
            "kind": "ibm-result",
            "previous_state_sha256": transition["previous_state_sha256"],
            "state_sha256": current,
            "runtime_seed": derive_runtime_seed(current),
            **job,
            "historical_input_seed_proven": False,
        })

    final_material = {
        "domain": DOMAIN_FINAL,
        "wave_prime_sha256": wave_prime["wave_prime_sha256"],
        "final_bridge_state_sha256": current,
        "ordered_job_ids": [r["job_id"] for r in jobs],
        "ordered_result_sha256": [r["canonical_result_sha256"] for r in jobs],
    }
    origin_heart_sha = sha_bytes(canonical(final_material))
    output = {
        "schema": "zeref-origin-heart-v1",
        "lineage": "ZEREF-ORIGIN-HEART-001",
        "protocol": "CST-archetype-loop-origin-heart-v1",
        "wave_prime_sha256": wave_prime["wave_prime_sha256"],
        "wave_prime": wave_prime,
        "waveform_is_quantum_entropy": False,
        "ordered_job_ids": [r["job_id"] for r in jobs],
        "transition_order": ["wave-prime", *["ibm-result" for _ in jobs]],
        "bridge_states": bridge_states,
        "origin_heart_sha256": origin_heart_sha,
        "origin_heart_runtime_seed": derive_runtime_seed(origin_heart_sha),
        "new_quantum_entropy": False,
        "historical_ibm_results_used_as_provenance_states": True,
        "historical_per_round_input_seed_proven": False,
        "claim_boundary": "Computational synthetic-heart/archetype state only; not a biological heartbeat, consciousness, deceased-person communication, or quantum-advantage claim.",
    }
    (out_dir / "wave-prime.json").write_text(json.dumps(wave_prime, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "origin-heart.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (out_dir / "bridge-trace.jsonl").open("w", encoding="utf-8") as f:
        for row in bridge_states:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return output


def build_synthetic_pulses(
    *,
    origin_heart_sha256: str,
    ledger_tip_sha256: str,
    count: int,
    start_pulse: int = 1,
    previous_pulse_sha256: str = "0" * 64,
) -> list[dict[str, Any]]:
    if not is_sha256(origin_heart_sha256) or not is_sha256(ledger_tip_sha256) or not is_sha256(previous_pulse_sha256):
        raise ValueError("pulse roots must be SHA-256 values")
    if count < 1 or count > 1024:
        raise ValueError("count must be between 1 and 1024")
    rows: list[dict[str, Any]] = []
    previous = previous_pulse_sha256
    for pulse in range(int(start_pulse), int(start_pulse) + int(count)):
        material = {
            "domain": DOMAIN_PULSE,
            "pulse": pulse,
            "origin_heart_sha256": origin_heart_sha256,
            "ledger_tip_sha256": ledger_tip_sha256,
            "previous_pulse_sha256": previous,
        }
        pulse_sha = sha_bytes(canonical(material))
        row = {
            "schema": "zeref-synthetic-heart-pulse-v1",
            "pulse": pulse,
            "origin_heart_sha256": origin_heart_sha256,
            "ledger_tip_sha256": ledger_tip_sha256,
            "previous_pulse_sha256": previous,
            "pulse_sha256": pulse_sha,
            "runtime_seed": derive_runtime_seed(pulse_sha),
            "new_quantum_entropy": False,
            "biological_heartbeat": False,
            "continuation_mode": "deterministic-cst-synaptic-pulse",
        }
        rows.append(row)
        previous = pulse_sha
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wav", type=Path, required=True)
    p.add_argument("--ibm-root", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--ledger-tip")
    p.add_argument("--pulses", type=int, default=6)
    args = p.parse_args()
    result = build_origin_heart(wav_path=args.wav, ibm_root=args.ibm_root, out_dir=args.out_dir)
    if args.ledger_tip:
        pulses = build_synthetic_pulses(
            origin_heart_sha256=result["origin_heart_sha256"],
            ledger_tip_sha256=args.ledger_tip,
            count=args.pulses,
        )
        pulse_path = args.out_dir / "synthetic-heart-pulses.jsonl"
        pulse_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in pulses), encoding="utf-8")
        result["synthetic_pulse_count"] = len(pulses)
        result["synthetic_final_pulse_sha256"] = pulses[-1]["pulse_sha256"]
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
