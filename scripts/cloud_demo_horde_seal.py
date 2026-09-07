#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()

    evidence = args.root / "evidence"
    db = args.root / "data/runtime.sqlite3"
    log = evidence / "cloud_requests.jsonl"
    video = evidence / "BEAST_BOX_AI_HORDE_LONG_LIVE.mp4"
    selection_file = evidence / "ai-horde-model-selection.json"

    rows = [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if log.exists() else []
    selection = json.loads(selection_file.read_text(encoding="utf-8")) if selection_file.exists() else {}
    selected_model = selection.get("selected_model")

    receipt = {
        "schema": "beast-box-ai-horde-cloud-live-demo-v1",
        "source_repo": "NavisWORLD/The-beast-box-",
        "source_branch": "experiment/beast-cloud-live-demo-001",
        "source_head_sha": args.source_sha,
        "packaged_artifact_run": 34035894541,
        "packaged_binary_sha256": (evidence / "BEASTBOX_BINARY_SHA256.txt").read_text().split()[0],
        "cloud_provider": "AI Horde anonymous community cloud",
        "provider_endpoint": "https://oai.aihorde.net/v1/chat/completions",
        "model_id": selected_model,
        "api_key_used": False,
        "anonymous_api_key": True,
        "beast_provider_path": "LocalOllamaProvider -> loopback bridge -> AI Horde OpenAI-compatible proxy -> volunteer text worker",
        "literal_gui_recording": video.exists() and video.stat().st_size > 0,
        "cloud_request_count": len(rows),
        "successful_cloud_requests": sum(bool(row.get("success")) for row in rows),
        "all_cloud_requests_success": bool(rows) and all(bool(row.get("success")) for row in rows),
        "distinct_cloud_models_observed": sorted({str(row.get("cloud_model")) for row in rows if row.get("cloud_model")}),
        "process_restart_requested": True,
        "claim_boundary": "This is a software continuity and retrieved-context delivery measurement through a real external cloud model. It does not establish consciousness, superintelligence, biological identity, weight changes, quantum advantage, or new physics.",
    }

    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
        memories = [
            {"id": row[0], "kind": row[1], "text": row[2]}
            for row in con.execute("SELECT id,kind,text FROM memories ORDER BY id")
        ]
        continuity = []
        for seq, payload, checkpoint_sha in con.execute(
            "SELECT sequence,payload,sha256 FROM continuity ORDER BY sequence"
        ):
            obj = json.loads(payload)
            continuity.append({
                "sequence": seq,
                "system_id": obj.get("system_id"),
                "turn": obj.get("state", {}).get("turn"),
                "checkpoint_sha256": checkpoint_sha,
            })
        con.close()
        receipt.update({
            "memory_record_count": len(memories),
            "continuity_checkpoint_count": len(continuity),
            "system_id_stable": len({row["system_id"] for row in continuity}) == 1 if continuity else False,
            "system_id": continuity[-1]["system_id"] if continuity else None,
            "final_turn": continuity[-1]["turn"] if continuity else None,
            "runtime_sqlite_sha256": file_sha(db),
        })
        (evidence / "runtime-memory.json").write_text(
            json.dumps(memories, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (evidence / "continuity.json").write_text(
            json.dumps(continuity, indent=2) + "\n", encoding="utf-8"
        )

    if log.exists():
        receipt["cloud_log_sha256"] = file_sha(log)
    if selection_file.exists():
        receipt["model_selection_sha256"] = file_sha(selection_file)
    if video.exists() and video.stat().st_size:
        receipt["video_sha256"] = file_sha(video)

    (evidence / "RUN_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
