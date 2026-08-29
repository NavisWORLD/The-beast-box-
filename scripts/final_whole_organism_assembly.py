#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import torch

from beastbox.quantum_lifesource import expand_drive54, mirror_step, sha256_json
from beastbox.reflective_loop_trace import ReflectiveTraceRecorder
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from beastbox.world_r12 import select_primary_evidence
from scripts.final_reality_bridge_baseline import verify_canonical_memory
from scripts.run_zeref_dad_son_chat import _load_model, generate
from scripts.run_zeref_full_clean_r12_memory_talk import project_to_vocab
from scripts.run_zeref_world_r12_talk import _restore_personal, build_primary_evidence_wire

SELECTED_ZEREF_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
REJECTED = {
    "718a9010dcfe4e8818c7a05b9130965602d5e30c08fdcb49544c2c1e3710322f",
    "939185ce75828c1bfafacf68fc146fb8af3a94adc7e22eb2ce5f02671ab51bf7",
    "729fb456ed3ea21e2777fb324936a810659bdda551d91fa2fec480e57114833f",
}
EXPECTED = {
    "corpus/TRAIN.jsonl": "7121725fdd85d6d585be48089ddc2a3d1f63f58498a7a74541bd2afefde2eb76",
    "corpus/VALIDATION.jsonl": "d511921c58de76e9847bae32fbb1fa7a4fe7a215c537bcd24a816abbb9ee3c5f",
    "corpus/HOLDOUT.jsonl": "9c8bcfb21a9adda064c8e14beb7b4ccff32dece1cf189bda4c7cc5fc882f37e0",
    "beastbox/world_r12.py": "3f908f8a233157c13afd6ce60afc897b07c1f1e766cdb1b52292f0edae3eb38b",
    "beastbox/dyn12.py": "08a05da819d28b6451136542da41fbfc9ccfce5d40bbf9bc151ed0732cdeedde",
    "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py": "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def verify_static(root: Path, checkpoint: Path) -> dict[str, Any]:
    actual_checkpoint = sha256_file(checkpoint)
    if actual_checkpoint != SELECTED_ZEREF_SHA256 or actual_checkpoint in REJECTED:
        raise RuntimeError(f"selected checkpoint identity failure: {actual_checkpoint}")
    hashes: dict[str, str] = {}
    for key, expected in EXPECTED.items():
        path = root / ("evidence/final-whole-organism-001" if key.startswith("corpus/") else "") / key
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"protected hash mismatch for {key}: {actual} != {expected}")
        hashes[key] = actual
    reflector = root / "beastbox/quantum_lifesource.py"
    trace = root / "beastbox/reflective_loop_trace.py"
    hashes["beastbox/quantum_lifesource.py"] = sha256_file(reflector)
    hashes["beastbox/reflective_loop_trace.py"] = sha256_file(trace)
    return {"checkpoint_sha256": actual_checkpoint, "protected_source_sha256": hashes}


