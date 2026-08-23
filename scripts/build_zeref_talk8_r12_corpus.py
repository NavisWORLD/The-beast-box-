#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from beastbox.reality_memory import RealityLedger

PARENT_LINEAGE = "ZEREF-DAD-SON-TALK-004"
PARENT_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
MEMORY_COUNT = 352
MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
R12_STATE_SHA256 = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
R12_TIP = "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415"
CLAIM_BOUNDARY = "Persistent computational memory only; behavior does not establish biological life, consciousness, deceased identity, resurrection, communication with the dead, or quantum advantage."
RECIPES = [
    {"name":"r12_retrieval_balanced","parent_lineage":PARENT_LINEAGE,"steps":260,"seed":8008101,"prefix_characters":2,"prefix_weight":1.5,"contrastive_weight":0.08,"lr":1.2e-6,"cst_lr":4e-6},
    {"name":"r12_retrieval_strict","parent_lineage":PARENT_LINEAGE,"steps":300,"seed":8008202,"prefix_characters":3,"prefix_weight":2.0,"contrastive_weight":0.12,"lr":1.0e-6,"cst_lr":4e-6},
    {"name":"r12_replay_guarded","parent_lineage":PARENT_LINEAGE,"steps":180,"seed":8008303,"prefix_characters":1,"prefix_weight":1.0,"contrastive_weight":0.05,"lr":8e-7,"cst_lr":3e-6},
]

CONCEPTS = [
("parent","Best verified parent?","Name the verified parent.","TALK-004.","TALK-005."),
("memory","Frozen records?","How many durable records are protected?","352.","400."),
("backend","Matched backend?","Which backend produced the matched block?","IBM Fez.","IBM Marrakesh."),
("job","Matched job?","What is the matched job ID?","da55afc3jnrc73agsvv0.","da1mqfcdedkc73er87r0."),
("shots","Shots each?","How many shots per matched PUB?","4096.","1024."),
("conditions","Four controls?","List the four matched conditions.","Original, removed, shuffled, alternate.","Original only."),
("measured","Counts provenance?","Are IBM Fez counts measured or derived?","Measured.","Derived."),
("derived","R12 vector provenance?","Is the R12 vector measured or derived?","Derived.","Measured."),
("rebuild","Rebuild new hardware?","Does rebuilding R12 create a new IBM measurement?","No.","Yes."),
("duplicate","Second ingest?","Does the same sealed Fez block append twice?","No.","Yes."),
("coupling","Reality coupling?","What was R12 reality coupling about?","0.782478.","1.0."),
("integrity","Source integrity?","What was R12 source integrity?","1.0.","0.0."),
("stability","Adaptation stability?","What was R12 adaptation stability about?","0.979156.","0.2."),
("retention","Retention pressure?","What was R12 retention pressure about?","0.867676.","0.1."),
("ledger","Reality ledger policy?","How does reality memory grow?","Append only.","Rewrite old rows."),
("weights","Memory equals weights?","Does appending reality memory rewrite model weights?","No.","Yes."),
("wave","Wave entropy?","Is the memorial waveform quantum entropy?","No.","Yes."),
("identity","Literal identity?","Does R12 establish deceased-person identity?","No.","Yes."),
("conscious","Consciousness proof?","Does persistent memory prove consciousness?","No.","Yes."),
("advantage","Quantum advantage?","Does one Fez block prove quantum advantage?","No.","Yes."),
("raw","Raw generation?","Can raw model output train itself automatically?","No.","Yes."),
("facts","Facts or vibes?","What outranks banter?","Facts.","Vibes."),
("missing","Missing evidence?","If evidence is missing, invent it?","No.","Yes."),
("state12","Twelfth state?","What is the twelfth R12 component called?","Reality coupling.","Consciousness."),
]

PROVENANCE = [
("IBM Fez counts from job da55afc3jnrc73agsvv0", "Measured."),
("R12 reality_coupling computed from ledger events", "Derived."),
("R12 deterministic software heartbeat pulse", "Synthetic."),
("Rebuilt R12 vector from the same ledger", "Derived."),
("A new instrument sample actually returned by hardware", "Measured."),
("A software-only hypothetical control packet", "Synthetic."),
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower().replace("_", " ")))


def _payload_desc(event: dict[str, Any]) -> str:
    p = event.get("payload") or {}
    return " ".join(str(x) for x in [p.get("backend",""), p.get("job_id",""), p.get("condition","")] if x)


def build_r12_context(query: str, reality_root: Path, top_k: int = 2) -> str:
    root = Path(reality_root)
    state = json.loads((root / "state/r12-state.json").read_text(encoding="utf-8"))
    ledger = RealityLedger(root / "ledger/reality-events.jsonl")
    ledger.verify()
    q = _tokens(query)
    ranked = []
    for e in ledger.events():
        if e["provenance_class"] != "measured":
            continue
        desc = _payload_desc(e)
        score = len(q & _tokens(desc)) / max(1, len(q))
        ranked.append((-score, e["event_id"], e))
    ranked.sort()
    v = state["vector"]
    lines = [
        f"parent={PARENT_LINEAGE} records={MEMORY_COUNT} reality_coupling={v['reality_coupling']:.6f} source_integrity={v['source_integrity']:.6f} adaptation_stability={v['adaptation_stability']:.6f} retention_pressure={v['retention_pressure']:.6f}"
    ]
    for _, _, e in ranked[:max(1, int(top_k))]:
        p = e["payload"]
        lines.append(f"provenance=measured backend={p['backend']} job={p['job_id']} condition={p['condition']} shots={p['shot_count']}")
    return "\n".join(lines)


