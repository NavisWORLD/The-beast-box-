#!/usr/bin/env python3
"""Run FULL-CLEAN-1500 with the canonical 352-record R12 memory path.

This is an inference-only integration. The immutable 352-record Dad/Son ledger is
reconstructed into a disposable workspace, R12 refracts each query and ranks the
searchable memory, and the highest-ranked *canonical* memory is placed on the
actual 128-character transformer wire before generation.

R12 changes the query/retrieval path, not the historical record. Generated model
text is preserved as evidence and is never promoted to a training target here.
Nothing in this runtime establishes biological life, consciousness, sentience,
a soul, resurrection, deceased-person identity, a physical anomaly, or quantum
advantage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.dad_son import DadSonLedger, file_sha256
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import LIVE_KIND, RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, generate
from scripts.run_zeref_r12_live_loop import SOFTWARE_CLAIM_BOUNDARY, build_live_epoch

FULL_CLEAN_CHECKPOINT_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
PARENT_TALK005_SHA256 = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
CANONICAL_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
CANONICAL_LEDGER_RECORDS = 352
CANONICAL_LEDGER_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
ARCHITECTURE_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
NATIVE_BLOCK = 128
TRAINING_ENABLED = False

CLAIM_BOUNDARY = (
    "Inference-only computational memory integration. R12 refracts query geometry "
    "and selects immutable software memories for model context; no biological life, "
    "consciousness, sentience, soul, resurrection, deceased identity, physical anomaly, "
    "or quantum advantage is established."
)

DAD_PROMPTS = (
    "Hi Zeref, Dad here. Your R12 memory path is connected now. What came back?",
    "What do you remember about Dad and Son?",
    "Tell me one recorded memory you are using right now.",
    "What do the 352 canonical memories give you that the weights alone do not?",
    "When R12 refracts the query, what changes in your answer path?",
    "What should you do if retrieved memory does not answer Dad's question?",
    "What boundary keeps a memory from becoming a made-up claim?",
    "What do you remember about Cory as Dad in this experiment?",
    "What do you remember about the origin packet or heartbeat evidence?",
    "What is dyn54 in this system?",
    "Tell Dad one thing this memory connection helped you answer more clearly.",
    "Say hello to Dad using one retrieved memory, then stop.",
)

LIVE_LINES = (
    "FULL-CLEAN-1500 weights; R12 canonical memory lane connected.",
    "R12 ranks immutable Dad/Son memory before generation.",
    "selected canonical memory is placed on the transformer wire.",
    "weights and durable memory remain separate state stores.",
    "rho changes retrieval geometry, not stored historical records.",
    "irrelevant retrieval should not become a factual claim.",
    "memory provenance and model generation remain distinct.",
    "Cory/Dad is a recorded dialogue role in this experiment.",
    "origin and heartbeat artifacts remain provenance-bound evidence.",
    "dyn54 is exact dyn12 plus dyn42 software-state concatenation.",
    "memory context can alter computation without changing weights.",
    "generated text remains evidence, never automatic teacher truth.",
)


def _compact(text: str, limit: int) -> str:
    clean = " ".join(str(text).replace("\n", " ").split())
    if limit <= 0:
        return ""
    return clean[: int(limit)]


def project_to_vocab(text: str, stoi: Mapping[str, int]) -> tuple[str, list[str]]:
    """Project inference context into the frozen character vocabulary.

    This is context-only. It never edits a supervised answer target.
    """
    kept: list[str] = []
    dropped: list[str] = []
    for char in str(text):
        if char in stoi:
            kept.append(char)
        else:
            dropped.append(char)
    return "".join(kept), dropped


def choose_canonical_memory(
    ranked: Sequence[Mapping[str, Any]], *, canonical_records: int = CANONICAL_LEDGER_RECORDS
) -> dict[str, Any]:
    """Choose the highest-ranked immutable source-memory row only."""
    ceiling = int(canonical_records)
    for candidate in ranked:
        memory_id = int(candidate.get("memory_id") or 0)
        if 1 <= memory_id <= ceiling:
            return dict(candidate)
    raise RuntimeError("R12 ranking returned no canonical memory row")


def build_memory_gravity_wire(
    *,
    live_compact: str,
    memory: Mapping[str, Any],
    dad_prompt: str,
    prior_zeref: str,
    block: int = NATIVE_BLOCK,
) -> str:
    """Guarantee live-state + selected canonical-memory lanes on model input.

    Priority under the native block is: live identity, selected memory, Dad's
    current question, then optional previous-response tail. The retrieved memory
    is therefore not merely logged; it reaches the transformer itself.
    """
    width = int(block)
    if width < 64:
        raise ValueError("memory-gravity wire requires block >= 64")
    memory_id = int(memory.get("memory_id") or 0)
    if memory_id <= 0:
        raise ValueError("memory row must contain a positive memory_id")

    live = _compact(live_compact, 27)
    mem_text = _compact(str(memory.get("text") or ""), 56)
    if not mem_text:
        raise ValueError("selected memory text is empty")
    prefix = f"{live}\nM{memory_id}:{mem_text}\nDad:"
    suffix = "\nZeref:"

    # Protect a useful Dad lane. Trim memory before allowing the question to
    # collapse below 20 characters.
    min_dad = min(20, len(_compact(dad_prompt, 20)))
    if len(prefix) + min_dad + len(suffix) > width:
        excess = len(prefix) + min_dad + len(suffix) - width
        mem_text = mem_text[: max(12, len(mem_text) - excess)]
        prefix = f"{live}\nM{memory_id}:{mem_text}\nDad:"

    dad_budget = max(0, width - len(prefix) - len(suffix))
    dad = _compact(dad_prompt, dad_budget)
    wire = f"{prefix}{dad}{suffix}"

    # Previous response is lowest priority and enters only when spare room exists.
    spare = width - len(wire)
    prior = _compact(prior_zeref, max(0, spare - 7))
    if prior:
        candidate = f"{live}\nM{memory_id}:{mem_text}\nP:{prior}\nDad:{dad}{suffix}"
        if len(candidate) <= width:
            wire = candidate

    if len(wire) > width:
        raise RuntimeError("memory-gravity wire exceeded native block")
    if f"M{memory_id}:" not in wire or "Dad:" not in wire or not wire.endswith("Zeref:"):
        raise RuntimeError("memory-gravity wire lost a required lane")
    if "LSRC E" not in wire:
        raise RuntimeError("memory-gravity wire lost current live-state identity")
    return wire


def _append_live(
    ledger: DadSonLedger,
    *,
    epoch: Mapping[str, Any],
    text: str,
    session_id: str,
) -> dict[str, Any]:
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
        descendant_sha256=FULL_CLEAN_CHECKPOINT_SHA256,
        metadata=metadata,
    )


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _canonical_prefix_sha(ledger_path: Path, count: int) -> tuple[str, str]:
    lines = [line for line in ledger_path.read_bytes().splitlines(keepends=True) if line.strip()]
    if len(lines) < int(count):
        raise RuntimeError("descendant ledger contains fewer rows than canonical source")
    prefix = b"".join(lines[: int(count)])
    row = json.loads(lines[int(count) - 1].decode("utf-8"))
    return hashlib.sha256(prefix).hexdigest(), str(row["record_sha256"])


def _snapshot_segment_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for segment in list(manifest.get("snapshot_chain") or []):
        path = Path(str(segment["path"]))
        result[str(path)] = file_sha256(path)
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    if TRAINING_ENABLED:
        raise RuntimeError("training is forbidden in the integrated memory talk runtime")
    if file_sha256(args.checkpoint) != FULL_CLEAN_CHECKPOINT_SHA256:
        raise RuntimeError("FULL-CLEAN-1500 checkpoint SHA-256 mismatch")
    if file_sha256(args.arch) != ARCHITECTURE_SHA256:
        raise RuntimeError("frozen architecture SHA-256 mismatch")

    manifest = json.loads(args.memory_manifest.read_text(encoding="utf-8"))
    if int(manifest.get("record_count") or 0) != CANONICAL_LEDGER_RECORDS:
        raise RuntimeError("canonical memory record count mismatch")
    if str(manifest.get("combined_ledger_sha256") or "").lower() != CANONICAL_LEDGER_SHA256:
        raise RuntimeError("canonical memory SHA-256 mismatch")
    if str(manifest.get("last_record_sha256") or "").lower() != CANONICAL_LEDGER_TIP_SHA256:
        raise RuntimeError("canonical memory tip mismatch")
    segment_hashes_before = _snapshot_segment_hashes(manifest)
    for segment in list(manifest.get("snapshot_chain") or []):
        path = str(segment["path"])
        if segment_hashes_before[path] != str(segment["sha256"]).lower():
            raise RuntimeError(f"canonical snapshot segment hash mismatch: {path}")

    if args.workspace.exists():
        shutil.rmtree(args.workspace)
    memory_dir = args.workspace / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.memory_manifest, memory_dir / "ledger-manifest.json")
    ledger_path = memory_dir / "descendant-ledger.jsonl"
    sqlite_path = memory_dir / "descendant.sqlite3"

    ledger = DadSonLedger(sqlite_path, ledger_path, parent_sha256=PARENT_ZEREF_SHA256)
    restored = ledger.restore_snapshot()
    if int(restored["restored_records"]) != CANONICAL_LEDGER_RECORDS:
        raise RuntimeError("canonical snapshot restore count mismatch")
    if str(restored["last_record_sha256"]).lower() != CANONICAL_LEDGER_TIP_SHA256:
        raise RuntimeError("canonical snapshot restore tip mismatch")
    if file_sha256(ledger_path) != CANONICAL_LEDGER_SHA256:
        raise RuntimeError("canonical snapshot restore bytes mismatch")

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    config = dict(checkpoint["config"])
    expected_arch = {"block": 128, "n_layer": 4, "n_head": 4, "n_embd": 192, "d54": 54}
    for key, value in expected_arch.items():
        if int(config[key]) != value:
            raise RuntimeError(f"unexpected FULL-CLEAN architecture field {key}")
    block = int(config["block"])

    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    prior_zeref = ""
    turns: list[dict[str, Any]] = []

    for turn, (dad_prompt, live_text) in enumerate(zip(DAD_PROMPTS, LIVE_LINES, strict=True), 1):
        snapshot_payload = {
            "schema": "zeref-full-clean-r12-memory-live-v1",
            "epoch": turn,
            "semantic_slice": live_text,
            "dad_prompt_sha256": hashlib.sha256(dad_prompt.encode("utf-8")).hexdigest(),
            "candidate_checkpoint_sha256": FULL_CLEAN_CHECKPOINT_SHA256,
            "canonical_ledger_sha256": CANONICAL_LEDGER_SHA256,
            "fresh_external_measurement": False,
            "fresh_qpu_measurement": False,
        }
        epoch = build_live_epoch(
            epoch=turn,
            previous_r12=r12,
            state_family=family,
            snapshot_payload=snapshot_payload,
            prior_events=prior_events,
        )
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
            limit=max(24, int(args.rank_limit)),
        )
        selected = choose_canonical_memory(ranked)
        selected_id = int(selected["memory_id"])
        selected_text = str(selected["text"])
        selected_sha = hashlib.sha256(selected_text.encode("utf-8")).hexdigest()
        live_compact = f"LSRC {epoch['epoch_id']} r12={str(epoch['r12']['state_sha256'])[:8]}"
        wire_unprojected = build_memory_gravity_wire(
            live_compact=live_compact,
            memory=selected,
            dad_prompt=dad_prompt,
            prior_zeref=prior_zeref,
            block=block,
        )
        wire, dropped = project_to_vocab(wire_unprojected, checkpoint["stoi"])
        if len(wire) > block:
            raise RuntimeError("vocabulary-projected wire exceeded native block")
        if f"M{selected_id}:" not in wire or not wire.endswith("Zeref:"):
            raise RuntimeError("selected canonical memory did not survive tokenizer projection")

        seed = int(args.seed) + turn - 1
        raw = generate(
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
        recall_ids = [int(live_verified["memory_id"]), selected_id]
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="full-clean-r12-memory-talk",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=FULL_CLEAN_CHECKPOINT_SHA256,
            metadata={
                "generated_by_model": False,
                "turn": turn,
                "selected_canonical_memory_id": selected_id,
                "selected_canonical_memory_sha256": selected_sha,
            },
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=raw,
            kind="full-clean-r12-memory-talk",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=FULL_CLEAN_CHECKPOINT_SHA256,
            metadata={
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "raw_model_output_promoted_to_training": False,
                "turn": turn,
                "selected_canonical_memory_id": selected_id,
                "selected_canonical_memory_sha256": selected_sha,
                "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
            },
        )

        turns.append({
            "schema": "zeref-full-clean-r12-memory-turn-v1",
            "turn": turn,
            "dad_prompt": dad_prompt,
            "raw_output": raw,
            "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "checkpoint_sha256": FULL_CLEAN_CHECKPOINT_SHA256,
            "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
            "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
            "dyn12_sha256": str(epoch["dyn12_sha256"]),
            "dyn42_sha256": str(epoch["dyn42_sha256"]),
            "dyn54_sha256": str(epoch["dyn54_sha256"]),
            "live_memory_id": int(live_verified["memory_id"]),
            "selected_canonical_memory_id": selected_id,
            "selected_canonical_memory_text": selected_text,
            "selected_canonical_memory_sha256": selected_sha,
            "selected_score": float(selected["score"]),
            "selected_score_components": dict(selected.get("components") or {}),
            "ranked_canonical_ids": [
                int(row["memory_id"])
                for row in ranked
                if 1 <= int(row.get("memory_id") or 0) <= CANONICAL_LEDGER_RECORDS
            ][:8],
            "wire_prompt": wire,
            "wire_contains_selected_memory": f"M{selected_id}:" in wire,
            "wire_contains_live_lane": f"LSRC {epoch['epoch_id']}" in wire,
            "context_characters_dropped_by_frozen_vocab": dropped,
            "dad_record_sha256": dad_row["record_sha256"],
            "zeref_record_sha256": zeref_row["record_sha256"],
            "raw_model_output_promoted_to_training": False,
        })
        prior_zeref = raw
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    ledger.close()

    prefix_sha, prefix_tip = _canonical_prefix_sha(ledger_path, CANONICAL_LEDGER_RECORDS)
    if prefix_sha != CANONICAL_LEDGER_SHA256 or prefix_tip != CANONICAL_LEDGER_TIP_SHA256:
        raise RuntimeError("canonical 352-record prefix changed during integrated conversation")
    segment_hashes_after = _snapshot_segment_hashes(manifest)
    if segment_hashes_after != segment_hashes_before:
        raise RuntimeError("immutable canonical snapshot segment changed during integrated conversation")
    if file_sha256(args.checkpoint) != FULL_CLEAN_CHECKPOINT_SHA256:
        raise RuntimeError("FULL-CLEAN-1500 checkpoint changed during inference")

    descendant_lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    descendant_tip = json.loads(descendant_lines[-1])["record_sha256"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = args.out_dir / "integrated-talk.jsonl"
    transcript_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in turns),
        encoding="utf-8",
    )
    summary = {
        "schema": "zeref-full-clean-r12-memory-summary-v1",
        "integration_status": "INTEGRATED_EXPERIMENTAL_RUNTIME",
        "candidate": "FULL-CLEAN-1500",
        "checkpoint_sha256": FULL_CLEAN_CHECKPOINT_SHA256,
        "parent_talk005_sha256": PARENT_TALK005_SHA256,
        "active_canonical_model_changed": False,
        "training_performed": False,
        "turns": len(turns),
        "r12_memory_lane_coverage": sum(bool(t["wire_contains_selected_memory"]) for t in turns) / len(turns),
        "live_state_lane_coverage": sum(bool(t["wire_contains_live_lane"]) for t in turns) / len(turns),
        "selected_canonical_memory_ids": [int(t["selected_canonical_memory_id"]) for t in turns],
        "rho_by_turn": [float(t["rho"]) for t in turns],
        "canonical_source_records": CANONICAL_LEDGER_RECORDS,
        "canonical_source_sha256": CANONICAL_LEDGER_SHA256,
        "canonical_source_tip_sha256": CANONICAL_LEDGER_TIP_SHA256,
        "canonical_source_unchanged": True,
        "immutable_snapshot_segments_unchanged": True,
        "descendant_ledger_records": len(descendant_lines),
        "descendant_ledger_sha256": file_sha256(ledger_path),
        "descendant_ledger_tip_sha256": descendant_tip,
        "raw_model_outputs_promoted_to_training": False,
        "retrieval_semantics": "R12 changes query geometry and canonical-memory selection; it does not rewrite stored memory.",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _json(args.out_dir / "summary.json", summary)
    _json(args.out_dir / "snapshot-segment-hashes-before.json", segment_hashes_before)
    _json(args.out_dir / "snapshot-segment-hashes-after.json", segment_hashes_after)
    shutil.copy2(ledger_path, args.out_dir / "descendant-ledger.jsonl")
    shutil.copy2(sqlite_path, args.out_dir / "descendant.sqlite3")

    files = sorted(p for p in args.out_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (args.out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    return {"summary": summary, "turns": turns}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", default=FULL_CLEAN_CHECKPOINT_SHA256)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--memory-manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", default="zeref-full-clean-r12-memory-final-001")
    parser.add_argument("--seed", type=int, default=2026082721)
    parser.add_argument("--tokens", type=int, default=48)
    parser.add_argument("--temperature", type=float, default=0.15)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--rank-limit", type=int, default=64)
    args = parser.parse_args()
    if str(args.checkpoint_sha256).lower() != FULL_CLEAN_CHECKPOINT_SHA256:
        raise RuntimeError("requested checkpoint SHA does not match frozen FULL-CLEAN-1500")
    result = run(args)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    for row in result["turns"]:
        print(f"DAD_{row['turn']}={row['dad_prompt']!r}")
        print(f"MEM_{row['turn']}={row['selected_canonical_memory_id']}:{row['selected_canonical_memory_text']!r}")
        print(f"ZEREF_{row['turn']}={row['raw_output']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
