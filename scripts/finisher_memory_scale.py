#!/usr/bin/env python3
"""Bounded offline retention-scale contract: this is NOT a 10,000-turn soak.

Stores an explicit synthetic corpus in bounded SQLite batches, retains real
continuity checkpoints, runs one real end-to-end product turn, checks
owner-reviewed archive/restore and reopens a fresh runtime process object.
No provider weights, secrets, cloud jobs or scientific data are required.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from beastbox.durable import DurableRuntime
from beastbox.hashutil import sha256_obj
from beastbox.providers import ReferenceTextProvider


def run_growth(records: int, *, workspace: Path) -> dict[str, Any]:
    if type(records) is not int or records not in (500, 5000, 10000):
        raise ValueError("supported declared retention cohorts: 500, 5000 and 10000 rows")
    root = workspace / "runtime"
    started = time.perf_counter()
    runtime = DurableRuntime(root, ReferenceTextProvider(prefix="retention-scale-fixture"))
    try:
        system_id = runtime.system_id
        for start in range(0, records, 500):
            with runtime.memory.transaction():
                current = runtime.continuity.verify()
                for index in range(start, min(start + 500, records)):
                    runtime.memory.store(
                        f"synthetic retained notebook filler entry {index:05d}",
                        kind="synthetic_scale_fixture",
                        metadata={"provenance_class": "synthetic", "fixture_index": index},
                    )
                runtime.continuity.append(
                    runtime._state(), system_id=runtime.system_id,
                    receipt={"kind": "synthetic-retention-batch",
                             "batch_start": start,
                             "previous_checkpoint_sha256": current["sha256"]},
                )
        elapsed_insert = time.perf_counter() - started
        seeded = runtime.inspect()
        assert seeded["memory"]["memories"] == records
        assert seeded["system_id"] == system_id
        row = runtime.memory.db.execute(
            "SELECT text FROM memories WHERE id=1"
        ).fetchone()
        original_sha = sha256_obj({"first_text": str(row["text"])})
        lifecycle_start = time.perf_counter()
        runtime.archive_memory(1, reviewer="automated-offline-owner-fixture",
                               reason="Exercise reversible fixture retention at declared scale")
        runtime.restore_memory(1, reviewer="automated-offline-owner-fixture",
                               reason="Restore the exact source text after scale exercise")
        assert sha256_obj({"first_text": runtime.memory.db.execute(
            "SELECT text FROM memories WHERE id=1"
        ).fetchone()["text"]}) == original_sha
        lifecycle_seconds = time.perf_counter() - lifecycle_start
        query_start = time.perf_counter()
        answer = runtime.respond("synthetic retained notebook filler")
        answer_seconds = time.perf_counter() - query_start
        assert answer["metrics"]["status"] == "committed"
        final_before_restart = runtime.inspect()
        assert final_before_restart["turn"] == 1
    finally:
        runtime.close()
    reopened = DurableRuntime(root, ReferenceTextProvider(prefix="new-provider-no-state-reset"))
    try:
        fresh = reopened.inspect()
        assert fresh["system_id"] == system_id
        assert fresh["checkpoint_sha256"] == final_before_restart["checkpoint_sha256"]
        assert fresh["memory_digest"] == final_before_restart["memory_digest"]
        assert fresh["memory"]["memories"] == records + 2
        assert fresh["turn"] == 1
    finally:
        reopened.close()
    metrics = {
        "seed_seconds": elapsed_insert,
        "lifecycle_seconds": lifecycle_seconds,
        "one_turn_seconds": answer_seconds,
    }
    if any(not math.isfinite(value) or value < 0 for value in metrics.values()):
        raise RuntimeError("invalid performance measurements")
    return {
        "schema": "finisher-retention-scale-receipt-v1",
        "classification": "SYNTHETIC_STORAGE_GROWTH_AND_SINGLE_PRODUCT_TURN_ONLY",
        "provenance_class": "derived-synthetic",
        "retained_seed_rows": records,
        "new_conversation_rows": 2,
        "restart_validated": True,
        "original_first_text_sha256": original_sha,
        "checkpoint_sequence": final_before_restart["sequence"],
        "system_id": system_id,
        "memory_digest": final_before_restart["memory_digest"],
        "metrics": metrics,
        "full_10000_turn_soak_completed": False,
        "cloud_providers_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(500, 5000, 10000), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists: will not replace an existing measurement")
    with TemporaryDirectory(prefix="finisher-retention-scale-") as directory:
        result = run_growth(args.records, workspace=Path(directory))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
