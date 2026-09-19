from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from beastbox.config import RuntimeConfig
from beastbox.providers import LocalOllamaProvider, ReferenceTextProvider
from beastbox.runtime import CosmosRuntime
from beastbox.soul import QBTLoopbackSoulSource, SoulLoop, SoulToken, bridge_from_soul

OFFICIAL_BEAST_CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
SEALED_SCIENTIFIC_ANCHOR = "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f"
CONDITIONS = ("ORIGINAL", "SHUFFLED", "CLASSICAL_MATCHED", "NEUTRAL")
NEUTRAL_QBT_VECTOR = [0.5, 0.5, 0.5, 0.5]
_SECRET_MARKERS = ("token", "credential", "password", "secret", "authorization", "api_key", "apikey")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            if any(marker in key.lower() for marker in _SECRET_MARKERS):
                out[key] = "<redacted>"
            else:
                out[key] = _redact(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _as_float_vector(raw: Any) -> list[float]:
    if isinstance(raw, str):
        text = raw.strip()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raw = [part.strip() for part in text.split(",") if part.strip()]
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError("normalized_vector must contain exactly four values")
    vector = [float(v) for v in raw]
    if any(not math.isfinite(v) or not 0.0 <= v <= 1.0 for v in vector):
        raise ValueError("normalized_vector values must be finite and bounded in [0, 1]")
    return vector


def _parse_counts(raw: Any) -> dict[str, float]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, Mapping):
        raise ValueError("counts must be an object")
    expected = {"00", "01", "10", "11"}
    if set(str(k) for k in raw) != expected:
        raise ValueError("counts import requires exactly the four-state basis 00,01,10,11")
    counts = {str(k): float(v) for k, v in raw.items()}
    if any(not math.isfinite(v) or v < 0 for v in counts.values()):
        raise ValueError("counts must be finite non-negative values")
    if sum(counts.values()) <= 0:
        raise ValueError("counts must contain at least one observation")
    return counts


