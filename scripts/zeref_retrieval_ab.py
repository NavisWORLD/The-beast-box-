#!/usr/bin/env python3
"""Self-memory A/B, REPORT ONLY: the same fixed questions to the growing door with self-memory on vs off.

Writes evidence/zeref-retrieval-ab-001/report.json. It changes nothing: no gate, eval set, pin or lesson is read
for scoring or written. The question set is hash-checked and verified absent from every evidence JSONL prompt
(eval sets A and B included). On-topic = the reply matches the question's regex (crude, stated rule).
Seeds: the live growing door takes no seed (its plain contract is byte-identical by design), so each arm is
asked REPEATS times in a fixed interleaved order and the spread is reported, not hidden.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "evidence/zeref-retrieval-ab-001"
QUESTIONS_SHA256 = "f05a127b2cb60c75198b49a32ea96a935476658fb17e2d15c72d603386f48dc0"
norm = lambda s: re.sub(r"\W+", " ", str(s).lower()).strip()


def load_questions() -> list[dict]:
    raw = (DIR / "questions.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != QUESTIONS_SHA256:
        sys.exit("questions.json hash mismatch; the fixed set was edited")
    return json.loads(raw)["questions"]


def assert_not_in_eval_sets(questions: list[dict]) -> int:
    wanted = {norm(q["question"]) for q in questions}
    scanned = 0
    for p in (ROOT / "evidence").rglob("*.jsonl"):
        if DIR in p.parents: continue
        scanned += 1
        for line in p.read_text(errors="ignore").splitlines():
            try: r = json.loads(line)
            except ValueError: continue
            if not isinstance(r, dict): continue
            for k in ("user", "prompt", "question", "input"):
                if isinstance(r.get(k), str) and norm(r[k]) in wanted:
                    sys.exit(f"question overlaps an evidence prompt: {p.relative_to(ROOT)}")
    return scanned


def ask(site: str, text: str, memory: bool) -> dict:
    body = {"text": text} if memory else {"text": text, "memory": False}
    for attempt in range(6):
        req = urllib.request.Request(site.rstrip("/") + "/api/guest-growing", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Origin": site.rstrip("/")})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(8 * (attempt + 1)); continue
            return {"error": f"HTTP {e.code}"}
        except (OSError, ValueError) as e:
            return {"error": type(e).__name__}
    return {"error": "rate limited"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="https://www.beastboxcosmos.xyz")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    qs = load_questions(); scanned = assert_not_in_eval_sets(qs)
    rows = []
    for rep in range(a.repeats):
        for q in qs:
            for arm in (("on", "off") if (rep + int(q["id"][1:])) % 2 == 0 else ("off", "on")):  # fixed interleave
                r = ask(a.site, q["question"], arm == "on")
                reply = r.get("reply") if isinstance(r.get("reply"), str) else None
                rows.append({"q": q["id"], "rep": rep, "arm": arm, "ok": reply is not None,
                             "on_topic": bool(reply and re.search(q["on_topic_regex"], reply, re.I)),
                             "reply": reply, "error": r.get("error"), "step": r.get("step"), "tag": r.get("tag"),
                             "memory_used": r.get("memory_used"), "memory_read": r.get("memory_read") or []})
                time.sleep(a.pause)
    def rate(arm):
        ok = [x for x in rows if x["arm"] == arm and x["ok"]]
        return {"answered": len(ok), "asked": sum(1 for x in rows if x["arm"] == arm),
                "on_topic": sum(x["on_topic"] for x in ok), "on_topic_rate": round(sum(x["on_topic"] for x in ok) / len(ok), 4) if ok else None,
                "memory_used_true": sum(1 for x in ok if x["memory_used"] is True)}
    report = {"schema": "zeref-retrieval-ab/v1", "label": "REPORT ONLY. Self-memory on vs off on the live growing door. Not a gate; changes nothing.",
              "site": a.site, "questions_sha256": QUESTIONS_SHA256, "eval_overlap_check": {"jsonl_files_scanned": scanned, "overlaps": 0},
              "repeats": a.repeats, "seed_note": "The live growing door takes no seed; repeats show the spread.",
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "on": rate("on"), "off": rate("off"), "rows": rows}
    (DIR / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("on", "off")}))


if __name__ == "__main__":
    main()
