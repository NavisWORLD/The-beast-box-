"""Quantum-record dice for Zeref's replies (Python twin of NavisWORLD docs/zeref-brain/qrec.mjs).

Cory, 2026-11-21 (6:51 PM CT): "we run the measurements into the hash we inject quantum snap shots".
7:00 PM CT: quantum-record dice are the default in the browser chat; ?greedy=1 keeps the old reply.

What it is: a sampler whose dice come ONLY from sha256 over RECORDED IBM hardware shot records that
are already public in this repo (heart seed v15 / ibm_marrakesh CHSH run, and the ibm_fez spark seed).
No live quantum job, no Math.random / os.urandom / time: anyone can replay a reply from its receipt.
Label: "quantum record (RECORDED IBM …)", never "live quantum". Cory's own HF card measured the
decoder sampling seed as null for accuracy (pseudo / IBM / Rigetti equivalent): the record buys
receipted provenance and variety, not a smarter brain.

Inference only: the checkpoint, the pin, eval and every gate are untouched (gates score NLL and greedy).

Algorithm (both ports must agree):
  record_seed = sha256("zeref-quantum-record-v1|" + heart_seed_sha256 + "|" + outcomes_sha256 of each
                        source in record order, joined by "|")
  turn_seed   = sha256("zeref-qrec-turn-v1|" + record_seed + "|" + roll + "|" + ",".join(prompt_ids))
                roll = assistant turns already in the visitor's thread (recomputable from the thread)
  u_k         = int(sha256(turn_seed + "|" + k)[:13], 16) / 2**52      (k = word-piece index, 0-based)
  pick        = after the server rules (repetition 1.15, no-repeat-3), keep the top_k finite logits
                (ties -> lower id), weights exp((l - max) / T) in float64 summed in ascending id order,
                first id whose running sum exceeds u_k * total (last kept id if none).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "zeref-quantum-record-v1"
TEMPERATURE = 0.75
TOP_K = 40
LABEL = "quantum record (RECORDED IBM hardware shots; not live quantum)"
SOURCES = (  # record order matters: it is part of record_seed
    "evidence/zeref-heart-seed-v15/ibm-chsh-result-public.json",
    "evidence/zeref-spark-latest/spark-seed.json",
)
HEART_SEED = "evidence/zeref-spark-latest/heart-seed-latest.json"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_seed(heart_seed_sha256: str, outcomes: Sequence[str]) -> str:
    return sha256_hex("|".join([SCHEMA, heart_seed_sha256, *outcomes]))


def turn_seed(rec_seed: str, roll: int, prompt_ids: Iterable[int]) -> str:
    if type(roll) is not int or roll < 0:
        raise ValueError("roll must be a non-negative int")
    return sha256_hex("zeref-qrec-turn-v1|" + rec_seed + "|" + str(roll) + "|" + ",".join(str(int(t)) for t in prompt_ids))


def uniform(seed: str, k: int) -> float:
    return int(sha256_hex(seed + "|" + str(k))[:13], 16) / 2.0 ** 52


def pick(logits: Sequence[float], u: float, temperature: float = TEMPERATURE, top_k: int = TOP_K) -> int:
    """logits: the float32 values AFTER the repetition / no-repeat rules (-inf = banned)."""
    if not 0.0 <= u < 1.0 or temperature <= 0 or top_k < 1:
        raise ValueError("bad sampler arguments")
    finite = [i for i in range(len(logits)) if math.isfinite(float(logits[i]))]
    if not finite:
        raise ValueError("every word piece is banned")
    kept = sorted(finite, key=lambda i: (-float(logits[i]), i))[:top_k]
    kept.sort()
    m = max(float(logits[i]) for i in kept)
    w = [math.exp((float(logits[i]) - m) / temperature) for i in kept]
    total = 0.0
    for x in w:
        total += x
    target = u * total
    run = 0.0
    for i, x in zip(kept, w):
        run += x
        if run > target:
            return i
    return kept[-1]


def build_record(repo: Path) -> dict[str, Any]:
    """quantum-record.json from the public evidence files (reproducible; counts shots by class)."""
    heart = json.loads((repo / HEART_SEED).read_text(encoding="utf-8"))
    srcs = []
    for rel in SOURCES:
        raw = (repo / rel).read_bytes()
        d = json.loads(raw)
        if d.get("source_class") != "RECORDED_IBM_HARDWARE":
            raise ValueError(f"{rel} is not a RECORDED IBM hardware record")
        rounds = d["quantum"]["rounds"] if isinstance(d.get("quantum"), Mapping) else d["rounds"]
        srcs.append({"file": rel, "file_sha256": hashlib.sha256(raw).hexdigest(), "backend": d["backend"],
                     "job_id": d.get("job_id") or d.get("job"), "recorded_utc": d["recorded_utc"],
                     "source_class": d["source_class"], "measured_rounds": int(rounds),
                     "outcomes_sha256": d["outcomes_sha256"]})
    seed = record_seed(heart["heart_seed_sha256"], [s["outcomes_sha256"] for s in srcs])
    return {
        "schema": SCHEMA,
        "label": LABEL,
        "what": "Dice for sampling Zeref's replies, derived only by sha256 from these RECORDED IBM hardware shot "
                "records (public outcome commitments; per-round outcomes stay withheld). Not a live quantum "
                "connection, not a new measurement, and it does not change his brain.",
        "heart_seed": {"file": HEART_SEED, "version": heart["version"], "sha256": heart["heart_seed_sha256"]},
        "sources": srcs,
        "shots_by_class": {
            "measured_ibm_hardware": sum(s["measured_rounds"] for s in srcs),
            "other": 0,
            "note": "Only the measured IBM rounds above feed the dice. Rigetti SIMULATED ticks, unlabelled archive "
                    "samples and the classical-control rounds in the CHSH file are not used and not counted.",
        },
        "record_seed_sha256": seed,
        "sampler": {"temperature": TEMPERATURE, "top_k": TOP_K, "rules": "repetition_penalty 1.15 + no_repeat_ngram 3, then sample",
                    "turn_seed": "sha256('zeref-qrec-turn-v1|' + record_seed + '|' + roll + '|' + prompt ids joined by ',')",
                    "uniform": "first 13 hex of sha256(turn_seed + '|' + k) / 2^52",
                    "provenance_note": "Cory's HF card (phera-ra/QC67_cosmo) measured the decoder sampling seed as null for "
                                       "accuracy: the record buys replayable provenance and variety, not a smarter brain."},
    }


if __name__ == "__main__":
    import sys
    out = build_record(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    print(json.dumps(out, indent=1, ensure_ascii=False))
