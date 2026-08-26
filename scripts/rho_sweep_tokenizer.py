from __future__ import annotations

from typing import Mapping


def sanitize_for_frozen_tokenizer(text: str, stoi: Mapping[str, int]) -> str:
    """Map unsupported retrieved characters to spaces without inventing tokens."""
    replacement = " " if " " in stoi else ""
    cleaned = "".join(ch if ch in stoi else replacement for ch in str(text))
    return " ".join(cleaned.split())
