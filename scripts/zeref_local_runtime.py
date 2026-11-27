"""Two-tier runtime for Zeref: browser ONNX lane plus a local high-capacity lane.

The browser lane (scripts/zeref_onnx_export.py, manifest schema
zeref-browser-brain-v1, opset 17) is NOT touched by this module. This module
adds the local tier alongside it: a Jetson / local-GPU profile that loads a
pinned checkpoint by pin step, runs the SAME deterministic SHA-256 chain
verification as the browser lane, and records a runtime receipt.

Chain construction is byte-identical to the repo's own canonical form:
beastbox/hashutil.py canonical_json (json.dumps with sort_keys=True,
separators (",", ":"), ensure_ascii=False) hashed with SHA-256, and the
verify rule mirrors scripts/zeref_self_study.py verify_ledger (each entry
carries prev, hash, and id = hash[:16]; prev starts at "genesis"). Because
both tiers run this exact construction, the chain recomputes identically
anywhere: same entries in, same head hash out. The browser tier and the
local tier differ only in declared capacity, never in chain math.

Additive only. Nothing here changes the pin, any gate, the Talk thread,
S_lived/S_taught counters, R_pin, the held-out hashes, or the film/margin
switches. No torch, no hardware needed: chain verification is pure stdlib.

Evidence taxonomy: IMPLEMENTED = this module and profile exist and run;
MEASURED = the parity test results in tests/test_zeref_runtime_parity.py;
NULL = anything not yet run on real hardware or against the live pinned
checkpoint (see the module docstring notes on the receipt).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    from beastbox.hashutil import canonical_json as _repo_canonical_json
except Exception:  # pragma: no cover - fallback is byte-identical by construction
    _repo_canonical_json = None

CHAIN_SCHEMA = "zeref-runtime-parity-chain-v1"
RECEIPT_SCHEMA = "zeref-runtime-receipt-v1"
PROFILE_SCHEMA = "zeref-local-runtime-profile-v1"
PIN_FILE = "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
LOCAL_PROFILE_FILE = "profiles/zeref-local-high-capacity.json"

# The browser tier, declared here for parity checks only. This module never
# imports or calls the exporter; the values below are the exporter's own
# recorded manifest values (schema zeref-browser-brain-v1, opset 17,
# browser_session_options numThreads 1, float32).
BROWSER_PROFILE = {
    "schema": "zeref-browser-brain-v1",
    "name": "browser-onnx",
    "tier": "browser",
    "device_class": "browser-wasm",
    "provider": "onnxruntime-web-wasm",
    "dtype": "float32",
    "opset": 17,
    "threads": 1,
    "max_parameters": None,
    "export_script": "scripts/zeref_onnx_export.py",
    "note": "Pinned distilled artifact; size is set by the export manifest, not by a parameter budget.",
}

LOCAL_PROFILE_REQUIRED_KEYS = (
    "schema",
    "name",
    "tier",
    "device_class",
    "max_parameters",
    "threads",
    "batch_size",
    "memory_budget_gb",
)


def canonical_json(value: Any) -> str:
    """Canonical JSON, byte-identical to beastbox.hashutil.canonical_json."""
    if _repo_canonical_json is not None:
        return _repo_canonical_json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(value: Any) -> str:
    """SHA-256 of the canonical JSON encoding, as in beastbox.hashutil."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_chain(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a hash chain from ordered payload dicts.

    Each entry carries the payload fields plus schema, prev, hash, and id.
    The hash covers every entry field except hash and id, exactly as
    scripts/zeref_self_study.py build_entry / verify_ledger do.
    """
    entries: list[dict[str, Any]] = []
    prev = "genesis"
    for payload in payloads:
        entry: dict[str, Any] = {"schema": CHAIN_SCHEMA, **payload, "prev": prev}
        entry["hash"] = hashlib.sha256(canonical_json(entry).encode("utf-8")).hexdigest()
        entry["id"] = entry["hash"][:16]
        entries.append(entry)
        prev = entry["hash"]
    return entries


def verify_chain(entries: list[dict[str, Any]]) -> tuple[bool, int, str]:
    """Recompute a hash chain. Returns (ok, entry count, head hash).

    Mirrors scripts/zeref_self_study.py verify_ledger: prev must link,
    hash must recompute over the entry minus hash/id, id must be hash[:16].
    An empty chain verifies with head "genesis". Returns (False, index, head)
    on the first bad entry, where index is the failing entry position.
    """
    prev = "genesis"
    for i, entry in enumerate(entries):
        if entry.get("prev") != prev:
            return False, i, prev
        expect = dict(entry)
        digest = expect.pop("hash", None)
        if digest is None:
            return False, i, prev
        entry_id = expect.pop("id", None)
        recomputed = hashlib.sha256(canonical_json(expect).encode("utf-8")).hexdigest()
        if recomputed != digest or hashlib.sha256(canonical_json(expect).encode("utf-8")).hexdigest()[:16] != entry_id:
            return False, i, prev
        prev = digest
    return True, len(entries), prev


def load_local_profile(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the local high-capacity profile."""
    profile_path = Path(path) if path is not None else REPO / LOCAL_PROFILE_FILE
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    missing = [k for k in LOCAL_PROFILE_REQUIRED_KEYS if k not in profile]
    if missing:
        raise ValueError("local profile %s missing keys: %s" % (profile_path, missing))
    if profile["schema"] != PROFILE_SCHEMA:
        raise ValueError("local profile schema is %r, expected %r" % (profile["schema"], PROFILE_SCHEMA))
    if profile["tier"] != "local":
        raise ValueError("local profile tier is %r, expected 'local'" % profile["tier"])
    return profile