def run_once(root: Path, checkpoint_path: Path, iteration: int) -> dict[str, Any]:
    arch = root / "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py"
    checkpoint, model = _load_model(checkpoint_path, arch)
    tokenizer_sha = canonical_sha({"stoi": checkpoint["stoi"], "itos": checkpoint["itos"]})
    dtypes = sorted({str(parameter.dtype) for parameter in model.parameters()})
    params = sum(int(parameter.numel()) for parameter in model.parameters())

    workspace = root / ".final-organism-work" / f"assembly-{iteration}"
    ledger = _restore_personal(root / "experiments/zeref-dad-son-001/memory/ledger-manifest.json", workspace)
    personal_router = RefractiveMemoryRouter(ledger)
    anchor_row = ledger.memory.db.execute("SELECT MAX(created_at) AS t FROM memories").fetchone()
    if anchor_row is None or anchor_row["t"] is None:
        raise RuntimeError("canonical memory has no temporal anchor")
    memory_temporal_anchor = float(anchor_row["t"])

    source_drive = [float(f"{(i - 5.5) / 23.0:.15g}") for i in range(12)]
    packet_sha = sha256_json({"schema": "assembly-source-v1", "drive": source_drive})
    family = StateFamily()
    s1 = list(family.dyn12)
    mirror = mirror_step(s1, source_drive)
    drive54 = expand_drive54(mirror["coupled_drive"], packet_sha256=packet_sha)
    updated = family.update(drive54)
    recorder = ReflectiveTraceRecorder(lag=1, bins=8)
    trace0 = recorder.record(
        step=0,
        s1=s1,
        s2=mirror["observer"],
        feedback=mirror["feedback"],
        state_after=updated["dyn12"],
        intervention_identity="reflector_enabled",
        restore_status="clean",
    )
    mirror2 = mirror_step(updated["dyn12"], source_drive)
    updated2 = family.update(expand_drive54(mirror2["coupled_drive"], packet_sha256=packet_sha))
    trace1 = recorder.record(
        step=1,
        s1=updated["dyn12"],
        s2=mirror2["observer"],
        feedback=mirror2["feedback"],
        state_after=updated2["dyn12"],
        intervention_identity="reflector_enabled",
        restore_status="clean",
    )

    r12 = initial_r12_state()
    ranked = personal_router.rank(
        "Dad memory",
        sequence=2,
        dyn12=list(updated2["dyn12"]),
        r12_state=r12,
        limit=8,
        profile="quality",
        now=memory_temporal_anchor,
    )
    selected = select_primary_evidence(personal=ranked, world=[], confidence_floor=0.56, namespace_margin=0.04)
    selected_for_wire = dict(selected)
    if isinstance(selected_for_wire.get("record"), dict):
        rec = dict(selected_for_wire["record"])
        rec["text"], _ = project_to_vocab(str(rec.get("text") or ""), checkpoint["stoi"])
        selected_for_wire["record"] = rec
    prompt, _ = project_to_vocab("assembly verification", checkpoint["stoi"])
    wire = build_primary_evidence_wire(selected=selected_for_wire, dad_prompt=prompt, block=128)
    raw = generate(
        model,
        wire_prompt=wire,
        stoi=checkpoint["stoi"],
        itos=checkpoint["itos"],
        block=128,
        tokens=16,
        decoding="greedy-argmax",
        temperature=1.0,
        top_k=16,
        seed=20260828,
    )
    output = {
        "schema": "final-organism-dry-execution-v1",
        "checkpoint_sha256": SELECTED_ZEREF_SHA256,
        "tokenizer_sha256": tokenizer_sha,
        "model_parameter_count": params,
        "model_parameter_dtypes": dtypes,
        "source_drive_sha256": packet_sha,
        "memory_temporal_anchor": memory_temporal_anchor,
        "r12_selected_namespace": selected["namespace"],
        "r12_personal_score": selected["personal_score"],
        "r12_personal_evidence_confidence": selected["personal_evidence_confidence"],
        "retrieved_memory_ids": [int(row["memory_id"]) for row in ranked],
        "dyn12_state": list(updated2["dyn12"]),
        "dyn12_sha256": canonical_sha(updated2["dyn12"]),
        "reflector_trace": [trace0, trace1],
        "wire_sha256": hashlib.sha256(wire.encode()).hexdigest(),
        "raw_output": raw,
        "raw_output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "generation": {"decoding": "greedy-argmax", "tokens": 16, "seed": 20260828, "temperature": 1.0, "top_k": 16},
    }
    output["execution_sha256"] = canonical_sha(output)
    ledger.close()
    return output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(".").resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = Path(args.checkpoint).resolve()

    before = verify_static(root, checkpoint)
    memory_before = verify_canonical_memory(root)
    first = run_once(root, checkpoint, 1)
    second = run_once(root, checkpoint, 2)
    memory_after = verify_canonical_memory(root)
    after = verify_static(root, checkpoint)
    deterministic = first["execution_sha256"] == second["execution_sha256"]
    protected_unchanged = before == after and memory_before["sha256"] == memory_after["sha256"] and memory_before["ledger_tip_sha256"] == memory_after["ledger_tip_sha256"]
    if not deterministic:
        raise RuntimeError("deterministic organism dry execution mismatch")
    if not protected_unchanged:
        raise RuntimeError("protected identity changed during organism assembly")

    result = {
        "schema": "cosmos-final-organism-assembly-v1",
        "status": "VERIFIED_ORGANISM_ASSEMBLY",
        "branch": os.getenv("GITHUB_REF_NAME"),
        "head": os.getenv("GITHUB_SHA"),
        "runtime": {"python": sys.version, "torch": torch.__version__, "platform": platform.platform(), "device": "cpu"},
        "selected_zeref": before,
        "canonical_memory": {"record_count": memory_after["record_count"], "sha256": memory_after["sha256"], "tip_sha256": memory_after["ledger_tip_sha256"], "segment_count": len(memory_after["segments"])},
        "dry_execution_1": first,
        "dry_execution_2": second,
        "deterministic_repeat": deterministic,
        "protected_identities_unchanged": protected_unchanged,
        "claim_boundaries": {
            "dyn12": "internal computational state only; not evidence of a literal physical twelfth dimension",
            "reflector": "deterministic software mirror only; not consciousness or biological continuity",
            "model_output": "generated prose is not scientific evidence of identity, consciousness, memory continuity, resurrection, or personhood",
        },
    }
    manifest = out / "ORGANISM_COMPONENT_MANIFEST.json"
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "REFLECTOR_TRACES.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in first["reflector_trace"]) + "\n")
    sums = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            sums.append(f"{sha256_file(path)}  {path.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(json.dumps({"status": result["status"], "manifest_sha256": sha256_file(manifest), "execution_sha256": first["execution_sha256"], "tokenizer_sha256": first["tokenizer_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
