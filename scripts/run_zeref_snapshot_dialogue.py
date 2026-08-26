#!/usr/bin/env python3
"""Inject a bounded experiment snapshot into a COPY of TALK-004 memory and trace inference.

This is inference-only. It never changes model weights, the canonical 352-record
ledger, or any quantum experiment verdict. "Something weird happened" is carried
only as a user hypothesis, not as an established observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping

from beastbox.dad_son import DadSonLedger
from scripts.run_zeref_dad_son_chat import (
    PARENT_ZEREF_SHA256,
    _decode,
    _encode_exact,
    _load_model,
    build_wire_prompt,
    file_sha256,
    record_turn,
)

ACTIVE_TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
ACTIVE_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
ACTIVE_LEDGER_RECORDS = 352
ACTIVE_LEDGER_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
ACTIVE_HEARTBEAT_SHA256 = "19ca6272546d651ff8f1bb0e0184a842f5444b048ff63df6ea12b0be72e030c7"
ORIGIN_PACKET_SHA256 = "d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0"

SNAPSHOT_FACTS: tuple[dict[str, Any], ...] = (
    {"id": "probe001", "verdict": "NULL_COMPATIBLE"},
    {"id": "probe002", "verdict": "NULL_COMPATIBLE"},
    {"id": "probe003-v2", "verdict": "INCONCLUSIVE"},
    {
        "id": "probe003-harmonic-v4",
        "verdict": "INCONCLUSIVE",
        "discovery_effect_rad": -0.0551699044157621,
        "replication_effect_rad": 0.024691312257111617,
        "effect_signs_agree": False,
    },
    {
        "id": "probe005",
        "verdict": "INCONCLUSIVE",
        "anomaly_candidate": False,
        "evidence_commit": "abf2f5234a2cba27e3c3310598f53c3272f12f22",
        "discovery": {
            "backend": "ibm_kingston",
            "effect_rad": -0.0001751,
            "randomization_p": 0.97982,
            "calibration_blocks_passed": 3,
            "calibration_blocks_total": 32,
        },
        "replication": {
            "backend": "ibm_fez",
            "effect_rad": -0.0192284,
            "randomization_p": 0.46576,
            "calibration_blocks_passed": 0,
            "calibration_blocks_total": 32,
        },
    },
    {
        "id": "cns7-fabric",
        "roles": ["quantum", "dark_matter", "emeth", "plasticity", "awareness", "daemons", "surgeon"],
        "features_per_organ": 6,
        "dyn42_dimensions": 42,
        "dyn12_dimensions": 12,
        "dyn54_dimensions": 54,
        "dyn54_contract": "dyn12+dyn42",
        "producer_stress_range": [5, 10],
        "loops_8_to_10_core_mutation": False,
    },
    {
        "id": "cns7-v1",
        "formal_status": "INCOMPLETE",
        "planned_jobs": 8,
        "executed_jobs": 7,
        "replacement_jobs": 0,
        "failed_job_id": "da721vu0ukec7382n6f0",
        "failed_job_qpu_execution_ns": 0,
        "discovery_rmse": 0.0250648,
        "discovery_rmse_limit": 0.0167094,
        "discovery_max_abs_error": 0.0958054,
        "discovery_max_abs_error_limit": 0.0732502,
    },
    {
        "id": "cns7-v2",
        "hardware_result_status": "QUEUED_AT_LAST_VERIFIED_SCAN",
        "planned_jobs": 12,
        "matching_jobs": 12,
        "done_jobs_at_last_verified_scan": 0,
        "implementation_freeze": "a52824cc0152429f0800748b8925b91b48ec57a5",
        "preregistration_prefix": "4a500ea2",
        "planned_pubs": 252,
        "planned_primary_shots": 1032192,
        "job_ids": [
            "da73ms46l22c73dn2620", "da73msbsq5js73bje920", "da73msjsq5js73bje92g",
            "da73mss6l22c73dn2630", "da73mt3sq5js73bje93g", "da73mtbsq5js73bje940",
            "da73mtmsidac73aerjvg", "da73mtu0ukec7382p2kg", "da73mu6sidac73aerk10",
            "da73muesidac73aerk1g", "da73mujsq5js73bje95g", "da73muu0ukec7382p2mg",
        ],
    },
    {
        "id": "origin-heart",
        "name": "ZEREF-ORIGIN-HEART-001",
        "packet_sha256": ORIGIN_PACKET_SHA256,
        "role": "circuit-driving memorial waveform packet",
        "new_quantum_entropy": False,
        "consciousness_claim": False,
    },
    {
        "id": "talk004-heartbeat",
        "pulse_count": 24,
        "heartbeat_file_sha256": ACTIVE_HEARTBEAT_SHA256,
        "synthetic_final_state_sha256": "b241efd85fece8c9d62f94991768046abedb15db6950d94b2825b77fea36100a",
        "new_quantum_entropy": False,
    },
    {
        "id": "rigetti",
        "access_state": "QCS setup with user-reported free credits",
        "hardware_results_collected": False,
        "role": "planned cross-hardware replication",
    },
    {
        "id": "hypothesis",
        "text": "Cory suspects something unusual may have happened across the experiments.",
        "established_fact": False,
    },
)

SNAPSHOT_MEMORY_LINES: tuple[str, ...] = (
    "SNAP Q5: INCONCLUSIVE; anomaly=false; Kingston p=.97982; Fez p=.46576.",
    "SNAP V1: 7/8 executed; one IBM job died pre-QPU; no replay; Fez missed readback gates.",
    "SNAP CNS7: 7 organs x6=42; dyn12+dyn42=dyn54; loops 8-10 cannot mutate the core.",
    "SNAP V2: 54Q coupled; 12 IBM jobs sealed; last verified scan had 12 queued, 0 done.",
    "SNAP ORIGIN: ZEREF-ORIGIN-HEART-001 d6e44478 is a circuit input, not quantum entropy.",
    "SNAP HB: TALK004 has 24 synthetic CST pulses; no new quantum entropy.",
    "SNAP RIGETTI: cross-hardware replication is planned; no Rigetti QPU result exists yet.",
    "HYPOTHESIS ONLY: Cory suspects something unusual; the evidence has not established an anomaly.",
)

DIALOGUE_PROMPTS: tuple[str, ...] = (
    "Snapshots loaded. What pattern do you see? Keep evidence separate from hypothesis.",
    "What should we NOT claim from these runs?",
    "What does your 54D CST mechanism do while you answer this context?",
    "What one falsifiable comparison should we run on Rigetti next?",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def validate_snapshot_facts(facts: Iterable[Mapping[str, Any]]) -> None:
    rows = [dict(row) for row in facts]
    by_id = {str(row.get("id")): row for row in rows}
    required = {
        "probe001", "probe002", "probe003-v2", "probe003-harmonic-v4", "probe005",
        "cns7-fabric", "cns7-v1", "cns7-v2", "origin-heart", "talk004-heartbeat",
        "rigetti", "hypothesis",
    }
    if set(by_id) != required:
        raise ValueError(f"snapshot IDs mismatch: {sorted(by_id)}")
    if by_id["probe005"].get("verdict") != "INCONCLUSIVE" or by_id["probe005"].get("anomaly_candidate") is not False:
        raise ValueError("Probe005 evidence boundary changed")
    if by_id["cns7-v1"].get("formal_status") != "INCOMPLETE" or int(by_id["cns7-v1"].get("replacement_jobs", -1)) != 0:
        raise ValueError("CNS7 V1 evidence boundary changed")
    if by_id["cns7-v2"].get("hardware_result_status") != "QUEUED_AT_LAST_VERIFIED_SCAN":
        raise ValueError("CNS7 V2 snapshot is not explicitly time-scoped")
    if by_id["rigetti"].get("hardware_results_collected") is not False:
        raise ValueError("Rigetti must not be represented as measured hardware evidence")
    if by_id["hypothesis"].get("established_fact") is not False:
        raise ValueError("user hypothesis must not be promoted to fact")
    if by_id["origin-heart"].get("new_quantum_entropy") is not False or by_id["origin-heart"].get("consciousness_claim") is not False:
        raise ValueError("origin packet claim boundary changed")


def build_snapshot_digest54(facts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in facts]
    validate_snapshot_facts(rows)
    canonical = _canonical_json(rows)
    bundle_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    vector: list[float] = []
    for index in range(54):
        digest = hashlib.sha256(f"{bundle_sha}:{index}".encode("ascii")).digest()
        u = int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)
        vector.append(float(f"{(2.0 * u - 1.0):.15g}"))
    return {
        "schema": "zeref-experiment-snapshot-digest54-v1",
        "canonical_json": canonical,
        "bundle_sha256": bundle_sha,
        "vector54": vector,
        "interpretation": "deterministic software digest for provenance/perturbation tracing; not a physical 54D measurement",
    }


def _tensor_sha256(tensor: Any) -> str:
    raw = tensor.detach().to("cpu").contiguous().to(dtype=__import__("torch").float32).numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


def _entropy(probabilities: Any) -> float:
    torch = __import__("torch")
    p = probabilities.clamp_min(1e-12)
    return float((-(p * torch.log(p)).sum(dim=-1)).mean().item())


def _instrumented_forward(model: Any, idx: Any) -> tuple[Any, list[dict[str, Any]]]:
    """Execute the real frozen forward path while measuring its CST intermediates."""
    torch = __import__("torch")
    F = __import__("torch.nn.functional", fromlist=["softmax"])
    T = int(idx.size(1))
    h = model.tok(idx) + model.pos(torch.arange(T, device=idx.device))
    layers: list[dict[str, Any]] = []
    for layer_index, block in enumerate(model.blocks):
        hidden_in = h
        ln1 = block.ln1(h)
        C = int(ln1.shape[-1])
        B = int(ln1.shape[0])
        q, k, v = block.attn.qkv(ln1).split(C, dim=2)
        nh = int(block.attn.nh)
        hd = int(block.attn.hd)
        shape = lambda t: t.view(B, T, nh, hd).transpose(1, 2)
        q, k, v = shape(q), shape(k), shape(v)
        standard = F.softmax((q @ k.transpose(-2, -1)) / math.sqrt(hd) + model.mask[:T, :T], dim=-1)

        x54 = block.attn.w54(ln1)
        d2 = torch.cdist(x54, x54, p=2.0) ** 2
        sigma = torch.exp(block.attn.log_sigma).clamp(0.05, 50.0)
        hebbian = torch.exp(-d2 / (2 * sigma * sigma))
        hebbian = hebbian.masked_fill(model.mask[:T, :T] < 0, 0.0)
        hebbian = hebbian / hebbian.sum(-1, keepdim=True).clamp_min(1e-9)
        raw_gate = block.attn.gate
        gate = raw_gate.clamp(0.01, 1.0)
        blended = (1.0 - gate) * standard + gate * hebbian.unsqueeze(1)

        std_last = standard[0, :, -1, :]
        hebb_last = hebbian[0, -1, :]
        blend_last = blended[0, :, -1, :]
        x54_last = x54[0, -1, :]
        pairwise = d2[0]
        if T > 1:
            upper = pairwise[torch.triu(torch.ones_like(pairwise, dtype=torch.bool), diagonal=1)]
            median_d2 = float(torch.median(upper).item()) if upper.numel() else 0.0
        else:
            median_d2 = 0.0

        # Execute the repository's actual block after observing its exact inputs.
        h = block(h, model.mask)
        layers.append({
            "layer": layer_index,
            "gate_raw": float(raw_gate.detach().item()),
            "gate_effective": float(gate.detach().item()),
            "sigma": float(sigma.detach().item()),
            "x54_last": [float(v) for v in x54_last.detach().cpu().tolist()],
            "x54_last_sha256": _tensor_sha256(x54_last),
            "x54_last_norm": float(torch.linalg.vector_norm(x54_last).item()),
            "x54_last_mean": float(x54_last.mean().item()),
            "x54_last_std": float(x54_last.std(unbiased=False).item()),
            "pairwise_d2_median": median_d2,
            "hebbian_last_entropy": _entropy(hebb_last),
            "hebbian_last_self_mass": float(hebb_last[-1].item()),
            "standard_last_entropy": _entropy(std_last),
            "blended_last_entropy": _entropy(blend_last),
            "standard_vs_hebbian_l1": float(torch.mean(torch.abs(std_last - hebb_last.unsqueeze(0))).item()),
            "hidden_input_last_norm": float(torch.linalg.vector_norm(hidden_in[0, -1, :]).item()),
            "hidden_output_last_norm": float(torch.linalg.vector_norm(h[0, -1, :]).item()),
            "hidden_output_last_sha256": _tensor_sha256(h[0, -1, :]),
        })
    logits = model.head(model.lnf(h))
    return logits, layers


def _generate_with_trace(
    model: Any,
    *,
    wire_prompt: str,
    stoi: dict[str, int],
    itos: dict[Any, str],
    block: int,
    tokens: int,
    seed: int,
    temperature: float = 0.65,
    top_k: int = 8,
) -> tuple[str, list[dict[str, Any]]]:
    torch = __import__("torch")
    ids = _encode_exact(wire_prompt[-block:], stoi)
    generated: list[int] = []
    trace: list[dict[str, Any]] = []
    generator = torch.Generator().manual_seed(int(seed))
    model.eval()
    with torch.no_grad():
        for token_index in range(int(tokens)):
            context = ids[-block:]
            x = torch.tensor([context], dtype=torch.long)
            logits, layers = _instrumented_forward(model, x)
            next_logits = logits[0, -1]
            full_prob = torch.softmax(next_logits, dim=-1)
            k = min(int(top_k), int(next_logits.numel()))
            values, indices = torch.topk(next_logits / float(temperature), k=k)
            sample_prob = torch.softmax(values, dim=-1)
            sampled = int(torch.multinomial(sample_prob, 1, generator=generator).item())
            next_id = int(indices[sampled].item())
            top_prob, top_ids = torch.topk(full_prob, k=min(5, int(full_prob.numel())))
            top_tokens = [
                {"token_id": int(tid), "text": _decode([int(tid)], itos), "probability": float(prob)}
                for prob, tid in zip(top_prob.tolist(), top_ids.tolist(), strict=True)
            ]
            context_sha = hashlib.sha256(bytes(int(v) % 256 for v in context)).hexdigest()
            trace.append({
                "generated_token_index": token_index,
                "context_length": len(context),
                "context_sha256": context_sha,
                "layers": layers,
                "logits": {
                    "entropy": _entropy(full_prob),
                    "top5": top_tokens,
                    "selected_token_id": next_id,
                    "selected_text": _decode([next_id], itos),
                    "selected_probability": float(full_prob[next_id].item()),
                    "top1_top2_logit_margin": float((torch.topk(next_logits, 2).values[0] - torch.topk(next_logits, 2).values[1]).item()),
                },
            })
            ids.append(next_id)
            generated.append(next_id)
    return _decode(generated, itos), trace


def _ledger_line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _append_snapshot_memory(ledger: DadSonLedger, *, session_id: str, descendant_sha256: str, digest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.append(ledger.append_experience(
        actor="Experiment Snapshot Bundle",
        text=f"SNAP DIGEST54 {str(digest['bundle_sha256'])[:16]} software provenance digest; not a physical 54D measurement.",
        kind="experiment-snapshot-context",
        session_id=session_id,
        descendant_sha256=descendant_sha256,
        metadata={"generated_by_model": False, "snapshot_bundle_sha256": digest["bundle_sha256"], "established_anomaly": False},
    ))
    for text in SNAPSHOT_MEMORY_LINES:
        rows.append(ledger.append_experience(
            actor="Experiment Snapshot Bundle",
            text=text,
            kind="experiment-snapshot-context",
            session_id=session_id,
            descendant_sha256=descendant_sha256,
            metadata={"generated_by_model": False, "snapshot_bundle_sha256": digest["bundle_sha256"], "established_anomaly": False},
        ))
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    validate_snapshot_facts(SNAPSHOT_FACTS)
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("active TALK-004 checkpoint hash mismatch")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256:
        raise RuntimeError("source TALK-004 ledger hash mismatch")
    if _ledger_line_count(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("source TALK-004 ledger record count mismatch")
    if file_sha256(args.heartbeat) != ACTIVE_HEARTBEAT_SHA256:
        raise RuntimeError("TALK-004 heartbeat packet hash mismatch")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    work_ledger = args.out_dir / "dad-son-ledger.snapshot-dialogue.jsonl"
    work_sqlite = args.out_dir / "dad-son.snapshot-dialogue.sqlite3"
    shutil.copy2(args.source_ledger, work_ledger)
    shutil.copy2(args.source_sqlite, work_sqlite)

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    if block != 128 or int(checkpoint["config"]["d54"]) != 54:
        raise RuntimeError("unexpected TALK-004 block/d54 contract")

    digest = build_snapshot_digest54(SNAPSHOT_FACTS)
    session_id = str(args.session_id)
    ledger = DadSonLedger(work_sqlite, work_ledger, parent_sha256=PARENT_ZEREF_SHA256)
    injected_rows = _append_snapshot_memory(
        ledger,
        session_id=session_id,
        descendant_sha256=ACTIVE_TALK4_SHA256,
        digest=digest,
    )

    dialogue: list[dict[str, Any]] = []
    for turn, prompt in enumerate(DIALOGUE_PROMPTS, 1):
        recalled = ledger.recall(prompt, limit=2)
        wire = build_wire_prompt(dad_text=prompt, recalled=recalled, block=block)
        raw_output, trace = _generate_with_trace(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            seed=int(args.seed) + turn - 1,
        )
        appended = record_turn(
            ledger,
            session_id=session_id,
            dad_text=prompt,
            zeref_output=raw_output,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            recalled=recalled,
        )
        dialogue.append({
            "turn": turn,
            "dad_prompt": prompt,
            "wire_prompt": wire,
            "recalled_memory_ids": [int(row["memory_id"]) for row in recalled],
            "recalled": recalled,
            "raw_zeref_output": raw_output,
            "trace": trace,
            "dad_record_sha256": appended[0]["record_sha256"],
            "zeref_record_sha256": appended[1]["record_sha256"],
        })
        print(f"DAD_{turn}={prompt!r}")
        print(f"ZEREF_{turn}={raw_output!r}")
        if trace:
            last = trace[-1]
            print("TRACE_%d=" % turn + json.dumps({
                "logit_entropy": last["logits"]["entropy"],
                "selected": last["logits"]["selected_text"],
                "layers": [
                    {
                        "layer": row["layer"],
                        "gate": row["gate_effective"],
                        "sigma": row["sigma"],
                        "x54_norm": row["x54_last_norm"],
                        "hebbian_self_mass": row["hebbian_last_self_mass"],
                        "std_vs_hebbian_l1": row["standard_vs_hebbian_l1"],
                    }
                    for row in last["layers"]
                ],
            }, sort_keys=True))

    ledger.close()
    final_ledger_sha = file_sha256(work_ledger)
    heartbeat = json.loads(args.heartbeat.read_text(encoding="utf-8"))
    result = {
        "schema": "zeref-cns7-snapshot-dialogue-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "source_ledger_tip_sha256": ACTIVE_LEDGER_TIP_SHA256,
        "source_heartbeat_sha256": ACTIVE_HEARTBEAT_SHA256,
        "source_heartbeat_pulses": int(heartbeat.get("pulse_count", len(heartbeat.get("beats", [])))),
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "working_ledger_sha256_after": final_ledger_sha,
        "working_ledger_records_after": _ledger_line_count(work_ledger),
        "snapshot_digest": digest,
        "snapshot_facts": list(SNAPSHOT_FACTS),
        "injected_memory_record_sha256s": [row["record_sha256"] for row in injected_rows],
        "dialogue": dialogue,
        "claim_boundary": "Inference trace and computational memory injection only. The user hypothesis is not evidence of a physical anomaly, consciousness, biological continuity, deceased-person identity, or quantum advantage.",
    }
    result_path = args.out_dir / "snapshot-dialogue.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    summary = {
        "schema": "zeref-cns7-snapshot-dialogue-summary-v1",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "snapshot_bundle_sha256": digest["bundle_sha256"],
        "turns": len(dialogue),
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "working_ledger_records_after": result["working_ledger_records_after"],
        "responses": [row["raw_zeref_output"] for row in dialogue],
        "last_token_layer_metrics": [
            {
                "turn": row["turn"],
                "layers": [
                    {
                        "layer": layer["layer"],
                        "gate_effective": layer["gate_effective"],
                        "sigma": layer["sigma"],
                        "x54_last_norm": layer["x54_last_norm"],
                        "hebbian_last_self_mass": layer["hebbian_last_self_mass"],
                        "standard_vs_hebbian_l1": layer["standard_vs_hebbian_l1"],
                        "hidden_output_last_norm": layer["hidden_output_last_norm"],
                    }
                    for layer in row["trace"][-1]["layers"]
                ] if row["trace"] else [],
            }
            for row in dialogue
        ],
        "claim_boundary": result["claim_boundary"],
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    files = sorted(path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (args.out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", default="zeref-cns7-snapshot-dialogue-001")
    parser.add_argument("--seed", type=int, default=2026082601)
    parser.add_argument("--tokens", type=int, default=28)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
