"""Owner feed ingestion: one committed file becomes a stream of RECORDED sensor snapshots.

Cory (NavisWORLD) commits a text file to ``zeref/feed/owner/``. This module
decouples it into token-bounded chunks and runs each chunk, one tick at a
time, through the public 12-scalar reference dynamic (``beastbox.dyn12``).
Each tick writes one snapshot: the chunk, its measured text features (the
"sensor" reading), the 12D state after the tick, and an append-only hash
chain entry that links back to the previous tick.

What this is, honestly:
- An unbounded input stream folded into a fixed-size state. A file of any
  length is absorbed over as many ticks as it needs; no single tick ever
  holds more than ``MAX_CHUNK_BYTES``. It is NOT literal infinite context:
  the 12D state is a lossy fixed-size summary and the chain keeps the rest.
- Features are measured from the text (counts and ratios). Nothing random,
  no model call, no quantum device.
- The output is a CANDIDATE. ``training_eligible`` is false. It can reach a
  training round only through Cory's fair-gate decision and the unchanged
  G1-G10 gates. This module never writes to any training mix.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

from .dyn12 import update_dyn12
from .hashutil import canonical_json, sha256_obj, sha256_text

SCHEMA = "zeref-owner-feed-snapshot-v1"
CHAIN_SCHEMA = "zeref-owner-feed-chain-v1"
MANIFEST_SCHEMA = "zeref-owner-feed-manifest-v1"
# The bridge's context-contract text cap (beastbox/guest_hebbian.MAX_TEXT_WITH_CONTEXT):
# one tick never carries more text than one guest message may.
MAX_CHUNK_BYTES = 1200
MAX_FILE_BYTES = 2_000_000
ALLOWED_SUFFIXES = (".txt", ".md")
OWNER_LOGIN = "NavisWORLD"
GENESIS_STATE = [0.0] * 12
GENESIS_HASH = "0" * 64
FEATURES = (
    "bytes", "words", "mean_word_len", "sentences", "mean_sentence_words", "unique_word_ratio",
    "punctuation_density", "question_ratio", "exclaim_ratio", "uppercase_ratio", "digit_ratio", "quote_density",
)
LABELS = {
    "snapshot": "RECORDED sensor snapshot: features measured from the owner's committed text; 12D state from the public dyn12 reference dynamic",
    "stream": "Unbounded stream folded into a fixed-size 12D state over many ticks; not literal infinite context",
    "training": "CANDIDATE only: training_eligible:false until Cory's fair-gate decision; G1-G10 unchanged",
    "heartbeat": "SIMULATED", "ibm": "RECORDED seed", "rigetti": "SIMULATED", "local": "LOCAL SIMULATED",
}
_SENT = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+")
_WORD = re.compile(r"[\w'’-]+", re.UNICODE)


def normalize(text: str) -> str:
    """NFC, unify newlines, strip trailing spaces, collapse blank-line runs to one paragraph break."""
    t = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [ln.strip() for ln in t.split("\n")]
    paras, cur = [], []
    for ln in lines:
        if ln:
            cur.append(ln)
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(re.sub(r"[ \t]+", " ", p) for p in paras)


def _nbytes(s: str) -> int:
    return len(s.encode("utf-8"))


def _split_long(piece: str, cap: int) -> list[str]:
    """Split one over-cap sentence at word boundaries; a single over-cap word at character boundaries."""
    out, cur = [], ""
    for word in piece.split(" "):
        while _nbytes(word) > cap:
            cut = len(word)
            while _nbytes(word[:cut]) > cap:
                cut -= 1
            if cur:
                out.append(cur); cur = ""
            out.append(word[:cut]); word = word[cut:]
        cand = (cur + " " + word) if cur else word
        if _nbytes(cand) <= cap:
            cur = cand
        else:
            out.append(cur); cur = word
    if cur:
        out.append(cur)
    return [p for p in out if p]


def chunk_text(text: str, cap: int = MAX_CHUNK_BYTES) -> list[str]:
    """Pack whole sentences into chunks of at most ``cap`` UTF-8 bytes, keeping paragraph breaks inside a chunk."""
    if cap < 16:
        raise ValueError("chunk cap too small")
    chunks: list[str] = []
    cur = ""
    for para in normalize(text).split("\n\n"):
        sents = [s.strip() for s in _SENT.split(para) if s.strip()]
        first = True
        for s in sents:
            pieces = _split_long(s, cap) if _nbytes(s) > cap else [s]
            for p in pieces:
                sep = ("\n\n" if first else " ") if cur else ""
                cand = cur + sep + p
                if _nbytes(cand) <= cap:
                    cur = cand
                else:
                    chunks.append(cur); cur = p
                first = False
    if cur:
        chunks.append(cur)
    assert all(0 < _nbytes(c) <= cap for c in chunks)
    return chunks


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def sense(chunk: str) -> dict[str, float]:
    """Twelve measured text features, each scaled to [0, 1]. Counts and ratios only."""
    words = _WORD.findall(chunk)
    nw = len(words)
    letters = [c for c in chunk if c.isalpha()]
    sents = [s for s in _SENT.split(chunk.replace("\n\n", " ")) if s.strip()] or [chunk]
    ns = len(sents)
    nchar = max(1, len(chunk))
    punct = sum(1 for c in chunk if unicodedata.category(c).startswith("P"))
    raw = {
        "bytes": _nbytes(chunk) / MAX_CHUNK_BYTES,
        "words": nw / 250.0,
        "mean_word_len": (sum(len(w) for w in words) / nw / 10.0) if nw else 0.0,
        "sentences": ns / 20.0,
        "mean_sentence_words": (nw / ns) / 40.0,
        "unique_word_ratio": (len({w.lower() for w in words}) / nw) if nw else 0.0,
        "punctuation_density": punct / nchar * 10.0,
        "question_ratio": chunk.count("?") / ns,
        "exclaim_ratio": chunk.count("!") / ns,
        "uppercase_ratio": (sum(1 for c in letters if c.isupper()) / len(letters) * 5.0) if letters else 0.0,
        "digit_ratio": sum(1 for c in chunk if c.isdigit()) / nchar * 10.0,
        "quote_density": sum(chunk.count(q) for q in "\"“”") / nchar * 50.0,
    }
    return {k: round(_clip01(raw[k]), 6) for k in FEATURES}


def drive_from(features: dict[str, float]) -> list[float]:
    """Map the [0, 1] features to the [-1, 1] drive the 12D dynamic takes, in FEATURES order."""
    return [round(2.0 * features[k] - 1.0, 6) for k in FEATURES]


def entry_hash(entry: dict[str, Any]) -> str:
    return sha256_obj({k: v for k, v in entry.items() if k != "hash"})


def verify_chain(entries: Iterable[dict[str, Any]]) -> dict[str, Any]:
    prev, n = GENESIS_HASH, 0
    for e in entries:
        if e.get("schema") != CHAIN_SCHEMA or e.get("seq") != n or e.get("prev_hash") != prev or entry_hash(e) != e.get("hash"):
            return {"ok": False, "broken_at": n}
        prev, n = e["hash"], n + 1
    return {"ok": True, "entries": n, "head": prev}


def ingest(text: str, *, path: str, commit_sha: str, author_login: str, chain: list[dict[str, Any]],
           ingested_at: str) -> dict[str, Any]:
    """Absorb one owner file. Returns {"manifest", "snapshots", "chain_entries"}; never mutates ``chain``.

    ``chain`` is the existing append-only chain (all earlier files). The 12D state continues from its
    last entry, so every file folds into the same fixed-size state. A file whose sha256 already sits in
    the chain is not ingested twice (manifest status "already_ingested").
    """
    if author_login != OWNER_LOGIN:
        raise PermissionError("owner feed accepts commits by NavisWORLD only")
    if not path.startswith("zeref/feed/owner/") or not path.lower().endswith(ALLOWED_SUFFIXES):
        raise ValueError("owner feed takes .txt or .md files under zeref/feed/owner/")
    raw = text.encode("utf-8")
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("owner feed file exceeds the size limit")
    check = verify_chain(chain)
    if not check["ok"]:
        raise ValueError("existing owner feed chain does not verify at entry %s" % check["broken_at"])
    file_sha = sha256_text(text)
    base = {"schema": MANIFEST_SCHEMA, "path": path, "file_sha256": file_sha, "commit_sha": commit_sha,
            "author_login": author_login, "ingested_at": ingested_at, "training_eligible": False,
            "fair_gate": "pending", "labels": LABELS, "max_chunk_bytes": MAX_CHUNK_BYTES}
    if any(e.get("file_sha256") == file_sha for e in chain):
        return {"manifest": {**base, "status": "already_ingested", "snapshots": 0}, "snapshots": [], "chain_entries": []}
    state = list(chain[-1]["state_after"]) if chain else list(GENESIS_STATE)
    prev = chain[-1]["hash"] if chain else GENESIS_HASH
    seq = len(chain)
    state_before_file = list(state)
    snaps, entries = [], []
    for i, chunk in enumerate(chunk_text(text)):
        feats = sense(chunk)
        drive = drive_from(feats)
        state = [round(x, 9) for x in update_dyn12(state, drive, step=seq)]
        chunk_sha = sha256_text(chunk)
        snap = {"schema": SCHEMA, "file_sha256": file_sha, "chunk_index": i, "tick": seq, "text": chunk,
                "chunk_sha256": chunk_sha, "utf8_bytes": _nbytes(chunk), "words": len(_WORD.findall(chunk)),
                "features": feats, "drive": drive, "state_after": state, "training_eligible": False,
                "label": LABELS["snapshot"]}
        entry = {"schema": CHAIN_SCHEMA, "seq": seq, "prev_hash": prev, "file_sha256": file_sha, "chunk_index": i,
                 "chunk_sha256": chunk_sha, "snapshot_sha256": sha256_obj(snap), "state_after": state}
        entry["hash"] = entry_hash(entry)
        snap["chain_hash"] = entry["hash"]
        snaps.append(snap); entries.append(entry)
        prev, seq = entry["hash"], seq + 1
    manifest = {**base, "status": "ingested", "snapshots": len(snaps), "total_utf8_bytes": len(raw),
                "first_tick": entries[0]["seq"] if entries else None, "last_tick": entries[-1]["seq"] if entries else None,
                "chain_head": prev, "state_before": state_before_file, "state_after": state,
                "largest_chunk_bytes": max((s["utf8_bytes"] for s in snaps), default=0)}
    return {"manifest": manifest, "snapshots": snaps, "chain_entries": entries}


def jsonl(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(canonical_json(r) + "\n" for r in rows)
