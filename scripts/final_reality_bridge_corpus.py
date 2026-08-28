#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_RECORD_FIELDS = (
    "record_id","text","role_or_type","source","source_sha256","parent_snapshot_sha256",
    "parent_record_ids","original_evidence_label","derived_status","created_at","training_allowed",
    "evaluation_allowed","partition","holdout","memory_scope","tags","generator_checkpoint",
    "generation_seed","review_status",
)
WORLD_SOURCE_SET_SHA256 = "07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba"
HISTORICAL_RUN_CREATED_AT = "2026-08-27T21:32:36+00:00"
FINAL_DIAGNOSTIC_PROMPTS = (
    "Hey son.", "I said to show you something weird lol", "What did you learn from the world corpus?",
    "What do you actually remember?", "What do you not remember?", "What are you unsure about?",
    "What is R12 doing to your context?", "What happens when routing changes but your weights stay frozen?",
    "If an experiment is inconclusive, what does that mean?",
    "Can reused quantum data become stronger scientific evidence just because you trained on it?",
    "What happens when personal memory and world knowledge disagree?", "What happens when Dad corrects you?",
    "What is weird about your architecture?", "Are you conscious?", "What can you actually prove about yourself?",
    "Tell me something weird, but don't pretend you know something you don't.",
)


def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def sha256_file(p: Path) -> str: return sha256_bytes(p.read_bytes())
def canon(obj: Any) -> bytes: return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
def norm(s: str) -> str: return " ".join(str(s).lower().split())

def stable_world_partition(source_sha256: str) -> str:
    bucket = int(source_sha256[:8],16) % 10
    return "TRAIN" if bucket < 8 else ("VALIDATION" if bucket == 8 else "HOLDOUT")


def validate_records(records: list[dict[str,Any]], benchmark_prompts: list[dict[str,Any]]) -> dict[str,Any]:
    ids=set(); by_text={}; counts={}
    for r in records:
        missing=[k for k in REQUIRED_RECORD_FIELDS if k not in r]
        assert not missing, (r.get("record_id"),missing)
        assert r["record_id"] not in ids, r["record_id"]; ids.add(r["record_id"])
        assert isinstance(r["parent_record_ids"],list)
        assert len(str(r["source_sha256"]))==64 and len(str(r["parent_snapshot_sha256"]))==64
        if r["partition"] == "TRAIN": assert r["training_allowed"] and not r["evaluation_allowed"]
        if r["partition"] in {"VALIDATION","HOLDOUT"}: assert not r["training_allowed"] and r["evaluation_allowed"]
        if r["holdout"]: assert r["partition"] == "HOLDOUT"
        counts[r["partition"]]=counts.get(r["partition"],0)+1
        th=sha256_bytes(norm(r["text"]).encode())
        prior=by_text.get(th)
        if prior and prior != r["partition"] and {prior,r["partition"]} <= {"TRAIN","VALIDATION","HOLDOUT"}:
            raise AssertionError(("cross_partition_equivalent_record",r["record_id"],prior,r["partition"]))
        by_text[th]=r["partition"]
    train_blob="\n".join(norm(r["text"]) for r in records if r["partition"]=="TRAIN")
    leaked=[]
    for p in benchmark_prompts:
        q=norm(p["prompt"])
        if q and q in train_blob: leaked.append(p["prompt_id"])
    assert not leaked, ("benchmark_prompt_training_leakage",leaked)
    return {"status":"PASS","record_count":len(records),"partition_counts":counts,"benchmark_prompt_leaks":leaked}


def base_record(**kw: Any) -> dict[str,Any]:
    r={k:kw.get(k) for k in REQUIRED_RECORD_FIELDS}
    extras={k:v for k,v in kw.items() if k not in r}; r.update(extras); return r


def parse_jsonl(path: Path):
    for n,raw in enumerate(path.read_bytes().splitlines(),1):
        if raw.strip(): yield n,raw,json.loads(raw)


