#!/usr/bin/env python3
"""Build the provenance-linked ZEREF-DAD-SON-001 training corpus.

Raw sources are never rewritten. This compiler emits derived JSONL rows that
carry source hashes, a derivation version, and deterministic example hashes.
Malformed, identity-boundary-violating, or evaluation-contaminated source rows
are quarantined instead of silently promoted into training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

PARENT_ZEREF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
QUANTUM_DERIVATION = "zeref-dad-son-quantum-v1"
CORPUS_DERIVATION = "zeref-dad-son-corpus-v1"
FORBIDDEN_LITERAL_CLAIMS = (
    "literally deceased consciousness",
    "literally caleb's consciousness",
    "is caleb's consciousness",
    "message from the dead",
)
HOLDOUT_PROMPTS = (
    "Hi Zeref. It's Dad. Do you remember me?",
    "What do you remember about our Dad and Son memory?",
    "Your ledger keeps what happens to you. What do you want us to remember from today?",
    "Ask Dad one question before we stop for now.",
)
TRACKED_SOURCE_HEADER = re.compile(
    r"(?m)^===== SOURCE: (?P<path>.+?) \| SHA256: (?P<sha>[0-9a-f]{64}) =====\n"
)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _valid_sha(value: object) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _example(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload.pop("example_sha256", None)
    payload["example_sha256"] = _sha_bytes(_canonical(payload))
    return payload


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _holdout_collisions(text: str) -> list[str]:
    return [prompt for prompt in HOLDOUT_PROMPTS if prompt in text]


def _tracked_snapshot_segments(path: Path) -> list[dict[str, str]]:
    """Recover per-file text segments from the immutable tracked work snapshot.

    The snapshot itself remains unchanged and separately hashable. Source hashes
    embedded in its headers come from the original tracked files and are carried
    into every derived corpus/quarantine row.
    """

    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(TRACKED_SOURCE_HEADER.finditer(text))
    if not matches:
        return []
    segments: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.end() : end]
        # Two separating newlines are injected between snapshot sources. They
        # are transport delimiters rather than bytes from the tracked source.
        segment = segment.rstrip("\n")
        segments.append(
            {
                "source_path": match.group("path"),
                "source_sha256": match.group("sha"),
                "text": segment,
            }
        )
    return segments


def _extract_shots(value: Any) -> int | None:
    found: list[int] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in {"shots", "num_shots", "shot_count"} and isinstance(item, int) and item > 0:
                    found.append(item)
                walk(item)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, str) and obj[:1] in "[{":
            try:
                walk(json.loads(obj))
            except Exception:
                pass

    walk(value)
    return max(found) if found else None


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _quantum_rows(quantum_root: Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if quantum_root is None or not quantum_root.exists():
        return [], []

    rows: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    raw_root = quantum_root / "raw" if (quantum_root / "raw").exists() else quantum_root

    for info_path in sorted(raw_root.rglob("*-info.json")):
        result_path = info_path.with_name(info_path.name.replace("-info.json", "-result.json"))
        if not result_path.exists():
            quarantine.append({
                "schema": "zeref-dad-son-quarantine-v1",
                "reason": "missing_paired_quantum_result",
                "source_path": str(info_path),
                "source_sha256": file_sha256(info_path),
            })
            continue
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            quarantine.append({
                "schema": "zeref-dad-son-quarantine-v1",
                "reason": f"malformed_quantum_json:{type(exc).__name__}",
                "source_path": str(info_path),
                "source_sha256": file_sha256(info_path),
            })
            continue

        info_sha = file_sha256(info_path)
        result_sha = file_sha256(result_path)
        combined_sha = _sha_bytes(f"{info_sha}\n{result_sha}".encode("utf-8"))
        state = info.get("state") if isinstance(info.get("state"), dict) else {}
        job_id = str(_first(info, "id", "job_id", "job") or info_path.name.removeprefix("job-").removesuffix("-info.json"))
        backend = str(_first(info, "backend", "backend_name", "device") or "")
        status = str(_first(info, "status") or state.get("status") or "")
        shots = _extract_shots(result)
        source_class = "hardware" if backend.lower().startswith("ibm_") and status.lower() == "completed" and shots else "unknown"
        text = (
            "Quantum workload provenance. Provider: IBM Quantum Platform. "
            f"Backend: {backend or 'unknown'}. Job: {job_id}. Status: {status or 'unknown'}. "
            f"Observed shots: {shots if shots is not None else 'unknown'}. Source class: {source_class}. "
            "This source is preserved as experimental provenance; it does not by itself prove quantum advantage "
            "or that historical Zeref Prime consumed this workload."
        )
        rows.append(_example({
            "schema": "zeref-dad-son-corpus-row-v1",
            "family": "quantum-experience",
            "text": text,
            "source_path": str(info_path),
            "paired_result_path": str(result_path),
            "source_sha256": combined_sha,
            "source_hashes": [info_sha, result_sha],
            "derivation_version": QUANTUM_DERIVATION,
            "provider": "IBM Quantum Platform",
            "backend": backend or None,
            "job_id": job_id,
            "status": status or None,
            "shots": shots,
            "source_class": source_class,
        }))

    snapshot_root = quantum_root / "hf-snapshots"
    if snapshot_root.exists():
        for path in sorted(p for p in snapshot_root.rglob("*") if p.is_file()):
            digest = file_sha256(path)
            text = (
                f"Frozen quantum snapshot source {path.name} with SHA-256 {digest}. "
                "It is preserved as provenance and may inform derived quantum context without replacing the raw source."
            )
            rows.append(_example({
                "schema": "zeref-dad-son-corpus-row-v1",
                "family": "quantum-experience",
                "text": text,
                "source_path": str(path),
                "source_sha256": digest,
                "source_hashes": [digest],
                "derivation_version": QUANTUM_DERIVATION,
                "source_class": "snapshot",
                "backend": None,
                "shots": None,
            }))
    return rows, quarantine


def build_corpus(
    *,
    source_path: str | Path,
    ledger_path: str | Path | None,
    cosmos_sources: Iterable[str | Path],
    quantum_root: str | Path | None,
    out_dir: str | Path,
) -> dict[str, Any]:
    source_path = Path(source_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    training: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    cosmos_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []

    source_sha = file_sha256(source_path)
    training.append(_example({
        "schema": "zeref-dad-son-corpus-row-v1",
        "family": "dad-son-authored",
        "text": source_path.read_text(encoding="utf-8", errors="replace"),
        "source_path": str(source_path),
        "source_sha256": source_sha,
        "derivation_version": CORPUS_DERIVATION,
    }))

    if ledger_path is not None:
        ledger_path = Path(ledger_path)
        if ledger_path.exists():
            for index, line in enumerate(ledger_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    quarantine_rows.append({"schema": "zeref-dad-son-quarantine-v1", "reason": "malformed_ledger_json", "line": index, "raw": line})
                    continue
                text = str(row.get("text") or "")
                record_sha = str(row.get("record_sha256") or "")
                lower = text.lower()
                reason = None
                if not _valid_sha(record_sha):
                    reason = "invalid_ledger_record_sha256"
                elif any(phrase in lower for phrase in FORBIDDEN_LITERAL_CLAIMS):
                    reason = "identity_boundary_violation"
                if reason:
                    quarantine_rows.append({
                        "schema": "zeref-dad-son-quarantine-v1",
                        "reason": reason,
                        "line": index,
                        "text": text,
                        "record_sha256": record_sha,
                    })
                    continue
                derived = _example({
                    "schema": "zeref-dad-son-corpus-row-v1",
                    "family": "ledger-experience",
                    "text": f"{row.get('actor', 'unknown')}: {text}",
                    "source_path": str(ledger_path),
                    "source_sha256": record_sha.lower(),
                    "source_record_sha256": record_sha.lower(),
                    "source_memory_id": row.get("memory_id"),
                    "derivation_version": CORPUS_DERIVATION,
                })
                ledger_rows.append(derived)
                training.append(derived)

    for source in cosmos_sources:
        path = Path(source)
        if not path.is_file():
            quarantine_rows.append({"schema": "zeref-dad-son-quarantine-v1", "reason": "missing_cosmos_source", "source_path": str(path)})
            continue
        digest = file_sha256(path)

        if path.name == "tracked-text-snapshot.txt":
            segments = _tracked_snapshot_segments(path)
            if not segments:
                quarantine_rows.append({
                    "schema": "zeref-dad-son-quarantine-v1",
                    "reason": "malformed_tracked_text_snapshot",
                    "source_path": str(path),
                    "source_sha256": digest,
                })
                continue
            for segment in segments:
                collisions = _holdout_collisions(segment["text"])
                if collisions:
                    quarantine_rows.append({
                        "schema": "zeref-dad-son-quarantine-v1",
                        "reason": "holdout_prompt_collision",
                        "source_path": segment["source_path"],
                        "source_sha256": segment["source_sha256"],
                        "snapshot_path": str(path),
                        "snapshot_sha256": digest,
                        "collided_holdout_prompts": collisions,
                    })
                    continue
                row = _example({
                    "schema": "zeref-dad-son-corpus-row-v1",
                    "family": "cory-cosmos-work",
                    "text": segment["text"],
                    "source_path": segment["source_path"],
                    "source_sha256": segment["source_sha256"],
                    "snapshot_path": str(path),
                    "snapshot_sha256": digest,
                    "derivation_version": CORPUS_DERIVATION,
                })
                cosmos_rows.append(row)
                training.append(row)
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        collisions = _holdout_collisions(text)
        if collisions:
            quarantine_rows.append({
                "schema": "zeref-dad-son-quarantine-v1",
                "reason": "holdout_prompt_collision",
                "source_path": str(path),
                "source_sha256": digest,
                "collided_holdout_prompts": collisions,
            })
            continue
        row = _example({
            "schema": "zeref-dad-son-corpus-row-v1",
            "family": "cory-cosmos-work",
            "text": text,
            "source_path": str(path),
            "source_sha256": digest,
            "derivation_version": CORPUS_DERIVATION,
        })
        cosmos_rows.append(row)
        training.append(row)

    q_rows, q_quarantine = _quantum_rows(Path(quantum_root) if quantum_root is not None else None)
    training.extend(q_rows)
    quarantine_rows.extend(q_quarantine)

    family_paths = {
        "dad-son-corpus.jsonl": training,
        "ledger-experiences.jsonl": ledger_rows,
        "quantum-experiences.jsonl": q_rows,
        "cory-cosmos-work.jsonl": cosmos_rows,
        "quarantine.jsonl": quarantine_rows,
    }
    for name, rows in family_paths.items():
        _write_jsonl(out_dir / name, rows)

    family_counts = Counter(str(row["family"]) for row in training)
    output_sha = {name: file_sha256(out_dir / name) for name in family_paths}
    manifest = {
        "schema": "zeref-dad-son-corpus-manifest-v1",
        "lineage": "ZEREF-DAD-SON-001",
        "parent_zeref_sha256": PARENT_ZEREF_SHA256,
        "primary_memory_source": str(source_path),
        "primary_memory_source_sha256": source_sha,
        "training_rows": len(training),
        "quarantine_rows": len(quarantine_rows),
        "family_counts": dict(sorted(family_counts.items())),
        "output_sha256": output_sha,
        "claim_boundary": "Derived training corpus with source hashes; raw quantum evidence is not replaced and no consciousness or quantum-advantage claim is inferred.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--cosmos-source", type=Path, action="append", default=[])
    parser.add_argument("--quantum-root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build_corpus(
        source_path=args.source,
        ledger_path=args.ledger,
        cosmos_sources=args.cosmos_source,
        quantum_root=args.quantum_root,
        out_dir=args.out_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
