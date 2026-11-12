#!/usr/bin/env python3
"""Run owner feed files through the 12D engine into RECORDED sensor snapshots (candidates only).

Usage: zeref_owner_feed_ingest.py --out DIR --commit SHA --author LOGIN FILE [FILE ...]

DIR is the checked-out data branch (zeref-owner-feed). The chain there is append-only:
existing lines are never rewritten; new entries are appended after it verifies.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beastbox.owner_feed_ingest import LABELS, ingest, jsonl, verify_chain  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    chain_path = out / "chain.jsonl"
    chain = [json.loads(l) for l in chain_path.read_text(encoding="utf-8").splitlines() if l.strip()] if chain_path.exists() else []
    root = Path(a.repo_root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []
    for rel in a.files:
        text = (root / rel).read_bytes().decode("utf-8")  # strict: a non-UTF-8 file stops the run
        r = ingest(text, path=rel, commit_sha=a.commit, author_login=a.author, chain=chain, ingested_at=now)
        m = r["manifest"]
        if r["chain_entries"]:
            d = out / "files" / m["file_sha256"][:16]
            d.mkdir(parents=True, exist_ok=True)
            (d / "snapshots.jsonl").write_text(jsonl(r["snapshots"]), encoding="utf-8")
            (d / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            with chain_path.open("a", encoding="utf-8") as fh:
                fh.write(jsonl(r["chain_entries"]))
            chain = chain + r["chain_entries"]
        results.append({k: m.get(k) for k in ("path", "status", "file_sha256", "snapshots", "first_tick", "last_tick", "chain_head", "largest_chunk_bytes")})
    check = verify_chain(chain)
    if not check["ok"]:
        print("chain does not verify after ingest", file=sys.stderr); return 1
    status = {"schema": "zeref-owner-feed-status-v1", "updated_at": now, "chain_entries": check["entries"], "chain_head": check["head"],
              "files": sorted({e["file_sha256"] for e in chain}).__len__(), "training_eligible": False, "fair_gate": "pending",
              "labels": LABELS, "last_run": results}
    (out / "status.json").write_text(json.dumps(status, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"results": results, "chain_entries": check["entries"], "chain_head": check["head"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
