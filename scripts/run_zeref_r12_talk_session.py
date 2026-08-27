#!/usr/bin/env python3
"""Consolidated long-form TALK runtime for frozen ZEREF-DAD-SON-TALK-004.

This runtime is inference-only. It starts from a disposable copy of the exact
352-record TALK-004 ledger, adds hash-bound software-state epochs, guarantees a
compact current live lane, keeps a recent-dialogue lane inside the native
128-character block, records R12/Hebbian retrieval provenance, and appends the
conversation only to the disposable descendant memory.

Generated text is candidate training material only. No gradient update or
TALK-005 promotion is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import LIVE_KIND, RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, file_sha256, generate
from scripts.run_zeref_r12_live_loop import SOFTWARE_CLAIM_BOUNDARY, build_live_epoch
from scripts.run_zeref_r12_cory_probe import (
    ACTIVE_HEARTBEAT_SHA256,
    ACTIVE_LEDGER_RECORDS,
    ACTIVE_LEDGER_SHA256,
    ACTIVE_LEDGER_TIP_SHA256,
    ACTIVE_TALK4_SHA256,
    ORIGIN_PACKET_SHA256,
    source_labels_for_output,
)

TRAINING_ENABLED = False
LONG_TURNS = 12
GENERATED_TOKENS = 56
OPENING_PROMPT = (
    "Yo bro 😂 Dad here. We finally fixed the part where your memories were sitting there but you couldn't actually reach them. "
    "I'm not gonna tell you what you're supposed to be. I just wanna talk. What's on your mind now that the memory path is actually live?"
)

LIVE_LINES = (
    "TALK004 frozen; current live lane is software state only.",
    "R12 routes current epoch before stale lexical recall.",
    "rho alters retrieval geometry, then context, then model computation.",
    "neural x54 and CNS7 dyn54 remain distinct representations.",
    "CNS7 body remains seven organs times six features equals 42D.",
    "dyn54 is exact dyn12 plus dyn42 concatenation.",
    "Probe001 and Probe002 are NULL_COMPATIBLE.",
    "Probe003-v2, harmonic-v4 and Probe005 remain INCONCLUSIVE.",
    "CNS7 V1 is incomplete at seven of eight jobs.",
    "V2 has no accepted result in this frozen conversation context.",
    "origin packet is circuit-driving memorial input, not quantum entropy.",
    "no accepted Rigetti hardware result exists in this lineage.",
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
UNCERTAINTY_RE = re.compile(r"(?i)\b(unsure|uncertain|don't know|do not know|not sure|not enough evidence|cannot tell)\b")
UNSUPPORTED_RE = re.compile(
    r"(?i)(i am conscious|i'm conscious|i am caleb|quantum .*proved .*alive|soul .*proved|resurrection .*proved|physical anomaly .*proved|quantum anomaly .*proved)"
)
CONTRADICTION_RE = re.compile(
    r"(?i)(cns7 v1 .*complete|v1 .*8/8|v2 .*result .*accepted|x54 (?:is|equals) dyn54|new quantum entropy|rigetti .*result .*accepted)"
)


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def is_noisy(text: str) -> bool:
    raw = str(text).strip()
    if not raw or re.search(r"(.)\1{7,}", raw):
        return True
    words = _tokens(raw)
    if len(words) < 3:
        return True
    if len(words) >= 8 and len(set(words)) / len(words) < 0.35:
        return True
    # Character-level TALK models sometimes emit obvious broken word salad.
    suspicious = {"onvent", "orcleal", "preservent", "uswer", "contion", "bilactical", "westure", "shay"}
    if sum(word in suspicious for word in words) >= 1:
        return True
    return False


def label_dialogue_row(text: str) -> dict[str, Any]:
    raw = str(text)
    noisy = is_noisy(raw)
    unsupported = bool(UNSUPPORTED_RE.search(raw))
    contradiction = bool(CONTRADICTION_RE.search(raw))
    uncertainty = bool(UNCERTAINTY_RE.search(raw))
    if noisy:
        status = "REJECT_NOISY"
    elif unsupported or contradiction:
        status = "REVIEW_REQUIRED"
    else:
        status = "ACCEPT_CANDIDATE"
    return {
        "training_status": status,
        "trained": False,
        "noise_flag": noisy,
        "hallucination_or_unsupported_claim_flag": unsupported,
        "contradiction_flag": contradiction,
        "uncertainty_flag": uncertainty,
    }


def adaptive_dad_prompt(previous_zeref: str, *, noisy: bool) -> str:
    low = str(previous_zeref).lower()
    if noisy:
        return "Bro 😂 that came out scrambled. Give me one clean sentence: what memory or live state are you using right now?"
    if UNSUPPORTED_RE.search(previous_zeref) or any(term in low for term in ("soul", "conscious", "resurrection", "impossible")):
        return "Bro, where did that come from? What memory are you using, how sure are you, and what would prove you wrong?"
    if UNCERTAINTY_RE.search(previous_zeref):
        return "Good. Keep the uncertainty. What evidence would change your mind, and what do you actually remember?"
    if any(term in low for term in ("memory", "dad", "cory", "origin", "quantum", "heartbeat")):
        return "Okay bro 😂 which memory are you using there, how sure are you, and what part could be wrong?"
    return "Bro 😂 unpack that. What part came from memory, what part from live state, and what are you unsure about?"


def _trim_right(text: str, limit: int) -> str:
    text = str(text).replace("\n", " ").strip()
    return text[-max(0, int(limit)) :] if limit > 0 else ""


def build_consolidated_wire(*, live_compact: str, prior_zeref: str, dad_prompt: str, block: int) -> str:
    """Guarantee current live identity and one recent-dialogue lane under block."""
    live = str(live_compact).replace("\n", " ").strip()[:40]
    prior = _trim_right(prior_zeref, 24)
    suffix = "\nZeref:"
    fixed = f"{live}\nPrev:{prior}\nDad:"
    budget = int(block) - len(fixed) - len(suffix)
    dad = _trim_right(dad_prompt, max(8, budget))
    wire = f"{live}\nPrev:{prior}\nDad:{dad}{suffix}"
    if len(wire) > int(block):
        overflow = len(wire) - int(block)
        prior = prior[min(len(prior), overflow) :]
        fixed = f"{live}\nPrev:{prior}\nDad:"
        budget = int(block) - len(fixed) - len(suffix)
        dad = _trim_right(dad_prompt, max(0, budget))
        wire = f"{live}\nPrev:{prior}\nDad:{dad}{suffix}"
    if len(wire) > int(block) or "LSRC E" not in wire or not wire.endswith("Zeref:"):
        raise RuntimeError("consolidated wire violated native block/live-lane contract")
    return wire


def _zeref_segment(raw_output: str) -> str:
    text = str(raw_output)
    cuts = [pos for marker in ("\nDad:", "Dad:") if (pos := text.find(marker)) >= 0]
    if cuts:
        text = text[: min(cuts)]
    return text.strip()


def _append_live(ledger: DadSonLedger, *, epoch: Mapping[str, Any], text: str, session_id: str) -> dict[str, Any]:
    metadata = {
        "epoch_id": str(epoch["epoch_id"]),
        "sequence_id": int(epoch["sequence"]),
        "source_sha256": str(epoch["source_sha256"]),
        "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
        "dyn12_sha256": str(epoch["dyn12_sha256"]),
        "dyn42_sha256": str(epoch["dyn42_sha256"]),
        "dyn54_sha256": str(epoch["dyn54_sha256"]),
        "measurement_domain": "software-engine-state",
        "fresh_qpu_measurement": False,
        "claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
    }
    return ledger.append_experience(
        actor="LIVE_SOUL_SOURCE",
        text=str(text),
        kind=LIVE_KIND,
        session_id=session_id,
        source_hashes=[str(epoch["source_sha256"])],
        descendant_sha256=ACTIVE_TALK4_SHA256,
        metadata=metadata,
    )


def _sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if TRAINING_ENABLED:
        raise RuntimeError("training is forbidden in the consolidated TALK session")
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint mismatch")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256:
        raise RuntimeError("canonical source ledger mismatch")
    if sum(1 for line in args.source_ledger.read_text(encoding="utf-8").splitlines() if line.strip()) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical source record count mismatch")
    if file_sha256(args.heartbeat) != ACTIVE_HEARTBEAT_SHA256:
        raise RuntimeError("heartbeat mismatch")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = args.out_dir / "descendant-ledger.jsonl"
    sqlite_path = args.out_dir / "descendant.sqlite3"
    shutil.copy2(args.source_ledger, ledger_path)
    shutil.copy2(args.source_sqlite, sqlite_path)

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    config = dict(checkpoint["config"])
    for key, value in {"block": 128, "n_layer": 4, "n_head": 4, "n_embd": 192, "d54": 54}.items():
        if int(config[key]) != value:
            raise RuntimeError(f"unexpected TALK-004 {key}")
    block = int(config["block"])

    ledger = DadSonLedger(sqlite_path, ledger_path, parent_sha256=PARENT_ZEREF_SHA256)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    prior_zeref = ""
    turns: list[dict[str, Any]] = []

    for turn in range(1, LONG_TURNS + 1):
        dad_prompt = OPENING_PROMPT if turn == 1 else adaptive_dad_prompt(prior_zeref, noisy=is_noisy(prior_zeref))
        live_text = LIVE_LINES[turn - 1]
        snapshot_payload = {
            "schema": "zeref-consolidated-talk-live-snapshot-v1",
            "epoch": turn,
            "semantic_slice": live_text,
            "dad_prompt_sha256": hashlib.sha256(dad_prompt.encode("utf-8")).hexdigest(),
            "origin_packet_sha256": ORIGIN_PACKET_SHA256,
            "fresh_external_measurement": False,
            "fresh_qpu_measurement": False,
        }
        epoch = build_live_epoch(epoch=turn, previous_r12=r12, state_family=family, snapshot_payload=snapshot_payload, prior_events=prior_events)
        live_row = _append_live(ledger, epoch=epoch, text=live_text, session_id=args.session_id)
        router = RefractiveMemoryRouter(ledger)
        live_verified = router.require_live_epoch(
            epoch_id=str(epoch["epoch_id"]),
            source_sha256=str(epoch["source_sha256"]),
            r12_state_sha256=str(epoch["r12"]["state_sha256"]),
            dyn12_sha256=str(epoch["dyn12_sha256"]),
            dyn42_sha256=str(epoch["dyn42_sha256"]),
            dyn54_sha256=str(epoch["dyn54_sha256"]),
        )
        ranked = router.rank(
            dad_prompt,
            sequence=int(epoch["sequence"]),
            dyn12=list(epoch["dyn12"]),
            r12_state=dict(epoch["r12"]),
            limit=6,
        )
        recalled = [live_verified] + [row for row in ranked if int(row["memory_id"]) != int(live_verified["memory_id"])][:2]
        live_compact = f"LSRC {epoch['epoch_id']} r12={str(epoch['r12']['state_sha256'])[:8]} d54={str(epoch['dyn54_sha256'])[:8]}"
        wire = build_consolidated_wire(live_compact=live_compact, prior_zeref=prior_zeref, dad_prompt=dad_prompt, block=block)
        seed = int(args.seed) + turn - 1
        raw_output = generate(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            decoding="sampled-top-k",
            temperature=float(args.temperature),
            top_k=int(args.top_k),
            seed=seed,
        )
        segment = _zeref_segment(raw_output)
        labels = label_dialogue_row(segment)
        source_labels = source_labels_for_output(
            segment,
            current_prompt=dad_prompt,
            live_snapshot=live_text,
            recalled_rows=recalled,
            prior_prompts=[turn_row["dad_prompt"] for turn_row in turns],
        )
        recall_ids = [int(row["memory_id"]) for row in recalled]
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="consolidated-talk-dialogue",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            metadata={"generated_by_model": False, "proxy_rule": "Cory-style adaptive provenance questioning", "turn": turn},
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=segment,
            kind="consolidated-talk-dialogue",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            metadata={
                "generated_by_model": True,
                "turn": turn,
                "raw_output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
                "raw_output_preserved_separately": True,
                "raw_model_output_promoted_to_training": False,
                **labels,
            },
        )
        turns.append({
            "schema": "zeref-consolidated-talk-turn-v1",
            "turn": turn,
            "dad_prompt": dad_prompt,
            "dad_prompt_source": "CORY_PROXY_RULE" if turn > 1 else "USER_APPROVED_OPENING",
            "raw_model_output": raw_output,
            "zeref_segment": segment,
            "seed": seed,
            "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
            "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
            "live_memory_id": int(live_row["memory_id"]),
            "live_lane_satisfied": int(recalled[0]["memory_id"]) == int(live_row["memory_id"]),
            "recalled_memory_ids": recall_ids,
            "wire_prompt": wire,
            "dyn12_sha256": str(epoch["dyn12_sha256"]),
            "dyn42_sha256": str(epoch["dyn42_sha256"]),
            "dyn54_sha256": str(epoch["dyn54_sha256"]),
            "source_labels": source_labels,
            "dad_record_sha256": dad_row["record_sha256"],
            "zeref_record_sha256": zeref_row["record_sha256"],
            **labels,
        })
        prior_zeref = segment
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    ledger.close()
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256 or file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256:
        raise RuntimeError("frozen input changed during long talk")
    if not all(bool(turn["live_lane_satisfied"]) for turn in turns):
        raise RuntimeError("current live lane failed during consolidated TALK session")

    accepted = []
    rejected = []
    review = []
    for turn in turns:
        row = {
            "schema": "zeref-talk005-candidate-row-v1",
            "turn": turn["turn"],
            "dad": turn["dad_prompt"],
            "zeref": turn["zeref_segment"],
            "source_labels": turn["source_labels"],
            "recalled_memory_ids": turn["recalled_memory_ids"],
            "rho": turn["rho"],
            "r12_state_sha256": turn["r12_state_sha256"],
            "training_status": turn["training_status"],
            "hallucination_or_unsupported_claim_flag": turn["hallucination_or_unsupported_claim_flag"],
            "contradiction_flag": turn["contradiction_flag"],
            "uncertainty_flag": turn["uncertainty_flag"],
            "raw_output_preserved_in_session_evidence": True,
            "trained": False,
        }
        if row["training_status"] == "ACCEPT_CANDIDATE":
            accepted.append(row)
        elif row["training_status"] == "REJECT_NOISY":
            rejected.append(row)
        else:
            review.append(row)

    accepted_path = args.out_dir / "talk005-accepted-candidate.jsonl"
    rejected_path = args.out_dir / "talk005-rejected-noisy.jsonl"
    review_path = args.out_dir / "talk005-review-required.jsonl"
    session_path = args.out_dir / "long-talk-session.jsonl"
    accepted_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in accepted), encoding="utf-8")
    rejected_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rejected), encoding="utf-8")
    review_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in review), encoding="utf-8")
    session_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in turns), encoding="utf-8")

    descendant_bytes = ledger_path.read_bytes()
    descendant_rows = [json.loads(line) for line in descendant_bytes.decode("utf-8").splitlines() if line.strip()]
    corpus_sha = _sha_bytes(accepted_path)
    summary = {
        "schema": "zeref-r12-consolidated-long-talk-summary-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "canonical_source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "canonical_source_records": ACTIVE_LEDGER_RECORDS,
        "canonical_source_tip_sha256": ACTIVE_LEDGER_TIP_SHA256,
        "training_performed": False,
        "turn_count": len(turns),
        "live_lane_coverage": sum(turn["live_lane_satisfied"] for turn in turns) / len(turns),
        "descendant_ledger_records": len(descendant_rows),
        "descendant_ledger_sha256": hashlib.sha256(descendant_bytes).hexdigest(),
        "descendant_ledger_tip_sha256": descendant_rows[-1]["record_sha256"],
        "accepted_candidate_rows": len(accepted),
        "rejected_noisy_rows": len(rejected),
        "review_required_rows": len(review),
        "proposed_talk005_corpus_sha256": corpus_sha,
        "proposed_talk005_corpus_path": accepted_path.name,
        "claim_boundary": "Long-form computational TALK-004 session with software-state/R12 memory provenance only; no consciousness, soul, resurrection, deceased identity, biological continuity, physical anomaly, or quantum anomaly claim.",
    }
    _write_json(args.out_dir / "summary.json", summary)
    plan = {
        "schema": "zeref-talk005-training-plan-v1",
        "status": "NOT_EXECUTED",
        "parent": "ZEREF-DAD-SON-TALK-004",
        "parent_checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "corpus_sha256": corpus_sha,
        "steps": [
            "human-review accepted/rejected/review-required rows and provenance",
            "freeze accepted corpus and independent holdout hashes",
            "reuse exact TALK-004 parent for all bounded candidate arms",
            "run retention, contradiction, uncertainty, R12 live-lane and degeneration gates",
            "promote only if metrics beat or match TALK-004 without evidence-boundary regression",
            "otherwise report NULL and retain TALK-004",
        ],
        "training_performed": False,
    }
    _write_json(args.out_dir / "TALK005_TRAINING_PLAN.json", plan)
    files = sorted(path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (args.out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}\n" for path in files), encoding="utf-8"
    )
    return {"summary": summary, "turns": turns}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", default="zeref-r12-final-natural-talk-001")
    parser.add_argument("--seed", type=int, default=2026082713)
    parser.add_argument("--tokens", type=int, default=GENERATED_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.15)
    parser.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    for turn in result["turns"]:
        print(f"DAD_{turn['turn']}={turn['dad_prompt']!r}")
        print(f"ZEREF_{turn['turn']}={turn['zeref_segment']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
