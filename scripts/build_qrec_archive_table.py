"""Build the full-loop quantum dice table (v2) from the public archive.

Downloads phera-ra/QC67_cosmo data/quantum_measurements_public.jsonl at the pinned
rev, verifies its sha256, builds the table with beastbox.qrec_sampler, and writes
quantum-dice-table.bin + quantum-record.json into the out dir
(default evidence/zeref-qrec-002). Pure stdlib; takes a few seconds.

    python scripts/build_qrec_archive_table.py [--out evidence/zeref-qrec-002]
    python scripts/build_qrec_archive_table.py --archive /path/to/quantum_measurements_public.jsonl --out /tmp/qrec002

The build is deterministic: the same archive bytes always give the same table sha256.
If the archive ever changes, the table sha will not match the pinned TABLE_SHA256 and
the script fails loudly instead of writing a different table.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from beastbox import qrec_sampler as q  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path("."), help="repo root (default: .)")
    ap.add_argument("--archive", type=Path, default=None, help="local quantum_measurements_public.jsonl (else downloads it)")
    ap.add_argument("--out", type=Path, default=None, help="output dir (default: <repo>/evidence/zeref-qrec-002)")
    args = ap.parse_args()

    repo = args.repo
    out = args.out or repo / "evidence" / "zeref-qrec-002"
    out.mkdir(parents=True, exist_ok=True)

    archive = args.archive
    if archive is None:
        archive = out / "quantum_measurements_public.jsonl"
        url = f"https://huggingface.co/{q.ARCHIVE_REPO}/resolve/{q.ARCHIVE_REV}/{q.ARCHIVE_FILE}"
        print("downloading", url)
        urllib.request.urlretrieve(url, archive)
    got = sha256_file(archive)
    if got != q.ARCHIVE_FILE_SHA256:
        raise SystemExit(f"archive sha mismatch: got {got}, want {q.ARCHIVE_FILE_SHA256}")
    print("archive sha ok:", got)

    records = q.load_archive_records(archive)
    print("records in table:", len(records))
    table = q.build_table_bytes(records)
    table_sha = hashlib.sha256(table).hexdigest()
    if table_sha != q.TABLE_SHA256:
        raise SystemExit(f"table sha mismatch: got {table_sha}, want {q.TABLE_SHA256}")
    print("table sha ok:", table_sha, f"({len(table):,} bytes, {q.TABLE_BITS:,} bits)")

    heart = json.loads((repo / q.HEART_SEED).read_text(encoding="utf-8"))
    rec = q.build_record_v2(heart["heart_seed_sha256"], table_sha)
    (out / "quantum-dice-table.bin").write_bytes(table)
    (out / "quantum-record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out / "quantum-dice-table.bin")
    print("wrote", out / "quantum-record.json", "record seed", rec["record_seed_sha256"])


if __name__ == "__main__":
    main()