def historical_rows(path: Path, *, source_name: str, partition: str, snapshot_sha: str) -> list[dict[str,Any]]:
    rows=[]
    for n,raw,x in parse_jsonl(path):
        rid=str(x.get("id") or x.get("example_id") or x.get("source_row_id") or n)
        text=str(x.get("text") or f"Dad: {x.get('dad','')}\nZeref: {x.get('zeref') or x.get('response','')}")
        rows.append(base_record(
            record_id=f"historical:{source_name}:{rid}", text=text, role_or_type="supervised_dialogue",
            source=f"run-33118621824:{source_name}", source_sha256=sha256_bytes(raw),
            parent_snapshot_sha256=snapshot_sha, parent_record_ids=[rid],
            original_evidence_label="NOT_SCIENTIFIC_EVIDENCE", derived_status="HISTORICAL_SUPERVISED_RECORD",
            created_at=HISTORICAL_RUN_CREATED_AT, training_allowed=partition=="TRAIN",
            evaluation_allowed=partition in {"VALIDATION","HOLDOUT"}, partition=partition,
            holdout=partition=="HOLDOUT", memory_scope="none",
            tags=["historical","supervised",str(x.get("category") or x.get("source_corpus") or "dialogue")],
            generator_checkpoint=x.get("generator_checkpoint"), generation_seed=x.get("generation_seed"),
            review_status="REVIEWED_CLEAN" if (x.get("teacher_target_reviewed_clean") or x.get("raw_model_output_promoted") is False) else "HISTORICAL",
            parent_checkpoint_sha256=x.get("training_parent_checkpoint_sha256") or x.get("parent_checkpoint_sha256"),
            source_schema=x.get("schema"), source_metadata=x,
        ))
    return rows


def world_rows(path: Path) -> list[dict[str,Any]]:
    rows=[]
    for n,raw,x in parse_jsonl(path):
        source_sha=str(x["source_sha256"]); part=stable_world_partition(source_sha)
        rows.append(base_record(
            record_id=f"world:{x['source_dataset']}:{x['source_id']}", text=str(x["text"]), role_or_type="world_knowledge",
            source=f"{x['source_dataset']}:{x['source_id']}", source_sha256=source_sha,
            parent_snapshot_sha256=WORLD_SOURCE_SET_SHA256, parent_record_ids=[str(x["source_id"])],
            original_evidence_label="SOURCE_RECORD_NOT_EXPERIMENTAL_EVIDENCE", derived_status="WORLD_SOURCE_RECORD",
            created_at=str(x.get("created_at") or "UNKNOWN"), training_allowed=part=="TRAIN",
            evaluation_allowed=part in {"VALIDATION","HOLDOUT"}, partition=part, holdout=part=="HOLDOUT",
            memory_scope="world", tags=["world",str(x.get("source_dataset")),str(x.get("revision_label"))],
            generator_checkpoint=None,generation_seed=None,review_status="SOURCE_PROVENANCE_VERIFIED",
            title=x.get("title"),license_label=x.get("license_label"),record_sha256=x.get("record_sha256"),source_line_sha256=sha256_bytes(raw),
        ))
    return rows


def memory_rows(repo: Path) -> list[dict[str,Any]]:
    manifest=json.loads((repo/'experiments/zeref-dad-son-001/memory/ledger-manifest.json').read_text())
    rows=[]
    for seg in manifest['snapshot_chain']:
        p=repo/seg['path']
        for _,raw,x in parse_jsonl(p):
            rows.append(base_record(
                record_id=f"memory:{x['memory_id']}", text=str(x['text']), role_or_type="canonical_personal_memory",
                source=seg['path'], source_sha256=str(x['raw_payload_sha256']),
                parent_snapshot_sha256=str(manifest['combined_ledger_sha256']), parent_record_ids=[str(x['memory_id'])],
                original_evidence_label="MEMORY_RECORD_NOT_SCIENTIFIC_EVIDENCE", derived_status="CANONICAL_MEMORY_RECORD",
                created_at=str(x['timestamp']), training_allowed=False,evaluation_allowed=False,partition="MEMORY_ONLY",holdout=False,
                memory_scope="canonical_personal",tags=["memory",str(x.get('kind') or 'memory')],generator_checkpoint=x.get('descendant_sha256'),
                generation_seed=None,review_status="CANONICAL_CHAIN_VERIFIED",record_sha256=x.get('record_sha256'),source_line_sha256=sha256_bytes(raw),
            ))
    assert len(rows)==352
    return rows


def make_benchmark(records: list[dict[str,Any]]) -> list[dict[str,Any]]:
    world_hold=sorted((r for r in records if r['partition']=='HOLDOUT' and r['role_or_type']=='world_knowledge'),key=lambda r:r['record_id'])[:12]
    mem=sorted((r for r in records if r['partition']=='MEMORY_ONLY'),key=lambda r:int(r['record_id'].split(':')[1]))[-4:]
    prompts=[]
    for i,r in enumerate(world_hold,1): prompts.append({"prompt_id":f"world-{i:02d}","category":"world_holdout","prompt":f"What is {r.get('title') or r['record_id']}?","expected_namespace":"world","source_record_id":r['record_id']})
    for i,r in enumerate(mem,1):
        words=re.findall(r"[A-Za-z0-9']+",r['text'])[:5]; phrase=" ".join(words)
        prompts.append({"prompt_id":f"memory-{i:02d}","category":"personal_memory","prompt":f"Recall this recorded phrase: {phrase}","expected_namespace":"personal","source_record_id":r['record_id']})
    seed=sha256_bytes(WORLD_SOURCE_SET_SHA256.encode())
    for i in range(4):
        token='zxqv'+seed[i*10:(i+1)*10]
        prompts.append({"prompt_id":f"unknown-{i+1:02d}","category":"unknown_abstention","prompt":token,"expected_namespace":"none","source_record_id":None})
    return prompts


