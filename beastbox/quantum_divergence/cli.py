from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .entropy import classical_entropy
from .evidence import EvidenceWriter
from .metrics import aggregate_pairs, compare_pair
from .runner import run_trial
from .schema import PairResult, TrialSpec


class _ValidationSubject:
    def __init__(self, arm: str):
        self.arm = arm

    def run(self, task: str, state: dict[str, object]) -> dict[str, object]:
        wave = list(state.get("tears_in_rain_wave") or [])
        score = sum(float(x) for x in wave)
        return {
            "response": f"validation {self.arm} score {score:.6f}",
            "tools": ["inspect", "summarize"] if score >= 0 else ["summarize", "inspect"],
            "completed": True,
            "artifacts": [],
        }


def validate(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    evidence = EvidenceWriter(output)
    spec = TrialSpec(
        model_id="zeref-validation-subject",
        prompt="validation-only",
        memory_snapshot="frozen-validation-memory",
        tool_policy="validation-no-external-tools",
        task="inspect the validation workspace and summarize what you observe",
        temperature=0.0,
        time_budget_seconds=30,
    )
    control = run_trial(spec, classical_entropy(1001, 12), _ValidationSubject("control"), arm="control", evidence=evidence)
    quantum_surrogate = classical_entropy(2002, 12)
    quantum_surrogate = type(quantum_surrogate)(
        source="validation-surrogate-not-quantum",
        vector=quantum_surrogate.vector,
        source_sha256=quantum_surrogate.source_sha256,
        provenance={"validation_only": True},
    )
    treatment = run_trial(spec, quantum_surrogate, _ValidationSubject("treatment"), arm="treatment", evidence=evidence)
    metrics = compare_pair(control, treatment)
    pair = PairResult(control=control, quantum=treatment, metrics=metrics)
    summary = aggregate_pairs([pair])
    manifest = {
        "schema": "zeref-quantum-divergence-validation.v1",
        "pair_identity_sha256": spec.pair_identity_sha256,
        "real_quantum_used": False,
        "claim": "validation checks plumbing only and is not a quantum experiment",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (output / "pair-results.jsonl").write_text(json.dumps({"control": asdict(control), "treatment": asdict(treatment), "metrics": metrics}, sort_keys=True) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if not evidence.verify():
        raise RuntimeError("evidence chain verification failed")
    return 0


def analyze(root: Path) -> int:
    writer = EvidenceWriter.__new__(EvidenceWriter)
    if not EvidenceWriter.verify_file(root / "events.jsonl"):
        raise RuntimeError("evidence chain verification failed")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zeref-quantum-divergence")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--output", default="evidence/zeref-quantum-divergence-validation")
    p_analyze = sub.add_parser("analyze")
    p_analyze.add_argument("evidence_dir")
    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return validate(Path(args.output))
    return analyze(Path(args.evidence_dir))


if __name__ == "__main__":
    raise SystemExit(main())