def load_pin(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Load the public pin file (training_steps and checkpoint sha)."""
    root = Path(repo_root) if repo_root is not None else REPO
    pin = json.loads((root / PIN_FILE).read_text(encoding="utf-8"))
    if "training_steps" not in pin or "checkpoint_sha256" not in pin:
        raise ValueError("pin file %s lacks training_steps/checkpoint_sha256" % (root / PIN_FILE))
    return pin


def build_receipt(profile: dict[str, Any], pin: dict[str, Any],
                  entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify a chain under one profile and record a runtime receipt.

    The receipt records the pin step, profile name, chain head hash, entry
    count, and verified flag. It does not move the pin or any gate: it is a
    record of a verification run, not a promotion.
    """
    ok, count, head = verify_chain(entries)
    return {
        "schema": RECEIPT_SCHEMA,
        "profile_name": profile["name"],
        "tier": profile["tier"],
        "device_class": profile["device_class"],
        "pin_step": pin["training_steps"],
        "checkpoint_sha256": pin["checkpoint_sha256"],
        "chain_schema": CHAIN_SCHEMA,
        "chain_head": head,
        "entry_count": count,
        "verified": ok,
    }


def verify_chain_for_profile(profile: dict[str, Any],
                             entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify a chain under a named profile. Same math on every tier."""
    ok, count, head = verify_chain(entries)
    return {
        "profile_name": profile["name"],
        "tier": profile["tier"],
        "device_class": profile["device_class"],
        "chain_head": head,
        "entry_count": count,
        "verified": ok,
    }


def load_chain_file(path: str | Path) -> list[dict[str, Any]]:
    """Load chain entries from a JSON list file or a JSONL file."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        entries = json.loads(text)
    else:
        entries = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(entries, list):
        raise ValueError("chain file must hold a JSON list or JSONL entries")
    return entries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=None, help="local profile JSON (default: profiles/zeref-local-high-capacity.json)")
    ap.add_argument("--pin-file", default=None, help="pin JSON (default: the repo public pin file)")
    ap.add_argument("--chain", default=None, help="chain entries: JSON list file or JSONL file")
    ap.add_argument("--out", default=None, help="write the receipt JSON here (default: print it)")
    a = ap.parse_args(argv)
    profile = load_local_profile(a.profile)
    if a.pin_file is not None:
        pin = json.loads(Path(a.pin_file).read_text(encoding="utf-8"))
    else:
        pin = load_pin()
    entries = load_chain_file(a.chain) if a.chain is not None else []
    receipt = build_receipt(profile, pin, entries)
    text = json.dumps(receipt, sort_keys=True, indent=1) + "\n"
    if a.out is not None:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if receipt["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