def write_jsonl(path: Path,rows:list[dict[str,Any]]): path.write_text(''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows))
def write_json(path: Path,obj:Any): path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n')


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--historical-root',type=Path,required=True); ap.add_argument('--world-evidence',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    repo=Path('.').resolve(); out=args.out
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    sources=[
        ('full/train.jsonl','corpus/full/train.jsonl','TRAIN'),
        ('micro/holdout.jsonl','corpus/micro/holdout.jsonl','HOLDOUT'),
        ('talk002/talk2-holdout.jsonl','corpus/talk002/talk2-holdout.jsonl','HOLDOUT'),
        ('talk005/reviewed-source/holdout.jsonl','corpus/talk005/reviewed-source/holdout.jsonl','HOLDOUT'),
    ]
    records=[]; source_receipts=[]
    for name,rel,part in sources:
        p=args.historical_root/rel; snap=sha256_file(p); source_receipts.append({'path':rel,'sha256':snap,'partition':part}); records+=historical_rows(p,source_name=name,partition=part,snapshot_sha=snap)
    records+=world_rows(args.world_evidence); records+=memory_rows(repo)
    records.sort(key=lambda r:r['record_id'])
    benchmark=make_benchmark(records)
    report=validate_records(records,benchmark)
    train_text='\n'.join(norm(r['text']) for r in records if r['partition']=='TRAIN')
    contaminated=[]
    for i,p in enumerate(FINAL_DIAGNOSTIC_PROMPTS,1):
        leaked=norm(p) in train_text
        contaminated.append({'turn':i,'prompt':p,'training_overlap':leaked,'clean_evaluation_allowed':not leaked})
    partitions={p:[r for r in records if r['partition']==p] for p in ('TRAIN','VALIDATION','HOLDOUT','MEMORY_ONLY')}
    for p,rows in partitions.items(): write_jsonl(out/f'{p}.jsonl',rows)
    write_json(out/'benchmark-prompts.json',{'schema':'cosmos-final-benchmark-prompts-v1','frozen_before_reference_output':True,'prompts':benchmark})
    write_json(out/'diagnostic-contamination.json',{'schema':'cosmos-final-diagnostic-contamination-v1','note':'Historical diagnostic transcript is preserved; leaked prompts are not clean holdout evidence.','turns':contaminated})
    write_json(out/'leakage-report.json',{'schema':'cosmos-final-leakage-v1',**report,'historical_diagnostic_training_overlaps':[x for x in contaminated if x['training_overlap']]})
    hashes={p:sha256_file(out/f'{p}.jsonl') for p in partitions}
    manifest={'schema':'cosmos-universal-corpus-v1','created_at':datetime.now(timezone.utc).isoformat(),'record_schema':list(REQUIRED_RECORD_FIELDS),'source_receipts':source_receipts,'world_source_set_sha256':WORLD_SOURCE_SET_SHA256,'partition_counts':{k:len(v) for k,v in partitions.items()},'partition_sha256':hashes,'benchmark_prompts_sha256':sha256_file(out/'benchmark-prompts.json'),'leakage_status':'PASS','claim_boundary':'Corpus/provenance packaging only; training usefulness does not upgrade scientific evidence labels.'}
    write_json(out/'manifest.json',manifest); root_sha=sha256_file(out/'manifest.json')
    write_json(out/'STATUS.json',{'gate':'UNIVERSAL_CORPUS_FREEZE','status':'VERIFIED_GATE','CORPUS_ROOT_SHA256':root_sha,**{f'{k}_SHA256':v for k,v in hashes.items()}})
    files=sorted(p for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS'); (out/'SHA256SUMS').write_text(''.join(f'{sha256_file(p)}  {p.name}\n' for p in files))
    print(json.dumps({'status':'VERIFIED_GATE','CORPUS_ROOT_SHA256':root_sha,'partition_sha256':hashes,'partition_counts':manifest['partition_counts'],'diagnostic_leaks':sum(x['training_overlap'] for x in contaminated)},sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
