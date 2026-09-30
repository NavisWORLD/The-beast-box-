"""Lossless Unicode text indexing shared by memory, R12 and provenance.

Persistent text is NEVER transliterated or stripped. Normalization is applied
only to comparison keys. Native model-tokenizer representability is a separate
provider capability: the host must never silently discard unsupported glyphs.
This is deterministic standard-library Unicode indexing, NOT multilingual
embeddings or language-agnostic semantic comprehension.
"""
from __future__ import annotations

import re
import unicodedata

_ASCII_TOKENS = re.compile(r"[A-Za-z0-9_']+")


def checked_utf8(value: str, *, label: str = "text") -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be Unicode text")
    try:
        return value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} contains an invalid unpaired Unicode surrogate") from exc


def canonical_text(value: str) -> str:
    """NFC preserves text semantics, accents, emoji joiners and script forms.

    Deliberately not NFKC: mathematical symbols, fullwidth text and styled
    characters are not flattened into other owner-authored text.
    """
    checked_utf8(value)
    return unicodedata.normalize("NFC", value)


def _cjk(char: str) -> bool:
    point = ord(char)
    return (
        0x3400 <= point <= 0x9FFF
        or 0xF900 <= point <= 0xFAFF
        or 0x20000 <= point <= 0x3134F
        or 0x3040 <= point <= 0x30FF
        or 0xAC00 <= point <= 0xD7AF
    )


def unicode_terms(value: str) -> list[str]:
    """Unaccented/RTL/CJK/emoji-aware deterministic *lexical* index tokens.

    Preserve the existing exact ASCII lexer on all-ASCII strings so legacy
    English lexical/Hebbian behavior and frozen score contracts do not drift.
    CJK substring matching gets character and adjacent-bigram keys; these are
    lexical conveniences, not a trained segmentation model. Whole joined emoji
    symbols are retained as one token, including modifiers and ZWJ sequences.
    """
    text = canonical_text(value)
    if text.isascii():
        return [match.group(0).lower() for match in _ASCII_TOKENS.finditer(text)]
    normalized = unicodedata.normalize("NFC", text.casefold())
    result: list[str] = []
    buf = ""
    kind: str | None = None

    def emit():
        nonlocal buf, kind
        if not buf:
            return
        result.append(buf)
        if kind == "cjk" and len(buf) > 1:
            # All shorter contiguous combinations let "东京" match "东京站".
            result.extend(buf[index] for index in range(len(buf)))
            result.extend(buf[index:index + 2] for index in range(len(buf) - 1))
        buf = ""
        kind = None

    index = 0
    while index < len(normalized):
        char = normalized[index]
        category = unicodedata.category(char)
        if char in {"'", "’"} and kind == "word" and index + 1 < len(normalized):
            following = unicodedata.category(normalized[index + 1])
            if following[0] in "LNM":
                buf += char
                index += 1
                continue
        if char == "_" or category[0] in "LNM":
            # Join script-specific combining marks to their base. Do not split
            # a Devanagari/Arabic word on vowel marks or a Vietnamese accent.
            target = "cjk" if _cjk(char) else "word"
            if category[0] == "M" and kind in {"word", "cjk"}:
                target = kind
            if kind != target:
                emit()
            kind = target
            buf += char
        elif category[0] == "S" or char in {"\u200d", "\ufe0e", "\ufe0f"}:
            # Emoji pictographs + joined sequences (and regional-flag pairs)
            # remain indexable without discarding ZWJ or skin-tone modifiers.
            if kind != "symbol":
                emit()
            kind = "symbol"
            buf += char
        else:
            emit()
        index += 1
    emit()
    return result
