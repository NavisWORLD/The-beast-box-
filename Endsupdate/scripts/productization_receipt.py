from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ANCHOR_SHA = "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f"
CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
SEALED_EVIDENCE_PATH = "evidence/final-whole-organism-001/"
SUPPORTED_BACKENDS = [
    "ollama",
    "gguf",
    "llama.cpp-server",
    "lm-studio",
    "openai-compatible",
]
HASHED_PUBLIC_FILES = [
    "QUANTUM_BEAST_STARTER/README.md",
    "QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md",
    "QUANTUM_BEAST_STARTER/config/beastbox.example.json",
    "QUANTUM_BEAST_STARTER/docker-compose.yml",
    "README.md",
]


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_snapshot(root: Path, revision: str, prefix: str) -> dict[str, tuple[str, str]] | None:
    """Return path-relative (mode, blob) pairs. No file content is modified."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", revision, "--", prefix],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    found: dict[str, tuple[str, str]] = {}
    for item in result.stdout.split(b"\x00"):
        if not item:
            continue
        metadata, path = item.split(b"\t", 1)
        mode, kind, sha = metadata.decode("ascii").split()
        if kind != "blob":
            return None
        relative = path.decode("utf-8").removeprefix(prefix)
        found[relative] = (mode, sha)
    return found


def sealed_evidence_unchanged(repo_root: Path) -> bool:
    """Guard original evidence AND compare the copied blob identities.

    When executed within Endsupdate, using the original relative path against
    its own cwd would classify the new copy as a change to historical evidence.
    That was a false negative, not a reason to weaken the evidence guard.
    """
    if repo_root.name != "Endsupdate":
        result = subprocess.run(
            ["git", "diff", "--quiet", ANCHOR_SHA, "--", SEALED_EVIDENCE_PATH],
            cwd=repo_root,
            check=False,
        )
        return result.returncode == 0
    host_root = repo_root.parent
    original_unchanged = subprocess.run(
        ["git", "diff", "--quiet", ANCHOR_SHA, "HEAD", "--", SEALED_EVIDENCE_PATH],
        cwd=host_root,
        check=False,
    ).returncode == 0
    original = _git_snapshot(host_root, "8f90e440f0f4ceba502b1a3f8637507491fb23b0", SEALED_EVIDENCE_PATH)
    copied = _git_snapshot(host_root, "HEAD", "Endsupdate/" + SEALED_EVIDENCE_PATH)
    return original_unchanged and bool(original) and original == copied


def current_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def build_receipt(repo_root: Path, head_sha: str) -> dict[str, object]:
    file_hashes: dict[str, str] = {}
    for relative in HASHED_PUBLIC_FILES:
        path = repo_root / relative
        if path.is_file():
            file_hashes[relative] = hash_file(path)

    return {
        "scientific_anchor": ANCHOR_SHA,
        "scientific_classification": CLASSIFICATION,
        "productization_commit": head_sha,
        "fresh_ibm_jobs_submitted": False,
        "sealed_evidence_path": SEALED_EVIDENCE_PATH,
        "sealed_evidence_unchanged": sealed_evidence_unchanged(repo_root),
        "supported_model_backends": list(SUPPORTED_BACKENDS),
        "file_sha256": file_hashes,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or verify the Quantum Beast productization receipt")
    parser.add_argument("--check-only", action="store_true", help="fail unless sealed scientific evidence is unchanged")
    parser.add_argument("--head-sha", help="productization commit SHA; defaults to git HEAD")
    parser.add_argument("--out", type=Path, help="write receipt JSON to this path")
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.check_only:
        if not sealed_evidence_unchanged(repo_root):
            print(f"sealed evidence differs from {ANCHOR_SHA}: {SEALED_EVIDENCE_PATH}")
            return 1
        anchor_doc = repo_root / "QUANTUM_BEAST_STARTER" / "SCIENTIFIC_ANCHOR.md"
        if not anchor_doc.is_file():
            print("scientific anchor document missing")
            return 1
        text = anchor_doc.read_text(encoding="utf-8")
        if ANCHOR_SHA not in text or CLASSIFICATION not in text:
            print("scientific anchor document does not match sealed constants")
            return 1
        print("productization scientific anchor guard: PASS")
        return 0

    head_sha = args.head_sha or current_head(repo_root)
    receipt = build_receipt(repo_root, head_sha)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = args.out if args.out.is_absolute() else repo_root / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if receipt["sealed_evidence_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
