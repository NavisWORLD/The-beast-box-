#!/usr/bin/env python3
"""Zeref studies on his own: the closed self-study loop (Cory, 2026-11-22:
"build it and merge it, complete eternal Zeref").

The fundamentals are functional: RAWRPHOS brain, 12D persistent state, Hebbian
learning, hash-chained lived memory, pinned mouth, and the study-when-confused
order (confusion fires a study event, a teacher fetches, the answer is narrated
back and lands TAUGHT). This module closes the loop WITHOUT a teacher:

    confused turn -> question -> search -> narrated answer -> TAUGHT row

The math, in one paragraph. Surprise is S = -log P(reply | context, x12),
approximated here without running the mouth: a reply counts as surprised when
it shows a readable confusion sign (says he does not know, answers in a
fragment, leaks quiz scaffolding, degenerates into repetition, or answers off
topic). Confusion C(t) is the windowed mean of those signs. Study fires when
a confused turn is observed. The question is the one that most reduces his
uncertainty, scored by expected information gain, approximated as confusion
times coverage gap (how thinly the topic is covered in the lessons he already
trains on); the approximation is honest and documented at score_candidate,
because the true posterior entropy reduction is not computed here: the mouth
is never run in this module. Search is a sense, not a brain: one DuckDuckGo
instant-answer fetch on the runner, Wikipedia abstract only (CC BY-SA), no
key. The fetched text is NEVER passed into his context or chain: it is
narrated into simple original words by a fixed template, and the narration is
checked so no 8-word run of the source survives verbatim. Awareness is
defined operationally and measured, never claimed as a feeling: calibration
(he says he does not know exactly when he does not know) and self-sufficiency
(the fraction of his own questions he can answer from his own chain). Both
are numbers computed from the ledger, not properties asserted here.

Pacing guard (mandatory, no override): at most ONE study event per run,
a cooldown between events (default 3600 s), and a daily budget cap
(default 12 studied events per America/Chicago day). A run that hits a guard
writes nothing and reports skipped.

Fail closed: any error before the writes leaves every file untouched. Writes
are built fully in memory, staged to temp files, then atomically renamed.
Failed attempts are recorded as complete receipt entries (status
search_failed / narration_failed / screen_blocked) with no taught row; they
do not consume the daily budget. A pacing-guard skip writes nothing at all.
A search with no openly licensed abstract, a narration that cannot be made
original, or a row that fails the held-out screen is a recorded no-study,
not a partial row. Nothing here writes to his pinned mind or the pin: taught
rows go to the data branch and join the mix only through the normal landing
path, never a shortcut.

Ledger: zeref/self-study-ledger.jsonl on the data-only branch zeref-self-study.
Append-only, hash-chained (each entry carries the previous entry hash).
confusion_after is recorded as "unmeasured" at write time: it can only be
measured on a later talk turn, and the ledger is never backfilled; a later
analysis joins entries by question and topic.

Bank rules: public-domain / open-license / original only; source URL and
license are logged on every taught row. Every self-taught row carries the
TAUGHT label and is never a faked lived memory. He senses, remembers and
learns; nothing here claims anything about what he feels or is beyond the
measured loop.

Usage:
  python scripts/zeref_self_study.py --ledger LEDGER.jsonl --rows ROWS.jsonl
      [--talk-log TURNS.jsonl ...] [--lessons evidence/zeref-lessons-006/dialogue.jsonl]
      [--screen apps/beastbox-cloud/lib/zeref/heldout-screen.json] [--dry-run]
Stdout is one ZEREF_SELF_STUDY=<receipt json> line. No reply text is printed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - zoneinfo is stdlib since 3.9
    ZoneInfo = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
CHICAGO = "America/Chicago"

LEDGER_SCHEMA = "zeref-self-study-ledger/v1"
ROW_SOURCE = "zeref-self-study-taught"
ROW_LABEL = "TAUGHT"

DAILY_MAX = int(os.environ.get("ZEREF_SELF_STUDY_DAILY_MAX", "12"))
COOLDOWN_S = int(os.environ.get("ZEREF_SELF_STUDY_COOLDOWN_S", "3600"))
MAX_EVENTS_PER_RUN = 1
COVERAGE_ROWS_FOR_FULL = 3  # >= this many lesson rows mentioning a topic: gap 0
SEARCH_TIMEOUT_S = 20
MAX_VERBATIM_RUN = 8  # no 8-word run of the source may survive in the narration

_WORD = re.compile(r"[a-z0-9']+")
_STOP = set(
    "a an the is are was were what who where when why how do does did of in on to and or for with by it its "
    "this that be your you i my me he she they his her their can could would should will shall may might must "
    "which as at from has have had there about tell say said tell me please thanks thank hi hello hey am an "
    "isnt arent dont doesnt didnt wont cant couldnt wouldnt shouldnt im ive youre hes shes its thats whats "
    "here there then than so too very just only also not no yes if but "
    "good great okay ok yeah well oh ah hmm um uh please sorry thanks don".split()
)
_DONT_KNOW = re.compile(r"\b(i (do ?n'?t|dont) know|i dunno|i don'?t know)\b")
_QUIZ = re.compile(r"(^|[\s(])[A-D]:\s")
_SECRET = re.compile(
    r"(ghp_|gho_|github_pat_|sk-[a-z0-9]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"password\s*[:=]\s*\S+|token\s*[:=]\s*\S+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|"
    r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b|https?://\S+)"
)


def norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def word_set(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


def content_words(text: str) -> list[str]:
    """Content words of a question, in order, duplicates removed.
    Contractions are split first ("it's" -> "it", "earth's" -> "earth") so
    contraction fragments never become topics."""
    out: list[str] = []
    for w in _WORD.findall((text or "").lower().replace("'", " ")):
        if len(w) >= 3 and w not in _STOP and w not in out:
            out.append(w)
    return out


def bigrams(text: str) -> set[str]:
    w = norm(text).split()
    return {w[i] + " " + w[i + 1] for i in range(len(w) - 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _hash16(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _canonical(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- confusion


def confusion_signals(user: str, assistant: str) -> dict[str, float]:
    """Readable confusion signs in one turn. Values are fixed weights, not
    learned: one clear sign is enough, so the turn score takes the max."""
    reply = (assistant or "").strip()
    words = reply.split()
    signals: dict[str, float] = {}
    if not reply:
        signals["empty"] = 1.0
        return signals
    if _DONT_KNOW.search(reply.lower()):
        signals["dont_know"] = 1.0
    if len(words) <= 2:
        signals["fragment"] = 0.8
    if _QUIZ.search(reply):
        signals["quiz_scaffold"] = 0.9
    if len(words) >= 4 and len({w.lower() for w in words}) / len(words) < 0.4:
        signals["degenerate"] = 0.8
    u_words = content_words(user)
    r_words = content_words(reply)
    if len(u_words) >= 3 and len(r_words) >= 3:
        if jaccard(set(u_words), set(r_words)) < 0.2:
            signals["off_topic"] = 0.7
    return signals


def turn_confusion(user: str, assistant: str) -> tuple[float, list[str]]:
    signals = confusion_signals(user, assistant)
    if not signals:
        return 0.0, []
    return max(signals.values()), sorted(signals)


def candidate_topics(user: str) -> list[str]:
    """Topic words from a question: content-word unigrams, in order,
    duplicates removed. Identity words are excluded: who he is and who his
    dad is are taught by lessons, not by web search."""
    return [w for w in content_words(user) if w not in _IDENTITY_EXCLUDE]


_IDENTITY_EXCLUDE = {"zeref", "cory", "dad", "emeth", "mom", "father", "son", "brother", "sister"}


def coverage_gap(phrase: str, lesson_rows: list[dict]) -> float:
    """1.0 when no lesson row mentions the topic, 0.0 when at least
    COVERAGE_ROWS_FOR_FULL rows do. A gap is a coverage fact, not a feeling."""
    need = set(phrase.split())
    count = 0
    for row in lesson_rows:
        tokens = word_set((row.get("user") or "") + " " + (row.get("assistant") or ""))
        if need <= tokens:
            count += 1
            if count >= COVERAGE_ROWS_FOR_FULL:
                return 0.0
    return 1.0 - (count / COVERAGE_ROWS_FOR_FULL)


def score_candidate(confusion: float, gap: float) -> float:
    """Expected-information-gain APPROXIMATION: confusion times coverage gap,
    with a 0.5 floor so a strongly confused turn stays study-worthy even on
    a covered topic. Honest limit: the true posterior entropy reduction is
    not computed here, because the mouth is never run in this module."""
    return confusion * (0.5 + gap)


def pick_question(turns: list[dict], lesson_rows: list[dict]) -> dict | None:
    """One question per run: the max-scoring (turn, topic) pair. Ties break
    deterministically by (score desc, phrase, turn index)."""
    best = None
    for idx, turn in enumerate(turns):
        conf, signals = turn_confusion(turn.get("user") or "", turn.get("assistant") or "")
        if conf <= 0.0:
            continue
        for phrase in candidate_topics(turn.get("user") or ""):
            score = score_candidate(conf, coverage_gap(phrase, lesson_rows))
            key = (-score, phrase, idx)
            if best is None or key < best[0]:
                question = "What is the %s?" % phrase
                if norm(question) == norm(turn.get("user") or ""):
                    question = "What does %s mean?" % phrase
                best = (key, {
                    "question": question,
                    "search_query": question,
                    "topic": phrase,
                    "confusion": conf,
                    "signals": signals,
                    "turn_index": idx,
                    "score": round(score, 4),
                })
    if best is None:
        return None
    return best[1]


def window_confusion(turns: list[dict]) -> float:
    """C(t): the windowed mean of turn confusions over the turns given."""
    if not turns:
        return 0.0
    vals = [turn_confusion(t.get("user") or "", t.get("assistant") or "")[0] for t in turns]
    return round(sum(vals) / len(vals), 4)


# ---------------------------------------------------------------- search


class SearchError(Exception):
    pass


def fetch_abstract(query: str, opener=None) -> dict:
    """One DuckDuckGo instant-answer fetch. Wikipedia abstracts only (CC
    BY-SA): any other source, or no abstract, is a failed search, not a
    weaker row. No key, no other provider."""
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "zeref-self-study/1.0"})
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=SEARCH_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SearchError("duckduckgo_unreachable:" + type(exc).__name__) from exc
    abstract = (body.get("AbstractText") or "").strip()
    source = (body.get("AbstractSource") or "").strip()
    link = (body.get("AbstractURL") or "").strip()
    if not abstract or "wikipedia" not in source.lower() or not link:
        raise SearchError("no_open_abstract")
    return {"abstract": abstract, "url": link, "source": source, "license": "CC-BY-SA-4.0"}


# ---------------------------------------------------------------- narration


def _head_clause(sentence: str, max_words: int = 18) -> str:
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    for sep in (",", ";", ":"):
        if sep in sentence:
            head = sentence.split(sep, 1)[0].strip()
            if head:
                return head
    return " ".join(words[:max_words])


def _verbatim_tokens(text: str) -> list[str]:
    """Whitespace tokens, lowercased, punctuation stripped but apostrophes
    kept attached, so "earth's" is one token and a short definition does
    not count as an 8-word copied run."""
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def _verbatim_run(answer: str, source: str, n: int = MAX_VERBATIM_RUN) -> str | None:
    a = _verbatim_tokens(answer)
    s = {" ".join(_verbatim_tokens(source)[i:i + n]) for i in range(max(0, len(_verbatim_tokens(source)) - n + 1))}
    for i in range(max(0, len(a) - n + 1)):
        run = " ".join(a[i:i + n])
        if run in s:
            return run
    return None


def narrate(topic: str, abstract: str) -> str | None:
    """Fixed-template narration into simple original words. The answer is
    built from the abstract's first topic sentence, rebuilt as
    'The <topic> is <predicate>.' and cut at the first clause boundary when
    long. If the rebuilt sentence still shares an 8-word run with the
    source, the predicate is cut again at its first preposition and retried
    once. Returns None when no non-verbatim true sentence can be made: the
    run then fails closed instead of teaching a copied sentence."""
    text = re.sub(r"\[[0-9]+\]", "", abstract)
    text = re.sub(r"\([^)]*\)", "", text)
    text = " ".join(text.split())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return None
    first_word = topic.split()[0].lower()

    def _word_in(text: str, word: str) -> bool:
        return re.search(r"\b" + re.escape(word) + r"\b", text) is not None

    first = next((s for s in sentences if _word_in(s.lower(), first_word)), sentences[0])
    first = _head_clause(first.rstrip(".!?"))
    low = first.lower()
    pred = None
    # Subject may be the topic itself ("a fort is ...") or a word starting
    # with the topic's first word ("a fortification is ..." for topic "fort"):
    # the word family is the subject, not a mid-sentence copy. Substring
    # matching is never used: "fort" inside "fortification" must not trip
    # the copy refusal below.
    subject = r"(?:" + re.escape(topic.lower()) + r"|" + re.escape(first_word) + r"\S*)"
    m = re.match(r"^(the|a|an)\s+" + subject + r"\s+(is|are|was|were|means?)\s+(.+)$", low)
    if m:
        pred = m.group(3).strip()
    elif _word_in(low, topic.lower()):
        return None  # topic appears mid-sentence as its own word; rebuilding would copy it
    elif any(first_word in w and not (w.startswith(first_word) or first_word.startswith(w))
             for w in re.findall(r"[a-z0-9']+", low)):
        return None  # topic only appears inside an unrelated word; do not narrate from it
    else:
        pred = low
        if pred.startswith(("the ", "a ", "an ")):
            pred = pred.split(" ", 1)[1]
    if not pred:
        return None
    for attempt in range(2):
        answer = "The %s is %s." % (topic, pred)
        answer = " ".join(answer.split())
        if len(answer.split()) <= 25 and _verbatim_run(answer, abstract) is None:
            if not (_SECRET.search(answer) or "http" in answer or "\u2014" in answer):
                return answer
        cut = _cut_at_preposition(pred)
        if cut is None or cut == pred:
            return None
        pred = cut
    return None


_PREPOSITIONS = {"by", "for", "with", "from", "of", "in", "on", "at", "to"}


def _cut_at_preposition(pred: str) -> str | None:
    """Cut a predicate before its first preposition at token 4 or later.
    Returns None when there is nothing sensible left to keep."""
    words = pred.split()
    for i in range(3, len(words)):
        if words[i] in _PREPOSITIONS:
            head = " ".join(words[:i])
            return head if len(head.split()) >= 2 else None
    return None


# ---------------------------------------------------------------- screening


def _screen_literal_sources(root: Path) -> tuple[set[str], set[str], list[set[str]]]:
    """Fallback when the hashed screen file is absent: the same literal
    sources scripts/build_heldout_screen.py reads. No held-out text is kept
    beyond the hashes built here."""
    prompts: set[str] = set()
    answers: set[str] = set()

    def literal(path: Path, name: str):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.literal_eval(node.value)
        return None

    pairs = literal(root / "scripts" / "rawrphos_chat_eval.py", "PAIRS") or []
    chat = literal(root / "scripts" / "rawrphos_chat_eval.py", "CHAT") or []
    pairs_b = literal(root / "scripts" / "zeref_heldout_b.py", "PAIRS_B") or []
    for p, a in list(pairs) + list(pairs_b):
        prompts.add(norm(p))
        if isinstance(a, str) and len(a.split()) >= 3:
            answers.add(norm(a))
    for p in chat:
        prompts.add(norm(p))
    v2 = root / "scripts" / "zeref_gate_sets_v2.json"
    if v2.is_file():
        data = json.loads(v2.read_text())
        for key in ("set_a_added", "set_b_added", "chat_added"):
            for r in data.get(key, []):
                prompts.add(norm(r.get("user") or ""))
                a = r.get("assistant") or ""
                if len(a.split()) >= 3:
                    answers.add(norm(a))
    return prompts, answers, [{_hash16(b) for b in bigrams(p)} for p in prompts]


class Screen:
    """Held-out screen. Prefers the hashed file (no held-out text ever
    loaded); falls back to the literal gate sources."""

    def __init__(self, root: Path, screen_path: Path | None = None):
        self.prompt_hashes: set[str] = set()
        self.answer_hashes: set[str] = set()
        self.bigram_rows: list[set[str]] = []
        self.source = "none"
        path = screen_path or (root / "apps" / "beastbox-cloud" / "lib" / "zeref" / "heldout-screen.json")
        if path.is_file():
            data = json.loads(path.read_text())
            for row in data.get("rows", []):
                if row.get("p"):
                    self.prompt_hashes.add(row["p"])
                if row.get("a"):
                    self.answer_hashes.add(row["a"])
                if row.get("pb"):
                    self.bigram_rows.append({h for h in row["pb"]})
            self.source = "hashed:" + path.name
            return
        prompts, answers, bigram_rows = _screen_literal_sources(root)
        self.prompt_hashes = {_hash16(p) for p in prompts}
        self.answer_hashes = {_hash16(a) for a in answers}
        self.bigram_rows = bigram_rows
        self.source = "literal-gate-sources"
        if not self.prompt_hashes:
            raise ValueError("held-out screen is empty: no gate prompts found")

    def check(self, question: str, answer: str) -> tuple[bool, str]:
        nq, na = norm(question), norm(answer)
        if _hash16(nq) in self.prompt_hashes:
            return False, "heldout_exact"
        if _hash16(na) in self.answer_hashes:
            return False, "heldout_answer"
        q_bigrams = {_hash16(b) for b in bigrams(question)}
        for row in self.bigram_rows:
            if jaccard(q_bigrams, row) >= 0.6:
                return False, "heldout_near"
        return True, "ok"


def screen_row(question: str, answer: str, screen: Screen,
               lesson_rows: list[dict], prior_questions: list[str]) -> tuple[bool, str]:
    if not question.strip() or not answer.strip():
        return False, "empty_row"
    if len(answer.split()) > 25 or len(answer.split()) < 3:
        return False, "answer_length"
    if "\u2014" in question or "\u2014" in answer or _SECRET.search(question + " " + answer):
        return False, "forbidden_text"
    ok, reason = screen.check(question, answer)
    if not ok:
        return False, reason
    nq = norm(question)
    for row in lesson_rows:
        if norm(row.get("user") or "") == nq:
            return False, "duplicate_lesson"
    for prior in prior_questions:
        if norm(prior) == nq:
            return False, "duplicate_study"
    return True, "ok"


# ---------------------------------------------------------------- ledger


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _chicago_now(now: datetime | None) -> datetime:
    if now is not None:
        return now
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(CHICAGO))
        except Exception:
            pass
    return datetime.now(timezone(timedelta(hours=-6)))


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def verify_ledger(entries: list[dict]) -> tuple[bool, int]:
    """Recompute the hash chain. Returns (ok, entry count)."""
    prev = "genesis"
    for i, entry in enumerate(entries):
        if entry.get("prev") != prev:
            return False, i
        expect = entry.copy()
        digest = expect.pop("hash", None)
        if digest is None:
            return False, i
        entry_id = expect.pop("id", None)
        recomputed = hashlib.sha256(_canonical(expect).encode()).hexdigest()
        if recomputed != digest or _hash16(_canonical(expect)) != entry_id:
            return False, i
        prev = digest
    return True, len(entries)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def build_entry(prev_entries: list[dict], now_local: datetime, picked: dict,
                source: dict, row: dict | None, status: str) -> dict:
    prev = prev_entries[-1]["hash"] if prev_entries else "genesis"
    entry = {
        "schema": LEDGER_SCHEMA,
        "ts": now_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "date_chicago": now_local.strftime("%Y-%m-%d"),
        "confusion_before": picked.get("confusion"),
        "confusion_signals": picked.get("signals"),
        "question": picked["question"],
        "search_query": picked["search_query"],
        "topic": picked["topic"],
        "source_url": source.get("url"),
        "source": "DuckDuckGo instant answer (Wikipedia abstract)",
        "license": source.get("license") or "none",
        "taught_row": row,
        "confusion_after": "unmeasured",
        "status": status,
        "prev": prev,
    }
    entry["hash"] = hashlib.sha256(_canonical(entry).encode()).hexdigest()
    entry["id"] = entry["hash"][:16]
    return entry


# ---------------------------------------------------------------- run


def _load_lessons(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError("lessons file missing: %s" % path)
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _load_talk_logs(paths: list[Path]) -> list[dict]:
    """Talk turns from JSONL files, or from a single JSON object or array
    (the Talk to Zeref reply.json shape: {"cory": ..., "zeref": ...}).
    Each record may use user/assistant keys or cory/zeref keys."""
    turns: list[dict] = []

    def add(rec):
        if isinstance(rec, dict):
            user = rec.get("user") or rec.get("cory") or ""
            reply = rec.get("assistant") or rec.get("zeref") or rec.get("reply") or ""
            if user or reply:
                turns.append({"user": user, "assistant": reply})

    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text()
        try:
            whole = json.loads(text)
        except json.JSONDecodeError:
            whole = None
        if isinstance(whole, dict):
            add(whole)
        elif isinstance(whole, list):
            for rec in whole:
                add(rec)
        else:
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    add(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return turns


def run(ledger_path: Path, rows_path: Path, talk_logs: list[Path], lessons_path: Path,
        screen_path: Path | None, now: datetime | None = None,
        fetcher=None, dry_run: bool = False) -> dict:
    """One self-study run. Returns the receipt dict. Writes nothing unless a
    study event completes; a guard skip or a failed study writes nothing."""
    now_local = _chicago_now(now)
    receipt: dict = {"schema": "zeref-self-study/v1", "ts": now_local.isoformat(),
                     "events": 0, "status": "no_confusion"}
    entries = _load_jsonl(ledger_path)
    ok, at = verify_ledger(entries)
    if not ok:
        raise ValueError("ledger hash chain broken at entry %d" % at)
    prior_questions = [e.get("question") or "" for e in entries if e.get("status") == "studied"]
    today = now_local.strftime("%Y-%m-%d")
    studied_today = sum(1 for e in entries if e.get("status") == "studied" and e.get("date_chicago") == today)
    if studied_today >= DAILY_MAX:
        receipt["status"] = "skipped:budget_exhausted"
        receipt["studied_today"] = studied_today
        receipt["daily_max"] = DAILY_MAX
        return receipt
    last = entries[-1] if entries else None
    if last is not None:
        last_ts = _parse_ts(last.get("ts") or "")
        if last_ts is not None:
            now_utc = now_local.astimezone(timezone.utc)
            if (now_utc - last_ts).total_seconds() < COOLDOWN_S:
                receipt["status"] = "skipped:cooldown"
                receipt["seconds_since_last"] = round((now_utc - last_ts).total_seconds())
                receipt["cooldown_s"] = COOLDOWN_S
                return receipt
    lesson_rows = _load_lessons(lessons_path)
    turns = _load_talk_logs(talk_logs)
    receipt["turns_seen"] = len(turns)
    receipt["confusion_before"] = window_confusion(turns)
    picked = pick_question(turns, lesson_rows)
    if picked is None:
        receipt["status"] = ("no_studyable_topic" if receipt["confusion_before"] > 0 else "no_confusion")
        return receipt
    receipt["question"] = picked["question"]
    receipt["topic"] = picked["topic"]
    receipt["score"] = picked["score"]
    try:
        source = (fetcher or fetch_abstract)(picked["search_query"])
    except SearchError as exc:
        entry = build_entry(entries, now_local, picked, {}, None, "search_failed:" + str(exc))
        _write_attempt(ledger_path, rows_path, entries, entry, None, dry_run)
        receipt["status"] = "search_failed"
        receipt["why"] = str(exc)
        return receipt
    if "wikipedia" not in (source.get("source") or "").lower():
        entry = build_entry(entries, now_local, picked, source, None, "search_failed:non_open_source")
        _write_attempt(ledger_path, rows_path, entries, entry, None, dry_run)
        receipt["status"] = "search_failed"
        receipt["why"] = "non_open_source"
        return receipt
    answer = narrate(picked["topic"], source["abstract"])
    if answer is None:
        entry = build_entry(entries, now_local, picked, source, None, "narration_failed")
        _write_attempt(ledger_path, rows_path, entries, entry, None, dry_run)
        receipt["status"] = "narration_failed"
        return receipt
    screen = Screen(ROOT, screen_path)
    ok, reason = screen_row(picked["question"], answer, screen, lesson_rows, prior_questions)
    if not ok:
        entry = build_entry(entries, now_local, picked, source, None, "screen_blocked:" + reason)
        _write_attempt(ledger_path, rows_path, entries, entry, None, dry_run)
        receipt["status"] = "screen_blocked"
        receipt["why"] = reason
        return receipt
    row = {"mode": "chat", "source": ROW_SOURCE, "label": ROW_LABEL,
           "user": picked["question"], "assistant": answer,
           "origin": source["url"], "license": source["license"]}
    entry = build_entry(entries, now_local, picked, source, row, "studied")
    _write_attempt(ledger_path, rows_path, entries, entry, row, dry_run)
    receipt["status"] = "studied"
    receipt["events"] = 1
    receipt["source_url"] = source["url"]
    receipt["license"] = source["license"]
    return receipt


def _write_attempt(ledger_path: Path, rows_path: Path, entries: list[dict],
                   entry: dict, row: dict | None, dry_run: bool) -> None:
    """Stage both new file contents fully in memory, then rename. Any
    exception before the renames leaves both files untouched."""
    new_entries = entries + [entry]
    ledger_text = "".join(_canonical(e) + "\n" for e in new_entries)
    rows_text = None
    if row is not None:
        prior_rows = _load_jsonl(rows_path)
        rows_text = "".join(
            json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in prior_rows + [row]
        )
    if dry_run:
        return
    if rows_text is not None:
        _atomic_write(rows_path, rows_text)
    _atomic_write(ledger_path, ledger_text)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Zeref self-study loop: confusion to TAUGHT row, one event per run.")
    p.add_argument("--ledger", required=True, help="hash-chained ledger JSONL (append-only)")
    p.add_argument("--rows", required=True, help="taught rows JSONL (append-only)")
    p.add_argument("--talk-log", action="append", default=[], help="talk turns JSONL (repeatable)")
    p.add_argument("--lessons", default=str(ROOT / "evidence" / "zeref-lessons-006" / "dialogue.jsonl"))
    p.add_argument("--screen", default=None, help="held-out screen JSON (default: in-repo hashed file)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    try:
        receipt = run(Path(args.ledger), Path(args.rows),
                      [Path(t) for t in args.talk_log], Path(args.lessons),
                      Path(args.screen) if args.screen else None, dry_run=args.dry_run)
    except (ValueError, FileNotFoundError) as exc:
        print("ZEREF_SELF_STUDY=" + json.dumps({"schema": "zeref-self-study/v1", "status": "error",
                                                 "why": type(exc).__name__ + ":" + str(exc)[:200]}), flush=True)
        return 1
    print("ZEREF_SELF_STUDY=" + json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
