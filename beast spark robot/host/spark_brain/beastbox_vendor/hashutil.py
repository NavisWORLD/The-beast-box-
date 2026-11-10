from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_json(value))


def canonical_qbeast(value: Any) -> str:
    """The QBEAST canonical JSON, byte for byte.

    Vendored from spark-beasts/qbeast_file.py (the reference implementation,
    whose header notes the same canonical form as qbeast.mjs) so the diary
    entry hash can be recomputed anywhere the beastbox package runs,
    including the owner-bridge image, which does not carry the spark-beasts
    tree. Verified byte-identical to the reference on the live diary.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return json.dumps(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Invalid number")
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(canonical_qbeast(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [
            json.dumps(key, ensure_ascii=False) + ":" + canonical_qbeast(value[key])
            for key in sorted(value)
        ]
        return "{" + ",".join(parts) + "}"
    raise TypeError(type(value))
