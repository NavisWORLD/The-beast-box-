from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .hashutil import sha256_obj

AUTHORITY_KEYS = {
    "authority",
    "credentials",
    "shell_access",
    "network_permissions",
    "ibm_token",
    "admin_access",
    "persistent_agent",
    "ibm_account_control",
}


@dataclass
class MissionState:
    mission_id: str
    objective: str
    hypothesis: str = ""
    current_step: int = 0
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    dyn12: list[float] = field(default_factory=lambda: [0.0] * 12)
    phos: float = 0.0
    audio_features: list[float] = field(default_factory=list)
    quantum_spark: list[float] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def digest(self) -> str:
        return sha256_obj(asdict(self))


@dataclass
class StateCapsule:
    schema: str
    state: MissionState
    integrity: str
    stripped_authority: list[str] = field(default_factory=list)

    @classmethod
    def freeze(cls, state: MissionState) -> "StateCapsule":
        payload = {"schema": "beastbox.capsule.v1", "state": asdict(state)}
        return cls(schema=payload["schema"], state=state, integrity=sha256_obj(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "state": asdict(self.state),
            "integrity": self.integrity,
            "stripped_authority": list(self.stripped_authority),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StateCapsule":
        stripped: list[str] = []
        clean = dict(raw)
        for key in list(clean):
            if key in AUTHORITY_KEYS:
                clean.pop(key, None)
                stripped.append(key)

        state_raw = dict(clean.get("state") or {})
        for key in list(state_raw):
            if key in AUTHORITY_KEYS:
                state_raw.pop(key, None)
                stripped.append(f"state.{key}")

        schema = str(clean.get("schema", ""))
        integrity = str(clean.get("integrity", ""))
        if schema != "beastbox.capsule.v1":
            raise ValueError("unsupported capsule schema")

        state = MissionState(**state_raw)
        expected = sha256_obj({"schema": schema, "state": asdict(state)})
        if integrity != expected:
            raise ValueError("capsule integrity mismatch")

        return cls(schema=schema, state=state, integrity=integrity, stripped_authority=stripped)