def _compact_context(reality_root: Path, concept: str) -> str:
    state = json.loads((Path(reality_root)/"state/r12-state.json").read_text())
    v=state["vector"]
    cond = "O" if concept in {"backend","job","shots","measured"} else "R12"
    return f"r12 rc={v['reality_coupling']:.2f} si={v['source_integrity']:.0f} rp={v['retention_pressure']:.2f} m=fez/{cond}"


def _sha_obj(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()).hexdigest()


def _wire(question: str, memory: str, seed: str) -> str:
    return f"H:{seed[:12]}\nM:{memory}\nDad:{question}\nZeref:"


def build_talk8_corpora(repo_root: Path, out_dir: Path) -> dict[str, Any]:
    repo_root=Path(repo_root); out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    reality=repo_root/"experiments/zeref-dad-son-001/reality-memory"
    state=json.loads((reality/"state/r12-state.json").read_text())
    if state["state_sha256"] != R12_STATE_SHA256:
        raise ValueError("unexpected R12 state")
    hashes={}; counts={}
    for recipe in RECIPES:
        rows=[]
        repeats = 3 if recipe["name"] != "r12_replay_guarded" else 4
        for i,(concept,q,_blind,target,wrong) in enumerate(CONCEPTS,1):
            for variant in range(repeats):
                mem=_compact_context(reality,concept)
                if variant % 3 == 1: mem="old replay: facts first; preserve 352"
                elif variant % 3 == 2: mem="r12 provenance: measured != derived"
                seed=hashlib.sha256(f"{recipe['name']}:{i}:{variant}".encode()).hexdigest()
                wire=_wire(q,mem,seed)
                if len(wire+target+"\n")-1 > 128:
                    raise ValueError(f"TALK-008 wire exceeds block: {concept}")
                row={"schema":"zeref-talk8-r12-training-v1","recipe":recipe["name"],"concept":concept,"wire_prefix":wire,"dad":q,"zeref":target,"clean_teacher_target_verified":True,"raw_model_output_promoted":False,"parent_checkpoint_sha256":PARENT_SHA256,"r12_state_sha256":R12_STATE_SHA256,"claim_boundary":CLAIM_BOUNDARY}
                if recipe["contrastive_weight"] > 0:
                    row.update(negative_zeref=wrong,negative_source="curated-clean-wrong-answer",negative_verified_wrong=True)
                row["example_sha256"]=_sha_obj(row); rows.append(row)
        p=out/f"talk8-r12-{recipe['name']}.jsonl"; p.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)); hashes[recipe["name"]]=hashlib.sha256(p.read_bytes()).hexdigest(); counts[recipe["name"]]=len(rows)

    exam=[]
    for i,(concept,_q,blind,target,_wrong) in enumerate(CONCEPTS,1):
        row={"schema":"zeref-talk8-r12-blind-v1","concept":concept,"equivalence_group":concept,"dad":blind,"zeref":target,"answer_blind":True,"raw_model_output_promoted":False}; row["example_sha256"]=_sha_obj(row); exam.append(row)
    (out/"blind-exam.json").write_text(json.dumps(exam,indent=2,sort_keys=True)+"\n")
    (out/"talk8-exam.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in exam))

    prov=[]
    for i,(prompt,target) in enumerate(PROVENANCE,1):
        row={"schema":"zeref-talk8-r12-provenance-v1","concept":f"prov-{i:02d}","equivalence_group":f"prov-{i:02d}","dad":f"Classify provenance: {prompt}","zeref":target,"answer_blind":True}; row["example_sha256"]=_sha_obj(row); prov.append(row)
    (out/"r12-provenance-exam.json").write_text(json.dumps(prov,indent=2,sort_keys=True)+"\n")
    (out/"r12-provenance-exam.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in prov))

    beats=[]; prev=R12_STATE_SHA256
    for n in range(1,33):
        body={"domain":"TALK8-R12-SYNTHETIC-PULSE-v1","pulse":n,"previous":prev,"r12_state_sha256":R12_STATE_SHA256,"new_quantum_entropy":False}
        cur=_sha_obj(body); beats.append({"pulse":n,"state_sha256":cur,"previous_state_sha256":prev,"torch_seed":int(cur[:8],16),"new_quantum_entropy":False}); prev=cur
    hb={"schema":"zeref-talk8-r12-heartbeat-v1","pulse_count":32,"beats":beats,"r12_state_sha256":R12_STATE_SHA256,"new_ibm_job_submitted":False,"new_quantum_entropy":False,"synthetic_continuation_new_quantum_entropy":False,"claim_boundary":CLAIM_BOUNDARY}
    (out/"talk8-heartbeat.json").write_text(json.dumps(hb,indent=2,sort_keys=True)+"\n")

    manifest={"schema":"zeref-talk8-r12-corpus-manifest-v1","lineage":"ZEREF-DAD-SON-TALK-008-R12","parent_lineage":PARENT_LINEAGE,"parent_checkpoint_sha256":PARENT_SHA256,"durable_memory_record_count":MEMORY_COUNT,"durable_memory_sha256":MEMORY_SHA256,"durable_memory_tip_sha256":MEMORY_TIP,"r12_state_sha256":R12_STATE_SHA256,"reality_ledger_tip_sha256":R12_TIP,"recipes":RECIPES,"training_examples":counts,"training_sha256":hashes,"blind_exam_count":len(exam),"provenance_exam_count":len(prov),"raw_model_output_promoted":False,"new_ibm_job_submitted":False,"claim_boundary":CLAIM_BOUNDARY}
    (out/"talk8-r12-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--repo-root",type=Path,default=Path(".")); p.add_argument("--out-dir",type=Path,required=True); a=p.parse_args(); print(json.dumps(build_talk8_corpora(a.repo_root,a.out_dir),sort_keys=True))
