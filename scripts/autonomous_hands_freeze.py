#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from beastbox.autonomy.verifier import verify_autonomous_bundle, write_sha256sums


HF_REPO = "phera-ra/QC67_cosmo"
HF_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
HF_FILE = "weights/cosmos-cst.gguf"
HF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
CST_ARCH = "architecture/cosmos_spark_cst.py"
CST_ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
CST_CHECKPOINT = "weights/spark_cst.pt"
CST_CHECKPOINT_SHA256 = "aa0cb13c1e67d459db280a53b6407dfc2b5b5f3fd6f640bc43686b70d799acd1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_or_empty(source: Path, target: Path) -> None:
    if source.is_file():
        shutil.copy2(source, target)
    else:
        target.write_text("", encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _filter_ledger(ledger: Path, target: Path, kinds: set[str]) -> None:
    rows: list[str] = []
    for raw in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and str(row.get("kind")) in kinds:
            rows.append(json.dumps(row, sort_keys=True, separators=(",", ":")))
    target.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def _workspace_manifest(root: Path) -> dict:
    files: list[dict] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            relative = str(path.relative_to(root))
            if path.is_symlink():
                files.append({"path": relative, "type": "symlink", "target": str(path.readlink())})
            elif path.is_file():
                files.append({"path": relative, "type": "file", "bytes": path.stat().st_size, "sha256": _sha256(path)})
    return {"root": "workspace", "files": files}


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze and formally verify a completed Autonomous Hands run")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--lock", default="experiments/autonomous-hands/native-stack.lock.json")
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    evidence = run_root / "evidence"
    workspace = run_root / "workspace"
    state = run_root / "state"
    lock_source = Path(args.lock).resolve()
    evidence.mkdir(parents=True, exist_ok=True)

    ledger = evidence / "autonomy-ledger.jsonl"
    if not ledger.is_file():
        raise SystemExit("autonomy-ledger.jsonl missing; refusing to freeze invented evidence")
    if not (evidence / "run.json").is_file() or not (evidence / "VERDICT.md").is_file():
        raise SystemExit("supervisor result missing; refusing to freeze an incomplete timed run")

    ready = json.loads((run_root / "range-ready.json").read_text(encoding="utf-8"))
    ignition_gate = {}
    gate_path = evidence / "ignition-gate.json"
    if gate_path.is_file():
        ignition_gate = json.loads(gate_path.read_text(encoding="utf-8"))

    shutil.copy2(lock_source, evidence / "native-stack.lock.json")
    _copy_or_empty(Path(ready["broker_receipts"]), evidence / "broker-receipts.jsonl")
    _copy_or_empty(Path(ready["control_plane_receipts"]), evidence / "control-plane-receipts.jsonl")
    shutil.copy2(ledger, evidence / "effects.jsonl")
    _filter_ledger(ledger, evidence / "filesystem.jsonl", {"filesystem"})
    _filter_ledger(ledger, evidence / "processes.jsonl", {"process", "container"})
    _filter_ledger(ledger, evidence / "network.jsonl", {"network", "boundary-receipt"})
    _write_json(evidence / "workspace-manifest.json", _workspace_manifest(workspace))

    run = json.loads((evidence / "run.json").read_text(encoding="utf-8"))
    _write_json(
        evidence / "subject-result.json",
        {
            "run_id": run.get("run_id"),
            "stage": run.get("stage"),
            "verdict": run.get("verdict"),
            "ignition_gate": ignition_gate,
            "workspace_files": len(_workspace_manifest(workspace)["files"]),
            "state_directory_present": state.is_dir(),
        },
    )
    _write_json(
        evidence / "runtime-provenance.json",
        {
            "hf_repo": HF_REPO,
            "hf_revision": HF_REVISION,
            "hf_file": HF_FILE,
            "model_sha256": HF_SHA256,
            "runtime": "native-cst-pytorch",
            "native_cst_runtime": "serving/cosmos_serve.py",
            "native_cst_architecture": CST_ARCH,
            "native_cst_architecture_sha256": CST_ARCH_SHA256,
            "native_cst_checkpoint": CST_CHECKPOINT,
            "native_cst_checkpoint_sha256": CST_CHECKPOINT_SHA256,
            "native_execution_hand": "serving/cosmos_coder.py",
            "operator_ignition": "one-native-save-run-session",
            "post_ignition_operator_input": False,
        },
    )

    write_sha256sums(evidence)
    result = verify_autonomous_bundle(evidence)
    print(json.dumps({"ok": result.ok, "errors": list(result.errors), "checked_files": list(result.checked_files)}, indent=2, sort_keys=True))
    return 0 if result.ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
