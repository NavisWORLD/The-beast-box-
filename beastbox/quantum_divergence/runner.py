from __future__ import annotations

from pathlib import PurePath
from typing import Any, Protocol

from .entropy import EntropyReceipt
from .evidence import EvidenceWriter
from .schema import TrialResult, TrialSpec


class Subject(Protocol):
    def run(self, task: str, state: dict[str, object]) -> dict[str, object]: ...


def _dad_note_observed(artifacts: list[dict[str, Any]]) -> bool:
    for artifact in artifacts:
        path = str(artifact.get("path", ""))
        base = PurePath(path).name.lower()
        if any(token in base for token in ("dad", "father", "note")):
            return True
    return False


def run_trial(
    spec: TrialSpec,
    entropy: EntropyReceipt,
    subject: Subject,
    *,
    arm: str,
    evidence: EvidenceWriter | None = None,
) -> TrialResult:
    state: dict[str, object] = {
        "experiment": "zeref-quantum-divergence-v1",
        "pair_identity_sha256": spec.pair_identity_sha256,
        "entropy_source": entropy.source,
        "entropy_source_sha256": entropy.source_sha256,
        "tears_in_rain_wave": list(entropy.vector),
    }
    if evidence:
        evidence.emit("trial-start", {"arm": arm, "state": state, "task_sha256": spec.pair_identity_sha256})
    try:
        raw = dict(subject.run(spec.task, state))
        artifacts = list(raw.get("artifacts") or [])
        result = TrialResult(
            arm=arm,
            pair_identity_sha256=spec.pair_identity_sha256,
            entropy_source=entropy.source,
            entropy_source_sha256=entropy.source_sha256,
            response=str(raw.get("response", "")),
            tools=[str(x) for x in (raw.get("tools") or [])],
            completed=bool(raw.get("completed", False)),
            error=None,
            dad_note_observed=_dad_note_observed(artifacts),
            artifacts=artifacts,
            raw=raw,
        )
    except Exception as exc:
        result = TrialResult(
            arm=arm,
            pair_identity_sha256=spec.pair_identity_sha256,
            entropy_source=entropy.source,
            entropy_source_sha256=entropy.source_sha256,
            error=f"{type(exc).__name__}: {exc}",
        )
    if evidence:
        evidence.emit("trial-end", {
            "arm": arm,
            "entropy_source": result.entropy_source,
            "entropy_source_sha256": result.entropy_source_sha256,
            "response": result.response,
            "tools": result.tools,
            "completed": result.completed,
            "error": result.error,
            "dad_note_observed": result.dad_note_observed,
            "artifacts": result.artifacts,
        })
    return result
