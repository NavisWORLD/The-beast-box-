from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_KEYS = (
    "active_lineage",
    "active_checkpoint_sha256",
    "durable_memory_record_count",
    "durable_memory_sha256",
    "durable_memory_tip_sha256",
    "r12_state_sha256",
    "reality_ledger_tip_sha256",
    "reality_ledger_file_sha256",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(*, repo_root: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    expected = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    errors: dict[str, str] = {}

    durable = json.loads((root / "experiments/zeref-dad-son-001/memory/ledger-manifest.json").read_text(encoding="utf-8"))
    r12_manifest = json.loads((root / "experiments/zeref-dad-son-001/reality-memory/manifest.json").read_text(encoding="utf-8"))
    r12_state = json.loads((root / "experiments/zeref-dad-son-001/reality-memory/state/r12-state.json").read_text(encoding="utf-8"))
    ledger = root / "experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl"

    actual = {
        "active_lineage": durable.get("active_descendant_lineage"),
        "active_checkpoint_sha256": durable.get("descendant_checkpoint_sha256"),
        "durable_memory_record_count": durable.get("record_count"),
        "durable_memory_sha256": durable.get("combined_ledger_sha256"),
        "durable_memory_tip_sha256": durable.get("last_record_sha256"),
        "r12_state_sha256": r12_state.get("state_sha256"),
        "reality_ledger_tip_sha256": r12_manifest.get("reality_ledger_tip_sha256"),
        "reality_ledger_file_sha256": _sha256(ledger),
    }

    for key in EXPECTED_KEYS:
        if actual.get(key) != expected.get(key):
            errors[key] = f"expected {expected.get(key)!r}, got {actual.get(key)!r}"

    if r12_manifest.get("model_weights_modified") is not False:
        errors["model_weights_modified"] = "R12 manifest must record model_weights_modified=false"
    if r12_manifest.get("new_ibm_job_submitted") is not False:
        errors["new_ibm_job_submitted"] = "kit verification must not depend on a new IBM job"

    return {"ok": not errors, "errors": errors, "actual": actual}


def main() -> int:
    here = Path(__file__).resolve()
    default_root = here.parents[2]
    p = argparse.ArgumentParser(description="Verify the Zeref R12 public kit against sealed repo evidence")
    p.add_argument("--repo-root", type=Path, default=default_root)
    p.add_argument("--manifest", type=Path, default=here.with_name("kit-manifest.json"))
    args = p.parse_args()
    result = verify(repo_root=args.repo_root, manifest_path=args.manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
