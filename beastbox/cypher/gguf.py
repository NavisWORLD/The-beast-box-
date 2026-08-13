from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any, BinaryIO

_TYPES = {0: ("u8", "<B"), 1: ("i8", "<b"), 2: ("u16", "<H"), 3: ("i16", "<h"), 4: ("u32", "<I"), 5: ("i32", "<i"), 6: ("f32", "<f"), 7: ("bool", "<?"), 8: ("string", None), 9: ("array", None), 10: ("u64", "<Q"), 11: ("i64", "<q"), 12: ("f64", "<d")}


def _read_exact(f: BinaryIO, n: int) -> bytes:
    data = f.read(n)
    if len(data) != n:
        raise ValueError("truncated GGUF file")
    return data


def _u32(f: BinaryIO) -> int:
    return struct.unpack("<I", _read_exact(f, 4))[0]


def _u64(f: BinaryIO) -> int:
    return struct.unpack("<Q", _read_exact(f, 8))[0]


def _string(f: BinaryIO) -> str:
    n = _u64(f)
    if n > 128 * 1024 * 1024:
        raise ValueError("unreasonable GGUF string length")
    return _read_exact(f, n).decode("utf-8", errors="replace")


def _scalar(f: BinaryIO, type_id: int) -> Any:
    if type_id not in _TYPES:
        raise ValueError(f"unknown GGUF metadata type {type_id}")
    _, fmt = _TYPES[type_id]
    if type_id == 8:
        return _string(f)
    if type_id == 9:
        raise ValueError("nested array handler required")
    assert fmt is not None
    return struct.unpack(fmt, _read_exact(f, struct.calcsize(fmt)))[0]


def _read_value(f: BinaryIO, type_id: int, preview_limit: int = 16) -> Any:
    if type_id != 9:
        return _scalar(f, type_id)
    elem_type = _u32(f)
    length = _u64(f)
    preview: list[Any] = []
    for idx in range(length):
        value = _read_value(f, elem_type, preview_limit=preview_limit)
        if idx < preview_limit:
            preview.append(value)
    if length <= preview_limit:
        return preview
    return {"count": length, "preview": preview, "element_type": _TYPES.get(elem_type, (str(elem_type),))[0]}


def inspect_gguf(path: str | Path, *, sha256: bool = False, preview_limit: int = 16) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    with p.open("rb") as f:
        if _read_exact(f, 4) != b"GGUF":
            raise ValueError("not a GGUF file (missing GGUF magic)")
        version = _u32(f)
        tensor_count = _u64(f)
        metadata_count = _u64(f)
        if metadata_count > 5_000_000:
            raise ValueError("unreasonable GGUF metadata count")
        metadata: dict[str, Any] = {}
        for _ in range(metadata_count):
            key = _string(f)
            type_id = _u32(f)
            metadata[key] = _read_value(f, type_id, preview_limit=preview_limit)
    architecture = metadata.get("general.architecture")
    context = metadata.get(f"{architecture}.context_length") if isinstance(architecture, str) else None
    result: dict[str, Any] = {"path": str(p), "bytes": p.stat().st_size, "version": version, "tensor_count": tensor_count, "metadata_count": metadata_count, "name": metadata.get("general.name"), "architecture": architecture, "context_length": context, "tokenizer_model": metadata.get("tokenizer.ggml.model"), "metadata": metadata}
    if sha256:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        result["sha256"] = h.hexdigest()
    return result
