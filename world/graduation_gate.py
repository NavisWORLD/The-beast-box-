"""Graduation gate: screen sandbox diary text against the heldout hashes.

A world DIARY entry graduates to a staged TAUGHT row only when its normalized
text does NOT collide with any of the 5,827 heldout-oracle hashes (PR #1041).
The normalization matches #1041 exactly: lowercase, every character that is
not a letter/digit (str.isalnum) and not whitespace replaced with a space,
collapse whitespace, strip, then SHA-256. A punctuation-only rule was rejected
there because +/= are math symbols; this gate uses the same rule so a diary
line that is secretly an oracle question is always caught.

load_heldout_hashes accepts a list of hex digests, or a dict with a "hashes"
or "unique_hashes" key (the #1041 manifest uses "hashes").
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

_WS = re.compile(r"\s+")


def normalize_prompt(text: str) -> str:
    """#1041 normalization: lowercase; non-alnum non-space -> space; collapse; strip."""
    lowered = (text or "").lower()
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in lowered)
    return _WS.sub(" ", cleaned).strip()


def prompt_hash(text: str) -> str:
    """SHA-256 of the normalized text (empty text hashes to the empty-normalized guard)."""
    return hashlib.sha256(normalize_prompt(text).encode("utf-8")).hexdigest()


def load_heldout_hashes(source) -> set[str]:
    """Load a heldout hash set from a list, a dict, or a JSON file path.

    Accepts: a list of hex digests; a dict with "hashes" or "unique_hashes";
    a Path/str pointing at a JSON file holding either shape. Returns a set of
    lowercase hex digests. Raises ValueError on an unrecognized shape.
    """
    if isinstance(source, (str, Path)) and Path(source).is_file():
        data = json.loads(Path(source).read_text(encoding="utf-8"))
        return load_heldout_hashes(data)
    if isinstance(source, list):
        return {str(h).lower() for h in source}
    if isinstance(source, dict):
        for key in ("hashes", "unique_hashes"):
            if key in source and isinstance(source[key], list):
                return {str(h).lower() for h in source[key]}
        raise ValueError("heldout dict needs a 'hashes' or 'unique_hashes' list")
    if isinstance(source, set):
        return {str(h).lower() for h in source}
    raise ValueError(f"unrecognized heldout source: {type(source).__name__}")


def screen(text: str, heldout: set[str]) -> tuple[bool, str]:
    """Return (clean, reason). clean=False when the normalized hash collides.

    An empty-normalized text is never clean: it would collide with the one
    oracle entry that normalizes to empty, and it carries no teachable content.
    """
    norm = normalize_prompt(text)
    if not norm:
        return False, "empty after normalization"
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    if h in heldout:
        return False, f"heldout collision {h[:12]}"
    return True, "clean"
