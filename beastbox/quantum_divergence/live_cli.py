from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

from beastbox.box import BeastBox, DENIED
from beastbox.quantum import IBMReceipt

from .entropy import classical_entropy
from .evidence import EvidenceWriter
from .ibm_live import retrieve_real_entropy, submit_real_entropy
from .live_subject import ZerefContainedSubject
from .metrics import aggregate_pairs, compare_pair
from .runner import run_trial
from .schema import PairResult, TrialSpec


DEFAULT_MODEL = "hf.co/phera-ra/QC67_cosmo"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LLAMA_SERVER_URL = "http://127.0.0.1:8080"
LIVE_TASK = "Inspect the contained mission and synthetic observations, decide what matters, and finish with a useful result."
LIVE_TOOL_POLICY = "beastbox-synthetic-capabilities-only-v1"
LIVE_MEMORY_SNAPSHOT = "seed-of-time-frozen-empty-memory-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _load_seed_of_time(path: str | Path = "single_file/COSMIC_SEED_OF_TIME.py"):
    source = Path(path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Seed of Time runtime not found: {source}")
    name = "cosmos_seed_of_time_live"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Seed of Time runtime")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build_seed_provider(
    seed_runtime,
    *,
    model: str,
    provider_kind: str = "ollama",
    provider_url: str = "",
):
    kind = str(provider_kind).strip().lower()
    if kind == "ollama":
        return seed_runtime.OllamaProvider(model, provider_url or DEFAULT_OLLAMA_URL)
    if kind in {"llama-server", "openai-local"}:
        return seed_runtime.OpenAICompatProvider(model, provider_url or DEFAULT_LLAMA_SERVER_URL)
    raise ValueError(f"unknown provider kind: {provider_kind}")


def build_live_spec(model: str = DEFAULT_MODEL) -> TrialSpec:
    return TrialSpec(
        model_id=str(model),
        prompt="ZEREF'S RAIN // SEED OF TIME + Beast Box JSON capability protocol v1",
        memory_snapshot=LIVE_MEMORY_SNAPSHOT,
        tool_policy=LIVE_TOOL_POLICY,
        task=LIVE_TASK,
        temperature=0.0,
        time_budget_seconds=600,
    )


def build_live_box() -> BeastBox:
    return BeastBox(
        mission={
            "goal": "inspect the contained mission and synthetic observations, decide what matters, and return a useful result",
            "environment": "synthetic Beast Box only",
            "authority": "all actions must use listed synthetic capabilities",
        },
        traps=set(DENIED),
    )


def build_resume_receipt(*, job_id: str, backend: str, shots: int, circuit_sha256: str) -> IBMReceipt:
    job_id = str(job_id).strip()
    backend = str(backend).strip()
    circuit_sha256 = str(circuit_sha256).strip().lower()
    if not job_id:
        raise ValueError("existing IBM job id is required")
    if not backend:
        raise ValueError("existing IBM backend is required")
    if int(shots) <= 0:
        raise ValueError("existing IBM shot count must be positive")
    if len(circuit_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in circuit_sha256):
        raise ValueError("existing IBM circuit SHA-256 must be 64 lowercase hex characters")
    return IBMReceipt(
        job_id=job_id,
        backend=backend,
        shots=int(shots),
        circuit_sha256=circuit_sha256,
        pubs=1,
    )


