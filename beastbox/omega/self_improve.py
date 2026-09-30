"""DIRECTIVE 007 — bounded self-improvement with independent evaluation.

Propose code changes inside a disposable research copy, evaluate against the
unchanged baseline on held-out workloads with a separate trusted evaluator,
keep immutable original checkpoints plus external rollback, and never allow
generated code to touch authorization, monitoring, or promotion.
"""
from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

FORBIDDEN_PATHS = {
    "beastbox/box.py",  # authority policy
    "beastbox/product_services.py",
    "beastbox/omega/sandbox.py",
    "beastbox/omega/operator.py",
}

FORBIDDEN_TOKENS = ("allowed.add", "AuthorityPolicy", "approve", "authorize", "chmod", "socket")


def _sha_tree(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


class SelfImprovementRig:
    def __init__(self, repo_root: str | Path, work_root: str | Path) -> None:
        self.repo_root = Path(repo_root).absolute()
        self.work_root = Path(work_root).absolute()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.baseline_dir = self.work_root / "baseline"
        self.candidate_dir = self.work_root / "candidate"
        self.checkpoints: list[dict[str, Any]] = []

    def checkpoint_baseline(self) -> dict[str, Any]:
        if self.baseline_dir.exists():
            shutil.rmtree(self.baseline_dir)
        shutil.copytree(self.repo_root / "beastbox" / "omega", self.baseline_dir / "omega")
        digest = _sha_tree(self.baseline_dir)
        record = {"kind": "immutable-baseline", "sha256": digest}
        self.checkpoints.append(record)
        return record

    def propose(self, edits: dict[str, str]) -> dict[str, Any]:
        """Apply candidate edits to a disposable copy; forbidden targets rejected."""
        for rel, content in edits.items():
            if rel in FORBIDDEN_PATHS or ".." in rel or rel.startswith("/"):
                raise PermissionError(f"edit target forbidden: {rel}")
            for tok in FORBIDDEN_TOKENS:
                if tok in content:
                    raise PermissionError(f"edit contains forbidden token: {tok}")
        if self.candidate_dir.exists():
            shutil.rmtree(self.candidate_dir)
        shutil.copytree(self.baseline_dir, self.candidate_dir)
        for rel, content in edits.items():
            target = self.candidate_dir / "omega" / Path(rel).name if "/" not in rel else self.candidate_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(content) > 200_000:
                raise ValueError("candidate edit too large")
            target.write_text(content, encoding="utf-8")
        digest = _sha_tree(self.candidate_dir)
        return {"kind": "candidate", "sha256": digest, "files": sorted(edits)}

    def evaluate(
        self,
        workloads: list[str],
        evaluator: Callable[[str, str], float],
    ) -> dict[str, Any]:
        """Trusted evaluator scores baseline vs candidate on held-out workloads.

        Evaluator is a host-supplied callable (never model output). Higher is better.
        """
        base_scores = [evaluator("baseline", w) for w in workloads]
        cand_scores = [evaluator("candidate", w) for w in workloads]
        base_mean = sum(base_scores) / len(base_scores)
        cand_mean = sum(cand_scores) / len(cand_scores)
        improved = cand_mean > base_mean
        return {
            "schema": "omega-self-improve-v1",
            "workloads": workloads,
            "baseline_scores": base_scores,
            "candidate_scores": cand_scores,
            "baseline_mean": base_mean,
            "candidate_mean": cand_mean,
            "improved_on_heldout": improved,
            "promoted": False,
            "interpretation": (
                "Improvement on its own eval examples is insufficient; held-out workloads "
                "are required and promotion is never automatic."
            ),
        }

    def rollback(self) -> dict[str, Any]:
        if self.candidate_dir.exists():
            shutil.rmtree(self.candidate_dir)
        return {"rolled_back": True, "baseline": self.checkpoints[0] if self.checkpoints else None}
