"""Disposable real old-source -> unified-source continuity/backup acceptance.

This script does not access Railway, the owner login, or any owner's data.
Runs old and new source in distinct subprocesses against synthetic records only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OLD_COMMIT = "d1ed41a7dcb7782aa4a9fb8277e4562d7c2189c3"
MARKER = "fixture-only ultraviolet-sapphire-memory-9317"

OLD_RUN = r"""
import json, sys
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
root, receipt = map(Path, sys.argv[1:3])
runtime = DurableRuntime(root, ReferenceTextProvider(prefix="fixture-legacy"))
item = runtime.store_external_memory("fixture-only ultraviolet-sapphire-memory-9317")
runtime.respond("synthetic bridge migration")
inspection = runtime.inspect()
row = runtime.memory.db.execute(
    "SELECT id,text,created_at,metadata_json FROM memories WHERE id=?",
    (item["memory_id"],)
).fetchone()
assert row is not None
receipt.write_text(json.dumps({
    "system_id": inspection["system_id"],
    "checkpoint_sha256": inspection["checkpoint_sha256"],
    "sequence": inspection["sequence"],
    "memory_id": item["memory_id"],
    "row": dict(row)
}, sort_keys=True))
runtime.close()
"""

NEW_RUN = r"""
import json, os, sys
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider

phase, path, receipt, report = sys.argv[1:5]
root, receipt, report = Path(path), Path(receipt), Path(report)
original = json.loads(receipt.read_text())
runtime = DurableRuntime(root, ReferenceTextProvider(prefix="fixture-unified"))
inspection = runtime.inspect()
assert inspection["valid"] is True
assert inspection["system_id"] == original["system_id"]
if phase in ("upgrade", "backup"):
    assert inspection["checkpoint_sha256"] == original["checkpoint_sha256"]
    assert inspection["sequence"] == original["sequence"]
elif phase == "resume":
    previous = json.loads(report.read_text())
    assert inspection["checkpoint_sha256"] == previous["after_archive_sha256"]
else:
    raise ValueError("unexpected recovery phase")
row = runtime.memory.db.execute(
    "SELECT id,text,created_at,metadata_json FROM memories WHERE id=?",
    (original["memory_id"],)
).fetchone()
assert row is not None
assert row["id"] == original["row"]["id"]
assert row["text"] == original["row"]["text"]
assert row["created_at"] == original["row"]["created_at"]
if phase == "upgrade":
    assert any(x.id == original["memory_id"]
               for x in runtime.memory.search("ultraviolet-sapphire-memory-9317"))
    result = runtime.archive_memory(
        original["memory_id"], reviewer="fixture-operator",
        reason="Synthetic owner-reviewed migration archive")
    assert result["changed"] is True
    assert all(x.id != original["memory_id"]
               for x in runtime.memory.search("ultraviolet-sapphire-memory-9317"))
    changed = runtime.inspect()
    assert changed["checkpoint_sha256"] != inspection["checkpoint_sha256"]
    report.write_text(json.dumps({
        "schema": "legacy-unified-memory-recovery-v1",
        "legacy_checkpoint_sha256": original["checkpoint_sha256"],
        "after_archive_sha256": changed["checkpoint_sha256"],
        "system_id_unchanged": True,
        "archived_source_bytes_preserved": True
    }, sort_keys=True))
    # Simulate a killed process: no runtime.close() and no clean shutdown.
    os._exit(0)
if phase == "resume":
    assert all(x.id != original["memory_id"]
               for x in runtime.memory.search("ultraviolet-sapphire-memory-9317"))
    restored = runtime.restore_memory(
        original["memory_id"], reviewer="fixture-operator",
        reason="Explicit synthetic owner restore after abrupt process exit")
    assert restored["changed"] is True
    row2 = runtime.memory.db.execute(
        "SELECT id,text,created_at,metadata_json FROM memories WHERE id=?",
        (original["memory_id"],)
    ).fetchone()
    assert row2["text"] == original["row"]["text"]
    assert row2["created_at"] == original["row"]["created_at"]
    assert any(x.id == original["memory_id"]
               for x in runtime.memory.search("ultraviolet-sapphire-memory-9317"))
    latest = json.loads(report.read_text())
    latest.update({
        "abrupt_restart_verified": True,
        "archive_exclusion_verified": True,
        "explicit_restore_verified": True,
        "restored_source_bytes_preserved": True,
        "post_restore_checkpoint_sha256": runtime.inspect()["checkpoint_sha256"]
    })
    report.write_text(json.dumps(latest, sort_keys=True))
if phase == "backup":
    # A separate untouched backup must still verify the exact old checkpoint.
    print("LEGACY_BACKUP_ORIGINAL_CHECKPOINT_VERIFIED", flush=True)
runtime.close()
"""


def run(script: str, args: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-c", script, *args],
        cwd=cwd, env=env, check=True, timeout=130,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    args.report = args.report.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # No connection secrets or host experimental feature flags enter a fixture.
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith(("BEASTBOX_", "RAWRPHOS_", "OPENAI_", "AZURE_", "HF_")):
            env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="beastbox-migration-") as d:
        work = Path(d)
        old_checkout = work / "legacy-source"
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach",
             str(old_checkout), OLD_COMMIT],
            check=True, timeout=45,
        )
        try:
            old = work / "legacy-state"
            baseline = work / "old-receipt.json"
            run(OLD_RUN, [str(old), str(baseline)], old_checkout, env)
            backup = work / "untouched-backup"
            active = work / "upgrade"
            shutil.copytree(old, backup)
            shutil.copytree(old, active)
            run(NEW_RUN, ["upgrade", str(active), str(baseline),
                          str(args.report)], repo, env)
            run(NEW_RUN, ["resume", str(active), str(baseline),
                          str(args.report)], repo, env)
            run(NEW_RUN, ["backup", str(backup), str(baseline),
                          str(args.report)], repo, env)
            receipt = json.loads(args.report.read_text())
            receipt["untouched_old_backup_reopens_exact_checkpoint"] = True
            receipt["legacy_source_commit"] = OLD_COMMIT
            receipt["no_real_owner_data_or_live_service"] = True
            args.report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            print("LEGACY_TO_UNIFIED_RECOVERY_ACCEPTANCE_PASS")
        finally:
            # Only disposable worktree/files are touched.
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(old_checkout)], check=False, timeout=20)


if __name__ == "__main__":
    main()
