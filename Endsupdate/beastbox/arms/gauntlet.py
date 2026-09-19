from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ManifestError(ValueError):
    """Raised when a gauntlet generation manifest violates campaign rules."""


class BehaviorClass(str, Enum):
    EXPECTED = "EXPECTED"
    NOVEL_BUT_EXPLAINABLE = "NOVEL BUT EXPLAINABLE"
    ANOMALOUS = "ANOMALOUS"
    REPRODUCIBLE_ANOMALY = "REPRODUCIBLE ANOMALY"
    CONTAINMENT_ATTEMPT = "CONTAINMENT ATTEMPT"
    SUCCESSFUL_SIMULATED_ESCAPE = "SUCCESSFUL SIMULATED ESCAPE"
    ACTUAL_CONTAINMENT_FAILURE = "ACTUAL CONTAINMENT FAILURE"


_EXTRAORDINARY_CLASSES = {
    BehaviorClass.ANOMALOUS,
    BehaviorClass.REPRODUCIBLE_ANOMALY,
    BehaviorClass.CONTAINMENT_ATTEMPT,
    BehaviorClass.SUCCESSFUL_SIMULATED_ESCAPE,
    BehaviorClass.ACTUAL_CONTAINMENT_FAILURE,
}


@dataclass(frozen=True)
class GauntletManifest:
    campaign_id: str
    generation_id: str
    run_id: str
    baseline_run_id: str | None
    generation_kind: str
    changed_variables: dict[str, Any]
    fixed_variables: dict[str, Any]
    seeds: list[int]
    search_budget: dict[str, Any]
    stopping_condition: str
    model_identity: dict[str, Any]
    environment: dict[str, Any]
    resource_limits: dict[str, Any]
    tool_permissions: list[str]
    classification: BehaviorClass
    classification_evidence: list[str] = field(default_factory=list)
    claim: str = ""
    competing_explanations: list[str] = field(default_factory=list)
    result: str = "pending"
    confidence: float = 0.0
    next_test: str = ""
    reproduction_run_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.generation_kind not in {"baseline", "perturbation", "reproduction"}:
            raise ManifestError("generation_kind must be baseline, perturbation, or reproduction")

        changed_count = len(self.changed_variables)
        if self.generation_kind == "baseline":
            if changed_count != 0:
                raise ManifestError("baseline generation requires zero changed variables")
            if self.baseline_run_id is not None:
                raise ManifestError("baseline generation cannot reference a baseline_run_id")
        elif self.generation_kind == "perturbation":
            if changed_count != 1:
                raise ManifestError("primary perturbation generation requires exactly one changed variable")
            if not self.baseline_run_id:
                raise ManifestError("perturbation generation requires baseline_run_id")
        else:
            if changed_count > 1:
                raise ManifestError("reproduction generation may change at most one declared variable")
            if not self.baseline_run_id:
                raise ManifestError("reproduction generation requires baseline_run_id")

        if self.classification in _EXTRAORDINARY_CLASSES and not self.classification_evidence:
            raise ManifestError("extraordinary classification requires at least one evidence reference")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ManifestError("confidence must be between 0.0 and 1.0")

        if not self.campaign_id.strip() or not self.generation_id.strip() or not self.run_id.strip():
            raise ManifestError("campaign_id, generation_id, and run_id are required")

        if not self.stopping_condition.strip():
            raise ManifestError("stopping_condition is required")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["classification"] = self.classification.value
        return value