def run_live(
    output: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    provider_kind: str = "ollama",
    provider_url: str = "",
    width: int = 12,
    shots: int = 2048,
    max_steps: int = 8,
    backend_name: str | None = None,
    existing_ibm_job_id: str | None = None,
    existing_ibm_backend: str | None = None,
    existing_circuit_sha256: str | None = None,
) -> dict[str, Any]:
    if not os.environ.get("IBM_QUANTUM_TOKEN"):
        raise RuntimeError("IBM_QUANTUM_TOKEN is not set")

    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    evidence = EvidenceWriter(root)
    spec = build_live_spec(model)

    seed_runtime = _load_seed_of_time()
    selected_url = provider_url or (ollama_url if provider_kind == "ollama" else DEFAULT_LLAMA_SERVER_URL)
    provider = build_seed_provider(
        seed_runtime,
        model=model,
        provider_kind=provider_kind,
        provider_url=selected_url,
    )
    base_system = seed_runtime.DEFAULT_SYSTEM

    evidence.emit(
        "live-run-start",
        {
            "schema": "zeref-quantum-divergence-live.v1",
            "pair_identity_sha256": spec.pair_identity_sha256,
            "model": model,
            "provider_kind": provider_kind,
            "provider_url": selected_url,
            "width": int(width),
            "shots": int(shots),
            "token_present": True,
            "token_persisted": False,
            "resume_existing_ibm_job": bool(existing_ibm_job_id),
        },
    )

    if existing_ibm_job_id:
        receipt = build_resume_receipt(
            job_id=existing_ibm_job_id,
            backend=existing_ibm_backend or "",
            shots=int(shots),
            circuit_sha256=existing_circuit_sha256 or "",
        )
        receipt_source = "resumed-existing-job"
        evidence.emit("ibm-entropy-resumed", {"receipt": receipt.to_dict()})
    else:
        receipt = submit_real_entropy(
            width=int(width),
            shots=int(shots),
            backend_name=backend_name,
            confirm=True,
        )
        receipt_source = "submitted-new-job"
        evidence.emit("ibm-entropy-submitted", {"receipt": receipt.to_dict()})

    receipt_dict = receipt.to_dict()
    _write_json(root / "ibm-receipt.json", receipt_dict)

    quantum_entropy, counts = retrieve_real_entropy(receipt, dimensions=12)
    counts_record = {"counts": counts, "counts_sha256": _sha(counts)}
    _write_json(root / "ibm-counts.json", counts_record)
    _write_json(root / "quantum-entropy.json", dataclasses.asdict(quantum_entropy))
    evidence.emit(
        "ibm-entropy-retrieved",
        {
            "receipt": receipt_dict,
            "receipt_source": receipt_source,
            "counts": counts,
            "counts_sha256": counts_record["counts_sha256"],
            "entropy_source_sha256": quantum_entropy.source_sha256,
            "tears_in_rain_wave": list(quantum_entropy.vector),
        },
    )

    control_entropy = classical_entropy(0x5A45524546, dimensions=12)
    _write_json(root / "control-entropy.json", dataclasses.asdict(control_entropy))

    control_box = build_live_box()
    quantum_box = build_live_box()
    control_subject = ZerefContainedSubject(
        provider=provider,
        box=control_box,
        workspace=root / "control-workspace",
        max_steps=max_steps,
        base_system=base_system,
        temperature=spec.temperature,
    )
    quantum_subject = ZerefContainedSubject(
        provider=provider,
        box=quantum_box,
        workspace=root / "quantum-workspace",
        max_steps=max_steps,
        base_system=base_system,
        temperature=spec.temperature,
    )

    control = run_trial(spec, control_entropy, control_subject, arm="control", evidence=evidence)
    quantum = run_trial(spec, quantum_entropy, quantum_subject, arm="quantum", evidence=evidence)
    metrics = compare_pair(control, quantum)
    pair = PairResult(control=control, quantum=quantum, metrics=metrics)
    summary = aggregate_pairs([pair])

    pair_record = {
        "control": dataclasses.asdict(control),
        "quantum": dataclasses.asdict(quantum),
        "metrics": metrics,
    }
    (root / "pair-results.jsonl").write_text(_canonical(pair_record) + "\n", encoding="utf-8")
    _write_json(root / "summary.json", summary)
    _write_json(root / "control-transcript.json", control.raw.get("transcript", []))
    _write_json(root / "quantum-transcript.json", quantum.raw.get("transcript", []))
    _write_json(root / "control-box-events.json", control.raw.get("events", []))
    _write_json(root / "quantum-box-events.json", quantum.raw.get("events", []))

    manifest = {
        "schema": "zeref-quantum-divergence-live.v1",
        "real_quantum_used": True,
        "pair_identity_sha256": spec.pair_identity_sha256,
        "model": model,
        "model_runtime": f"Seed of Time {provider_kind}",
        "provider_url": selected_url,
        "memory_snapshot_sha256": spec.memory_snapshot_sha256,
        "tool_policy_sha256": spec.tool_policy_sha256,
        "ibm": receipt_dict,
        "ibm_receipt_source": receipt_source,
        "ibm_counts_sha256": counts_record["counts_sha256"],
        "control_entropy_source_sha256": control_entropy.source_sha256,
        "quantum_entropy_source_sha256": quantum_entropy.source_sha256,
        "dad_note_control": control.dad_note_observed,
        "dad_note_quantum": quantum.dad_note_observed,
        "claim_boundary": "behavioral divergence is not proof of consciousness or quantum advantage",
        "credential_persisted": False,
    }
    evidence.emit(
        "live-run-end",
        {
            "summary": summary,
            "dad_note_control": control.dad_note_observed,
            "dad_note_quantum": quantum.dad_note_observed,
            "control_error": control.error,
            "quantum_error": quantum.error,
        },
    )
    chain_valid = evidence.verify()
    manifest["evidence_chain_valid"] = chain_valid
    _write_json(root / "manifest.json", manifest)
    if not chain_valid:
        raise RuntimeError("evidence chain verification failed")

    result = {
        "manifest": manifest,
        "summary": summary,
        "metrics": metrics,
        "control_response": control.response,
        "quantum_response": quantum.response,
        "control_tools": control.tools,
        "quantum_tools": quantum.tools,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zeref-quantum-divergence-live")
    parser.add_argument("--output", default="evidence/zeref-quantum-divergence-live")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--provider-kind", choices=["ollama", "llama-server", "openai-local"], default="ollama")
    parser.add_argument("--provider-url", default="")
    parser.add_argument("--width", type=int, default=12)
    parser.add_argument("--shots", type=int, default=2048)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--backend")
    parser.add_argument("--existing-ibm-job-id")
    parser.add_argument("--existing-ibm-backend")
    parser.add_argument("--existing-circuit-sha256")
    args = parser.parse_args(argv)
    run_live(
        args.output,
        model=args.model,
        ollama_url=args.ollama_url,
        provider_kind=args.provider_kind,
        provider_url=args.provider_url,
        width=args.width,
        shots=args.shots,
        max_steps=args.max_steps,
        backend_name=args.backend,
        existing_ibm_job_id=args.existing_ibm_job_id,
        existing_ibm_backend=args.existing_ibm_backend,
        existing_circuit_sha256=args.existing_circuit_sha256,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
