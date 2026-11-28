#!/usr/bin/env python3
"""Append-only context-retrieval index over Zeref's growing ledger (TRACK 2).

The self-study loop (scripts/zeref_self_study.py) appends one TAUGHT row
plus one hash-chained ledger entry per study event, forever. A forward pass
cannot hold an unbounded history, so this module is the retrieval layer
that sits between the ledger and the caller: it reads ledger and rows files
WITHOUT modifying them and answers deterministic, token-budget-aware
topic queries over everything learned so far.

What it reads, first hand from main:
  * Taught rows JSONL (zeref/self-study-rows.jsonl): one dict per row,
    {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
    "user": question, "assistant": narration, "origin": url,
    "license": "CC-BY-SA-4.0"} (run() in zeref_self_study.py, lines 604-683).
  * Ledger JSONL (zeref/self-study-ledger.jsonl): hash-chained entries,
    schema "zeref-self-study-ledger/v1", each carrying its taught row
    nested under "taught_row" (or None for a failed attempt), a "status"
    ("studied" or "search_failed:..." / "narration_failed" /
    "screen_blocked:..."), and a "license" (build_entry, lines 533-560).
  * World diary rows: the same user/assistant/license rows-file shape
    produced by scripts/zeref_world_rows.py world_rows(). A diary rows
    file is read through the same rows reader; its rows pass through the
    same license gate below.

Invariants (the index never breaks them, because it never writes):
  * Read-only over the ledger and rows. This module opens files for
    reading only. It never appends, rewrites, reorders, or deletes a
    ledger entry or a taught row, and it never calls run() or narrate().
    Pacing (one event per run, 3600 s cooldown, 12 per day), the
    held-out screen, and the open-license check inside run() are
    untouched: retrieval cannot change what gets studied.
  * No total row ceiling. The index grows unboundedly as rows append.
    There is no MAX_ROWS and no eviction. The only bound is the
    caller's per-query token budget, which limits what one query
    returns, never what the index holds.
  * Deterministic retrieval. Same index plus same query gives the same
    ranked rows, every time: ranking is a fixed score with ties broken
    by append order (sequence number), and the inverted index is only
    a candidate finder, never a source of randomness or ordering.
  * Open-license only. A row is retrievable only when its license
    normalizes to one of CC-BY-SA-4.0, CC0-1.0, or PUBLIC-DOMAIN.
    A missing license, or any other string, excludes the row from
    retrieval and is counted in the stats (see excluded_unlicensed).
    NOTE: the world diary rows produced by world_rows() on main carry
    the license "Beast Box world record (owner's own, same as
    repository)". That string is not one of the three accepted open
    licenses, so diary rows in that form are counted as excluded, not
    indexed. Whether the owner-original diary license should be added
    as a recognized license is an open decision for Cory, not something
    this module decides on its own. A diary rows file whose rows carry
    a recognized open license indexes normally.

How ranking works (fixed, documented, no model involved):
  * Query and row text are tokenized into content words (lowercased
    [a-z0-9']+ tokens, stop words dropped, minimum length 3).
  * Score = 2 * (distinct query words found in the row question) +
    1 * (distinct query words found in the row answer).
  * Ties break by sequence number ascending (earliest appended first).
  * Rows sharing no content word with the query score 0 and are not
    returned.

Token budget (estimate, documented honestly):
  * estimate_tokens(text) counts words and returns ceil(words * 4 / 3),
    the usual 1 token per 0.75 words approximation, plus a 4 token
    per-row framing overhead. It is an estimate, not a tokenizer
    measurement; callers that need an exact count must measure with
    their own tokenizer. The budget is still respected exactly against
    this estimate: tokens_used never exceeds max_tokens.
  * query() walks the ranked rows in order and takes every row that
    fits in the remaining budget, skipping rows that do not fit. Rows
    not returned are reported as leftover, so the caller always knows
    how much matching context was left out.

Consistency as the ledger appends (see docs/ZEREF_LEDGER_INDEX.md):
  * The index keeps, per file, how many lines it has consumed.
    refresh() reads only the new tail lines and appends them; existing
    entries are never re-read, reordered, or rewritten.
  * If a file ever has FEWER lines than the index consumed, refresh()
    raises ValueError and changes nothing: history was rewritten,
    which append-only files must never do. That is a fail-closed
    signal, not something to repair by re-indexing.
  * The ledger hash chain itself is NOT re-verified here; chain
    verification stays with verify_ledger() in zeref_self_study.py.
    This module trusts the files it is given and reports what it read.

Usage:
  python scripts/zeref_ledger_index.py --rows ROWS.jsonl --ledger LEDGER.jsonl
      --query "what is the fort" --max-tokens 200
Stdout is one ZEREF_LEDGER_INDEX=<result json> line.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

OPEN_LICENSES = frozenset({"CC-BY-SA-4.0", "CC0-1.0", "PUBLIC-DOMAIN"})

# Accepted spellings, normalized key -> canonical license. Only these
# spellings map; anything else is unrecognized and excludes the row.
_LICENSE_ALIASES = {
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-sa": "CC-BY-SA-4.0",
    "cc-by-sa-40": "CC-BY-SA-4.0",
    "cc0-1.0": "CC0-1.0",
    "cc0": "CC0-1.0",
    "public-domain": "PUBLIC-DOMAIN",
}

_WORD = re.compile(r"[a-z0-9']+")
_STOP = frozenset(
    "a an the is are was were what who where when why how do does did of in on to and or for with by it its "
    "this that be your you i my me he she they his her their can could would should will shall may might must "
    "which as at from has have had there about tell say said tell me please thanks thank hi hello hey am "
    "isnt arent dont doesnt didnt wont cant couldnt wouldnt shouldnt im ive youre hes shes its thats whats "
    "here there then than so too very just only also not no yes if but "
    "good great okay ok yeah well oh ah hmm um uh sorry".split()
)

ROW_OVERHEAD_TOKENS = 4


def normalize_license(value) -> str | None:
    """Canonical open license for a raw license string, or None when the
    string is missing or unrecognized. Normalization is case, spacing,
    and hyphen tolerant only; it never guesses a license for prose."""
    if not isinstance(value, str):
        return None
    key = re.sub(r"[\s_]+", "-", value.strip().lower())
    key = key.replace("creative-commons-", "cc-")
    return _LICENSE_ALIASES.get(key)


def content_words(text: str) -> list[str]:
    """Content words of a text, in order, duplicates removed."""
    out: list[str] = []
    for w in _WORD.findall((text or "").lower().replace("'", " ")):
        if len(w) >= 3 and w not in _STOP and w not in out:
            out.append(w)
    return out


def estimate_tokens(text: str) -> int:
    """Token estimate for a text: ceil(words * 4 / 3). An estimate, not
    a tokenizer measurement; see the module docstring."""
    words = (text or "").split()
    if not words:
        return 0
    return int(math.ceil(len(words) * 4 / 3))


class IndexedRow:
    """One retrievable row. seq is the global append order (0-based),
    stable for the life of the index; nothing ever renumbers it."""

    __slots__ = ("seq", "kind", "user", "assistant", "license", "origin", "source_file", "line_no")

    def __init__(self, seq, kind, user, assistant, license, origin, source_file, line_no):
        self.seq = seq
        self.kind = kind
        self.user = user
        self.assistant = assistant
        self.license = license
        self.origin = origin
        self.source_file = source_file
        self.line_no = line_no

    def text(self) -> str:
        return (self.user + " " + self.assistant).strip()

    def tokens(self) -> int:
        return estimate_tokens(self.text()) + ROW_OVERHEAD_TOKENS

    def as_dict(self) -> dict:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "user": self.user,
            "assistant": self.assistant,
            "license": self.license,
            "origin": self.origin,
            "source_file": self.source_file,
            "line_no": self.line_no,
            "tokens": self.tokens(),
        }


class LedgerIndex:
    """Read-only, unbounded, deterministic retrieval index over ledger
    and rows JSONL files. Build with add_file(), grow with refresh(),
    ask with query(). Never writes to any file."""

    def __init__(self):
        self.entries: list[IndexedRow] = []
        self._postings: dict[str, list[int]] = {}
        self._files: dict[str, int] = {}
        self.stats = {
            "lines_read": 0,
            "indexed": 0,
            "excluded_unlicensed": 0,
            "excluded_no_taught_row": 0,
            "excluded_malformed": 0,
            "excluded_empty": 0,
        }

    def add_file(self, path) -> None:
        """Register a ledger or rows JSONL file and index all its lines.
        The file kind is detected per line, so a ledger file and a rows
        file can both be added with the same call."""
        key = str(Path(path))
        if key in self._files:
            raise ValueError("file already indexed: %s" % key)
        lines = Path(path).read_text().splitlines()
        self._files[key] = 0
        self._index_lines(key, lines, 0)

    def refresh(self) -> dict:
        """Re-index only the appended tail of each registered file.
        Existing entries are untouched. Raises ValueError, changing
        nothing, if any file shrank (history rewritten)."""
        for key, consumed in list(self._files.items()):
            lines = Path(key).read_text().splitlines()
            if len(lines) < consumed:
                raise ValueError(
                    "file shrank, history rewritten, refusing to re-index: %s" % key
                )
            if len(lines) > consumed:
                self._index_lines(key, lines[consumed:], consumed)
        return dict(self.stats)

    def _index_lines(self, source_file: str, lines: list[str], start_line: int) -> None:
        for offset, line in enumerate(lines):
            self.stats["lines_read"] += 1
            if not line.strip():
                self.stats["excluded_empty"] += 1
                continue
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                self.stats["excluded_malformed"] += 1
                continue
            if not isinstance(record, dict):
                self.stats["excluded_malformed"] += 1
                continue
            row = self._row_from_record(record, source_file, start_line + offset + 1)
            if row is None:
                continue
            self._append(row)
        self._files[source_file] = start_line + len(lines)

    def _row_from_record(self, record: dict, source_file: str, line_no: int):
        """Normalize one JSONL record to an IndexedRow, or None when the
        record carries nothing retrievable. Ledger entries yield their
        nested taught row only when status is studied; failed attempts
        have taught_row None and yield nothing. Rows-file records (taught
        or world diary rows) yield themselves. In every case the license
        gate applies; a missing or unrecognized license excludes."""
        taught = record.get("taught_row")
        if isinstance(taught, dict):
            if record.get("status") != "studied":
                self.stats["excluded_no_taught_row"] += 1
                return None
            user = taught.get("user") or ""
            assistant = taught.get("assistant") or ""
            raw_license = taught.get("license") or record.get("license")
            kind = "taught"
            origin = taught.get("origin") or record.get("source_url") or ""
        elif "taught_row" in record:
            self.stats["excluded_no_taught_row"] += 1
            return None
        else:
            user = record.get("user") or ""
            assistant = record.get("assistant") or ""
            raw_license = record.get("license")
            label = str(record.get("label") or record.get("kind") or "").upper()
            kind = "diary" if label in ("DIARY", "RECORDED") else "taught"
            origin = record.get("origin") or record.get("source") or ""
        if not user.strip() or not assistant.strip():
            self.stats["excluded_empty"] += 1
            return None
        license = normalize_license(raw_license)
        if license is None:
            self.stats["excluded_unlicensed"] += 1
            return None
        return IndexedRow(
            seq=len(self.entries),
            kind=kind,
            user=user,
            assistant=assistant,
            license=license,
            origin=origin,
            source_file=source_file,
            line_no=line_no,
        )

    def _append(self, row: IndexedRow) -> None:
        self.entries.append(row)
        self.stats["indexed"] += 1
        for token in set(content_words(row.user)) | set(content_words(row.assistant)):
            self._postings.setdefault(token, []).append(row.seq)

    def rank(self, query_text: str) -> list[tuple[int, IndexedRow]]:
        """All matching rows as (score, row), ranked by score desc then
        seq asc. Score 0 rows are not matches and are not returned."""
        words = content_words(query_text)
        if not words:
            return []
        candidates: set[int] = set()
        for word in words:
            candidates.update(self._postings.get(word, []))
        scored: list[tuple[int, IndexedRow]] = []
        for seq in candidates:
            row = self.entries[seq]
            user_words = set(content_words(row.user))
            answer_words = set(content_words(row.assistant))
            score = 0
            for word in words:
                if word in user_words:
                    score += 2
                if word in answer_words:
                    score += 1
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1].seq))
        return scored

    def query(self, query_text: str, max_tokens: int) -> dict:
        """Token-budget-aware retrieval. Returns the highest-ranked rows
        that fit in max_tokens, in rank order, plus the leftover count:
        how many matching rows were left out. tokens_used never exceeds
        max_tokens. Raises ValueError for a non-positive budget."""
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        ranked = self.rank(query_text)
        chosen: list[IndexedRow] = []
        used = 0
        leftover = 0
        for _score, row in ranked:
            cost = row.tokens()
            if used + cost <= max_tokens:
                chosen.append(row)
                used += cost
            else:
                leftover += 1
        return {
            "query": query_text,
            "max_tokens": max_tokens,
            "matched": len(ranked),
            "returned": len(chosen),
            "leftover": leftover,
            "tokens_used": used,
            "rows": [row.as_dict() for row in chosen],
        }


def build_index(paths) -> LedgerIndex:
    """Build an index over the given ledger/rows JSONL files, in order."""
    index = LedgerIndex()
    for path in paths:
        index.add_file(path)
    return index


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Query the append-only ledger index (read-only).")
    p.add_argument("--rows", action="append", default=[], help="taught or diary rows JSONL (repeatable)")
    p.add_argument("--ledger", action="append", default=[], help="hash-chained ledger JSONL (repeatable)")
    p.add_argument("--query", required=True, help="topic query text")
    p.add_argument("--max-tokens", type=int, default=200, help="per-query token budget")
    args = p.parse_args(argv)
    index = build_index([Path(x) for x in args.rows + args.ledger])
    result = index.query(args.query, args.max_tokens)
    result["stats"] = dict(index.stats)
    print("ZEREF_LEDGER_INDEX=" + json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