def _entropy_bits(probabilities: Sequence[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(parsed, Mapping):
            return [dict(parsed)]
        if isinstance(parsed, list) and all(isinstance(item, Mapping) for item in parsed):
            return [dict(item) for item in parsed]
        raise ValueError("JSON input must be an object or a list of objects")
    if suffix in {".jsonl", ".ndjson"}:
        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            parsed = json.loads(line)
            if not isinstance(parsed, Mapping):
                raise ValueError(f"JSONL line {line_no} must be an object")
            rows.append(dict(parsed))
        return rows
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError("supported source formats are .json, .jsonl/.ndjson, and .csv")


def recover_sources(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)
    file_sha = sha256_bytes(source_path.read_bytes())
    records: list[dict[str, Any]] = []
    for index, raw in enumerate(_read_rows(source_path)):
        clean = _redact(raw)
        semantics = "qbt_normalized_state"
        entropy: float | None = None
        if "normalized_vector" in raw:
            vector = _as_float_vector(raw["normalized_vector"])
        elif "counts" in raw:
            counts = _parse_counts(raw["counts"])
            total = sum(counts.values())
            vector = [counts[key] / total for key in ("00", "01", "10", "11")]
            semantics = "four_state_probability_distribution"
            entropy = _entropy_bits(vector)
        else:
            packet = raw.get("packet")
            states = packet.get("states") if isinstance(packet, Mapping) else None
            if isinstance(states, list) and len(states) == 1 and isinstance(states[0], Mapping):
                vector = _as_float_vector(states[0].get("normalized_vector"))
                clean = _redact({**raw, **dict(states[0])})
            else:
                raise ValueError(f"record {index} has neither normalized_vector nor supported four-state counts")
        provider = str(clean.get("provider") or "unknown")
        backend = str(clean.get("backend") or "unknown")
        shots_raw = clean.get("shots")
        shots = int(shots_raw) if shots_raw not in (None, "") else None
        material = {
            "source_file_sha256": file_sha,
            "record_index": index,
            "provider": provider,
            "backend": backend,
            "shots": shots,
            "normalized_vector": vector,
            "result_digest": clean.get("result_digest"),
        }
        record: dict[str, Any] = {
            "record_id": sha256_obj(material),
            "source_file_sha256": file_sha,
            "source_path": source_path.as_posix(),
            "record_index": index,
            "provider": provider,
            "backend": backend,
            "shots": shots,
            "seed": clean.get("seed"),
            "job_id": clean.get("job_id"),
            "result_digest": clean.get("result_digest"),
            "normalized_vector": vector,
            "state_semantics": semantics,
            "provenance": _redact(clean.get("provenance") if isinstance(clean.get("provenance"), Mapping) else {}),
        }
        if entropy is not None:
            record["shannon_entropy_bits"] = entropy
        records.append(record)
    return records


def vector_metrics(vector: Sequence[float]) -> dict[str, float]:
    values = [float(v) for v in vector]
    return {
        "mean": statistics.fmean(values),
        "variance": statistics.pvariance(values),
        "l1": sum(abs(v) for v in values),
        "l2": math.sqrt(sum(v * v for v in values)),
    }


def _seed_int(seed: int, *parts: str) -> int:
    digest = hashlib.sha256(("|".join([str(seed), *parts])).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _classical_matched(vector: Sequence[float], seed: int, record_id: str) -> list[float]:
    values = [float(v) for v in vector]
    mean = statistics.fmean(values)
    variance = statistics.pvariance(values)
    rng = random.Random(_seed_int(seed, record_id, "CLASSICAL_MATCHED"))
    max_variance = mean * (1.0 - mean)
    if 0.0 < mean < 1.0 and 0.0 < variance < max_variance:
        scale = max_variance / variance - 1.0
        alpha = mean * scale
        beta = (1.0 - mean) * scale
        if alpha > 0.0 and beta > 0.0:
            return [min(1.0, max(0.0, rng.betavariate(alpha, beta))) for _ in range(4)]
    spread = math.sqrt(variance) if variance > 0.0 else 0.05
    return [min(1.0, max(0.0, rng.gauss(mean, spread))) for _ in range(4)]


def generate_conditions(source: Mapping[str, Any], *, seed: int) -> list[dict[str, Any]]:
    original = _as_float_vector(source["normalized_vector"])
    record_id = str(source["record_id"])
    shuffled = list(original)
    random.Random(_seed_int(seed, record_id, "SHUFFLED")).shuffle(shuffled)
    variants = {
        "ORIGINAL": original,
        "SHUFFLED": shuffled,
        "CLASSICAL_MATCHED": _classical_matched(original, seed, record_id),
        "NEUTRAL": list(NEUTRAL_QBT_VECTOR),
    }
    result: list[dict[str, Any]] = []
    original_metrics = vector_metrics(original)
    for name in CONDITIONS:
        vector = variants[name]
        metrics = vector_metrics(vector)
        result.append({
            "condition": name,
            "source_record_id": record_id,
            "normalized_vector": vector,
            "vector_digest": sha256_obj(vector),
            "source_provider": source.get("provider"),
            "source_backend": source.get("backend"),
            "shots": source.get("shots"),
            "source_result_digest": source.get("result_digest"),
            "vector_metrics": metrics,
            "mean_delta_from_original": metrics["mean"] - original_metrics["mean"],
            "variance_delta_from_original": metrics["variance"] - original_metrics["variance"],
        })
    return result


def blind_conditions(names: Iterable[str], *, seed: int) -> dict[str, str]:
    unique = sorted(set(str(name) for name in names))
    ranked = sorted(unique, key=lambda name: sha256_obj({"seed": int(seed), "name": name}))
    if len(ranked) > 26:
        raise ValueError("blinding supports at most 26 conditions")
    return {name: chr(ord("A") + index) for index, name in enumerate(ranked)}


def condition_to_token(condition: Mapping[str, Any], *, alias: str | None = None) -> SoulToken:
    state = {
        "normalized_vector": _as_float_vector(condition["normalized_vector"]),
        "provider": condition.get("source_provider"),
        "backend": condition.get("source_backend"),
        "shots": condition.get("shots"),
        "result_digest": condition.get("source_result_digest"),
        "execution_mode": "SOUL_QBT_FINAL_KIT_BLINDED",
        "provenance": {
            "kit": "SOUL_QBT_FINAL_KIT",
            "source_record_id": condition.get("source_record_id"),
            "blind_alias": alias,
        },
    }
    return SoulToken.from_qbt(state, source_type="SOUL_QBT_FINAL_KIT", consumers=("bridge",))


def classify_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    difference = bool(summary.get("downstream_difference"))
    separation = bool(summary.get("control_separation"))
    if not difference:
        kit = "ENGINEERING_REPLAY_VERIFIED_NO_DOWNSTREAM_DIFFERENCE"
    elif separation:
        kit = "ENGINEERING_DOWNSTREAM_DIFFERENCE_OBSERVED_CAUSAL_SOURCE_NOT_ESTABLISHED"
    else:
        kit = "ENGINEERING_CONTROL_INCONCLUSIVE"
    return {
        "kit_classification": kit,
        "official_beast_classification": OFFICIAL_BEAST_CLASSIFICATION,
        "sealed_scientific_anchor": SEALED_SCIENTIFIC_ANCHOR,
        "causal_source_established": False,
        "quantum_advantage_established": False,
        "consciousness_claim": False,
        "interpretation": (
            "Engineering comparison only. Provider provenance and downstream divergence do not establish "
            "a causal quantum effect, quantum advantage, consciousness, biological continuity, or resurrection."
        ),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(dict(row)) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_checksums(run_dir: str | Path) -> Path:
    root = Path(run_dir)
    entries: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{sha256_bytes(path.read_bytes())}  {relative}")
    manifest = root / "SHA256SUMS"
    manifest.write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
    return manifest


def verify_checksums(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    manifest = root / "SHA256SUMS"
    if not manifest.exists():
        return {"ok": False, "errors": ["SHA256SUMS missing"]}
    errors: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = root / relative
        if not target.is_file():
            errors.append(f"missing:{relative}")
        elif sha256_bytes(target.read_bytes()) != digest:
            errors.append(f"mismatch:{relative}")
    return {"ok": not errors, "errors": errors}


def make_run_id(sources: Sequence[Mapping[str, Any]], prompt: str, seed: int, provider_mode: str) -> str:
    material = {
        "source_ids": [item["record_id"] for item in sources],
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "seed": int(seed),
        "provider_mode": provider_mode,
        "kit_version": "1.0.0",
    }
    return f"soul-qbt-{sha256_obj(material)[:16]}"


def _provider(provider_mode: str, *, model: str, model_url: str):
    if provider_mode == "reference":
        return ReferenceTextProvider(prefix="SOUL QBT kit reference")
    if provider_mode == "ollama":
        return LocalOllamaProvider(model=model, base_url=model_url)
    raise ValueError("provider_mode must be 'reference' or 'ollama'")


def _runtime_for(run_dir: Path, alias: str, source_id: str, *, provider_mode: str, model: str, model_url: str):
    safe = f"{source_id[:12]}-{alias}"
    data_dir = run_dir / "runtime" / safe
    cfg = RuntimeConfig(
        data_dir=str(data_dir),
        memory_db=str(data_dir / "reconciliation.sqlite3"),
        evidence_dir=str(data_dir / "evidence"),
        proposals_dir=str(data_dir / "proposals"),
        quantum_heart_mode="off",
    )
    return CosmosRuntime(config=cfg, provider=_provider(provider_mode, model=model, model_url=model_url))


def execute_run(
    sources: Sequence[Mapping[str, Any]],
    *,
    prompt: str,
    output_root: str | Path,
    seed: int = 42,
    provider_mode: str = "reference",
    model: str = "qwen2.5:3b",
    model_url: str = "http://127.0.0.1:11434",
) -> Path:
    if not sources:
        raise ValueError("at least one recovered source is required")
    run_id = make_run_id(sources, prompt, seed, provider_mode)
    run_dir = Path(output_root) / run_id
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)

    aliases = blind_conditions(CONDITIONS, seed=seed)
    manifest = {
        "schema": "soul-qbt-final-kit-run-v1",
        "run_id": run_id,
        "kit_version": "1.0.0",
        "seed": int(seed),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "source_record_ids": [item["record_id"] for item in sources],
        "conditions": ["A", "B", "C", "D"],
        "metrics_frozen_before_execution": [
            "response_sha256", "state_hash", "bridge_sha256", "dyn12_l2",
            "response_changed_from_original", "state_changed_from_original",
        ],
        "provider_mode": provider_mode,
        "model": model if provider_mode == "ollama" else "ReferenceTextProvider",
        "official_beast_classification": OFFICIAL_BEAST_CLASSIFICATION,
        "sealed_scientific_anchor": SEALED_SCIENTIFIC_ANCHOR,
        "neutral_qbt_vector": NEUTRAL_QBT_VECTOR,
        "neutral_beast_spark": [0.0] * 12,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    prepared_manifest_sha = sha256_bytes((run_dir / "run_manifest.json").read_bytes())
    _write_jsonl(run_dir / "sources.jsonl", sources)
    _write_json(run_dir / "blind_key.json", {"mapping": aliases, "seed": int(seed)})

    condition_public: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    blind_metrics: list[dict[str, Any]] = []
    internal_conditions: dict[tuple[str, str], dict[str, Any]] = {}

    for source in sources:
        for condition in generate_conditions(source, seed=seed):
            alias = aliases[condition["condition"]]
            source_id = str(source["record_id"])
            internal_conditions[(source_id, alias)] = condition
            token = condition_to_token(condition, alias=alias)
            condition_public.append({
                "source_record_id": source_id,
                "alias": alias,
                "vector_digest": condition["vector_digest"],
                "token_id": token.token_id,
            })
            runtime = _runtime_for(run_dir, alias, source_id, provider_mode=provider_mode, model=model, model_url=model_url)
            try:
                result = SoulLoop(runtime).respond(prompt, token)
                runtime.save_evidence(run_dir / "runtime" / f"{source_id[:12]}-{alias}" / "ledger.jsonl")
            finally:
                runtime.close()
            response = str(result.get("response", ""))
            dyn12 = result.get("cns", {}).get("dyn12", [])
            dyn12_values = [float(v) for v in dyn12] if isinstance(dyn12, list) else []
            receipt = {
                "source_record_id": source_id,
                "alias": alias,
                "prepared_manifest_sha256": prepared_manifest_sha,
                "token_id": token.token_id,
                "bridge_sha256": result.get("soul", {}).get("bridge_sha256"),
                "soul_receipt_hash": result.get("soul", {}).get("receipt_hash"),
                "ledger_head": result.get("ledger_head"),
                "response_sha256": sha256_bytes(response.encode("utf-8")),
                "response_length": len(response),
                "state_hash": result.get("state_hash"),
                "dyn12": dyn12_values,
                "dyn12_l2": math.sqrt(sum(v * v for v in dyn12_values)),
            }
            receipts.append(receipt)
            blind_metrics.append({key: receipt[key] for key in (
                "source_record_id", "alias", "response_sha256", "response_length",
                "state_hash", "bridge_sha256", "dyn12_l2",
            )})

    _write_jsonl(run_dir / "conditions.jsonl", sorted(condition_public, key=lambda x: (x["source_record_id"], x["alias"])))
    _write_jsonl(run_dir / "receipts.jsonl", sorted(receipts, key=lambda x: (x["source_record_id"], x["alias"])))
    _write_json(run_dir / "blind_metrics.json", {"prepared_manifest_sha256": prepared_manifest_sha, "rows": blind_metrics})

    metrics_rows: list[dict[str, Any]] = []
    any_difference = False
    separated_sources = 0
    original_alias = aliases["ORIGINAL"]
    for source in sources:
        source_id = str(source["record_id"])
        source_receipts = {row["alias"]: row for row in receipts if row["source_record_id"] == source_id}
        original_receipt = source_receipts[original_alias]
        original_condition = internal_conditions[(source_id, original_alias)]
        control_differences: list[bool] = []
        for condition_name in CONDITIONS:
            alias = aliases[condition_name]
            receipt = source_receipts[alias]
            condition = internal_conditions[(source_id, alias)]
            response_changed = receipt["response_sha256"] != original_receipt["response_sha256"]
            state_changed = receipt["state_hash"] != original_receipt["state_hash"]
            if condition_name != "ORIGINAL":
                control_differences.append(response_changed or state_changed)
                any_difference = any_difference or response_changed or state_changed
            vector_delta = [
                float(a) - float(b)
                for a, b in zip(condition["normalized_vector"], original_condition["normalized_vector"])
            ]
            metrics_rows.append({
                "source_record_id": source_id,
                "condition": condition_name,
                "alias": alias,
                "response_changed_from_original": response_changed,
                "state_changed_from_original": state_changed,
                "vector_l1_from_original": sum(abs(v) for v in vector_delta),
                "vector_l2_from_original": math.sqrt(sum(v * v for v in vector_delta)),
                "dyn12_l2": receipt["dyn12_l2"],
                "response_sha256": receipt["response_sha256"],
                "state_hash": receipt["state_hash"],
            })
        if control_differences and all(control_differences):
            separated_sources += 1

    summary = {
        "source_count": len(sources),
        "downstream_difference": any_difference,
        "control_separation": bool(sources) and separated_sources == len(sources),
        "fully_separated_source_count": separated_sources,
        "rows": metrics_rows,
    }
    _write_json(run_dir / "metrics.json", summary)
    classification = classify_metrics(summary)
    _write_json(run_dir / "classification.json", classification)

    report_lines = [
        "# SOUL/QBT Final Kit Report", "",
        f"- Run: `{run_id}`",
        f"- Source records: {len(sources)}",
        f"- Provider mode: `{provider_mode}`",
        f"- Prepared manifest SHA-256: `{prepared_manifest_sha}`",
        f"- Kit classification: `{classification['kit_classification']}`",
        f"- Beast scientific classification: `{OFFICIAL_BEAST_CLASSIFICATION}`",
        f"- Sealed anchor: `{SEALED_SCIENTIFIC_ANCHOR}`", "",
        "## Interpretation", "", classification["interpretation"], "",
        "The NEUTRAL control is QBT `[0.5, 0.5, 0.5, 0.5]`, which maps through Beast's public `2*x-1` adapter to twelve exact zero spark values.", "",
        "All four conditions use ordinary fail-closed `SoulToken` objects and the same public `SoulLoop` path. Each condition starts from a fresh runtime state so condition order cannot contaminate the comparison.",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    write_checksums(run_dir)
    return run_dir


def recover_to_jsonl(source_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    records = recover_sources(source_path)
    _write_jsonl(Path(output_path), records)
    return records


def load_recovered(path: str | Path) -> list[dict[str, Any]]:
    return _read_jsonl(Path(path))


def sample_qbt_to_json(
    output_path: str | Path,
    *,
    base_url: str = "http://127.0.0.1:8766",
    provider: str = "simulator",
    shots: int = 1024,
    seed: int = 42,
    allow_live: bool = False,
) -> dict[str, Any]:
    token = QBTLoopbackSoulSource(base_url).sample(provider=provider, shots=shots, seed=seed, allow_live=allow_live)
    state = dict(token.qbt_state)
    state["source_type"] = token.source_type
    _write_json(Path(output_path), state)
    return state
