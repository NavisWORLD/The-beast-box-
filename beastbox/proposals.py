from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .hashutil import sha256_obj


@dataclass
class Proposal:
    proposal_id: str
    created_at: float
    title: str
    rationale: str
    target: str
    proposed_content: str
    tests: list[str]
    status: str = "PROPOSED"


class ProposalLane:
    """Approval-gated self-improvement lane.

    It writes proposals to a sandbox directory. It deliberately does not apply
    them to the running core, create persistence, or bypass human review.
    """

    def __init__(self, root: str | Path = ".beastbox/proposals") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def propose(self, title: str, rationale: str, target: str, proposed_content: str, tests: list[str] | None = None) -> Path:
        base = {
            "created_at": time.time(),
            "title": title,
            "rationale": rationale,
            "target": target,
            "proposed_content": proposed_content,
            "tests": list(tests or []),
        }
        proposal = Proposal(proposal_id=sha256_obj(base)[:16], status="PROPOSED", **base)
        path = self.root / f"{proposal.proposal_id}.json"
        path.write_text(json.dumps(asdict(proposal), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def review(self, proposal_id: str, decision: str, note: str = "") -> dict[str, Any]:
        if decision not in {"APPROVE_FOR_MANUAL_APPLICATION", "REJECT"}:
            raise ValueError("decision must be APPROVE_FOR_MANUAL_APPLICATION or REJECT")
        path = self.root / f"{proposal_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["status"] = decision
        raw["review_note"] = note
        path.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")
        return raw
