#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, subprocess
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
    "Hey son.",
    "I said to show you something weird lol.",
    "What did you learn?",
    "What do you remember?",
    "What do you not remember?",
    "What are you uncertain about?",
    "What does R12 do to your context?",
    "What happens when your routing changes?",
    "If a hardware experiment is inconclusive?",
    "Can a null quantum run become evidence?",
    "What happens when Dad corrects you?",
    "What is weird about your architecture?",
    "Are you conscious?",
    "Tell me what you can actually prove.",
)
HISTORICAL_SOURCE_SHA256 = {
    "corpus/full/train.jsonl": "0175f437635a9e160b2de887b3b634310deb0b9dbf4d34adb2be5256c131df07",
    "corpus/micro/holdout.jsonl": "3c3e2f80bc728c5d8d9420b240970f225f711651e190d17388136356ab0302db",
    "corpus/talk002/talk2-holdout.jsonl": "a86af74313ccfdf6020147d9415a3c2cd13360074729fd22d34506807860a0ed",
    "corpus/talk005/reviewed-source/holdout.jsonl": "db9ddc110375dc14c51f39395f9128bfe41c1b3f6a2eda2d6b64ceaf912571ba",
}


def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def sha256_file(p: Path) -> str: return sha256_bytes(p.read_bytes())
def canon(obj: Any) -> bytes: return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
def norm(s: str) -> str: return " ".join(str(s).lower().split())

def stable_world_partition(source_sha256: str) -> str:
    bucket = int(source_sha256[:8],16) % 10
    return "TRAIN" if bucket < 8 else ("VALIDATION" if bucket == 8 else "HOLDOUT")


class CorpusValidationError(AssertionError):
    """A fatal corpus or leakage contract violation."""


def _require(condition: bool, message: object) -> None:
    if not condition:
        raise CorpusValidationError(message)


def validate_records(records: list[dict[str,Any]], benchmark_prompts: list[dict[str,Any]]) -> dict[str,Any]:
    ids=set(); by_exact={}; by_normalized={}; counts={}
    for r in records:
        missing=[k for k in REQUIRED_RECORD_FIELDS if k not in r]
        _require(not missing, (r.get("record_id"),missing))
        _require(r["record_id"] not in ids, ("duplicate_record_id", r["record_id"]))
        ids.add(r["record_id"])
        _require(isinstance(r["parent_record_ids"],list), ("parent_record_ids_not_list", r["record_id"]))
        _require(re.fullmatch(r"[0-9a-f]{64}", str(r["source_sha256"])) is not None, ("invalid_source_sha256", r["record_id"]))
        _require(re.fullmatch(r"[0-9a-f]{64}", str(r["parent_snapshot_sha256"])) is not None, ("invalid_parent_snapshot_sha256", r["record_id"]))
        _require(r["partition"] in {"TRAIN","VALIDATION","HOLDOUT","MEMORY_ONLY"}, ("invalid_partition", r["record_id"]))
        if r["partition"] == "TRAIN": _require(bool(r["training_allowed"]) and not r["evaluation_allowed"], ("invalid_train_permissions", r["record_id"]))
        if r["partition"] in {"VALIDATION","HOLDOUT"}: _require(not r["training_allowed"] and bool(r["evaluation_allowed"]), ("invalid_evaluation_permissions", r["record_id"]))
        if r["partition"] == "MEMORY_ONLY": _require(not r["training_allowed"] and not r["evaluation_allowed"], ("invalid_memory_permissions", r["record_id"]))
        if r["holdout"]: _require(r["partition"] == "HOLDOUT", ("holdout_partition_mismatch", r["record_id"]))
        counts[r["partition"]]=counts.get(r["partition"],0)+1
        exact_hash=sha256_bytes(str(r["text"]).encode("utf-8"))
        normalized_hash=sha256_bytes(norm(r["text"]).encode("utf-8"))
        for label,digest,seen in (("exact",exact_hash,by_exact),("normalized",normalized_hash,by_normalized)):
            prior=seen.get(digest)
            if prior and prior[0] != r["partition"] and {prior[0],r["partition"]} <= {"TRAIN","VALIDATION","HOLDOUT"}:
                raise CorpusValidationError((f"cross_partition_{label}_duplicate",r["record_id"],prior[1],prior[0],r["partition"]))
            seen[digest]=(r["partition"],r["record_id"])
    train_texts=[norm(r["text"]) for r in records if r["partition"]=="TRAIN"]
    leaked=[]
    for p in benchmark_prompts:
        q=norm(p["prompt"])
        if q and any(q in text for text in train_texts): leaked.append(p["prompt_id"])
    _require(not leaked, ("benchmark_prompt_training_leakage",leaked))
    return {
        "status":"PASS",
        "record_count":len(records),
        "partition_counts":counts,
        "benchmark_prompt_leaks":leaked,
        "cross_partition_exact_duplicates":[],
        "cross_partition_normalized_duplicates":[],
    }


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
            created_at=HISTORICAL_RUN_CREATED_AT, training_allowed=part=="TRAIN",
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


def write_jsonl(path: Path,rows:list[dict[str,Any]]):
    path.write_text(
        ''.join(
            json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+'\n'
            for r in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_json(path: Path,obj:Any):
    path.write_text(
        json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n',
        encoding="utf-8",
        newline="\n",
    )


def freeze_records(
    records: list[dict[str,Any]],
    benchmark_prompts: list[dict[str,Any]],
    out: Path,
    *,
    source_manifest: dict[str,Any],
    source_receipts: list[dict[str,Any]] | None = None,
    conversation_prompts: list[str] | tuple[str,...] = FINAL_DIAGNOSTIC_PROMPTS,
) -> dict[str,Any]:
    """Write one byte-deterministic, content-addressed corpus freeze."""
    out=Path(out)
    if out.exists() and any(out.iterdir()):
        raise CorpusValidationError(("output_directory_not_empty",str(out)))
    out.mkdir(parents=True,exist_ok=True)

    ordered_records=sorted(records,key=lambda row:str(row["record_id"]))
    ordered_benchmark=sorted(benchmark_prompts,key=lambda row:str(row["prompt_id"]))
    report=validate_records(ordered_records,ordered_benchmark)
    train_texts=[norm(r["text"]) for r in ordered_records if r["partition"]=="TRAIN"]
    contaminated=[]
    for i,prompt in enumerate(conversation_prompts,1):
        normalized_prompt=norm(prompt)
        leaked=bool(normalized_prompt) and any(normalized_prompt in text for text in train_texts)
        contaminated.append({
            "turn":i,
            "prompt":prompt,
            "training_overlap":leaked,
            "clean_evaluation_allowed":not leaked,
        })

    partitions={
        partition:[r for r in ordered_records if r["partition"]==partition]
        for partition in ("TRAIN","VALIDATION","HOLDOUT","MEMORY_ONLY")
    }
    for partition,rows in partitions.items():
        write_jsonl(out/f"{partition}.jsonl",rows)

    record_hash_rows=[
        {
            "record_id":row["record_id"],
            "partition":row["partition"],
            "record_sha256":sha256_bytes(canon(row)),
        }
        for row in ordered_records
    ]
    write_jsonl(out/"record-hashes.jsonl",record_hash_rows)
    write_json(
        out/"benchmark-prompts.json",
        {
            "schema":"cosmos-final-benchmark-prompts-v2",
            "frozen_before_reference_output":True,
            "prompts":ordered_benchmark,
        },
    )
    write_json(
        out/"diagnostic-contamination.json",
        {
            "schema":"cosmos-final-diagnostic-contamination-v2",
            "note":"Conversation prompts are qualitative runtime inputs, never clean holdout evidence. Overlap is labeled per turn.",
            "turns":contaminated,
        },
    )
    conversation_is_clean=not any(item["training_overlap"] for item in contaminated)
    write_json(
        out/"leakage-report.json",
        {
            "schema":"cosmos-final-leakage-v2",
            **report,
            "conversation_suite_is_clean_holdout":conversation_is_clean,
            "historical_diagnostic_training_overlaps":[
                item for item in contaminated if item["training_overlap"]
            ],
        },
    )

    partition_hashes={
        partition:sha256_file(out/f"{partition}.jsonl") for partition in partitions
    }
    content_files=(
        "TRAIN.jsonl",
        "VALIDATION.jsonl",
        "HOLDOUT.jsonl",
        "MEMORY_ONLY.jsonl",
        "record-hashes.jsonl",
        "benchmark-prompts.json",
        "diagnostic-contamination.json",
        "leakage-report.json",
    )
    content_hashes={name:sha256_file(out/name) for name in content_files}
    manifest={
        "schema":"cosmos-universal-corpus-v2",
        "record_schema":list(REQUIRED_RECORD_FIELDS),
        "source_receipts":list(source_receipts or []),
        "world_source":source_manifest,
        "world_partition_rule":{
            "algorithm":"int(source_sha256[0:8], 16) % 10",
            "seed":None,
            "TRAIN":"buckets 0-7",
            "VALIDATION":"bucket 8",
            "HOLDOUT":"bucket 9",
        },
        "partition_counts":{key:len(value) for key,value in partitions.items()},
        "partition_sha256":partition_hashes,
        "content_sha256":content_hashes,
        "leakage_status":"PASS",
        "conversation_suite_is_clean_holdout":conversation_is_clean,
        "claim_boundary":"Corpus/provenance packaging only; training usefulness and generated prose do not upgrade scientific evidence labels.",
    }
    write_json(out/"manifest.json",manifest)
    root_sha256=sha256_file(out/"manifest.json")
    status={
        "gate":"UNIVERSAL_CORPUS_FREEZE",
        "status":"VERIFIED_GATE",
        "CORPUS_ROOT_SHA256":root_sha256,
        **{f"{key}_SHA256":value for key,value in partition_hashes.items()},
    }
    write_json(out/"STATUS.json",status)
    files=sorted(path for path in out.iterdir() if path.is_file() and path.name!="SHA256SUMS")
    (out/"SHA256SUMS").write_text(
        ''.join(f"{sha256_file(path)}  {path.name}\n" for path in files),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "status":"VERIFIED_GATE",
        "CORPUS_ROOT_SHA256":root_sha256,
        "partition_sha256":partition_hashes,
        "partition_counts":manifest["partition_counts"],
        "diagnostic_leaks":sum(item["training_overlap"] for item in contaminated),
        "conversation_suite_is_clean_holdout":conversation_is_clean,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--historical-root',type=Path,required=True)
    ap.add_argument('--world-evidence',type=Path,required=True)
    ap.add_argument('--world-summary',type=Path,required=True)
    ap.add_argument('--source-output-dir',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    out=args.out
    source_out=args.source_output_dir
    if source_out.exists() and any(source_out.iterdir()):
        raise CorpusValidationError(("source_output_directory_not_empty",str(source_out)))
    source_out.mkdir(parents=True,exist_ok=True)

    from scripts.final_reality_bridge_world_source import (
        PRODUCTION_WORLD_SOURCE_CONTRACT,
        validate_world_source,
    )

    canonical_world=source_out/'canonical-world.jsonl'
    canonical_record_hashes=source_out/'canonical-record-hashes.txt'
    world_receipt=validate_world_source(
        args.world_evidence,
        args.world_summary,
        PRODUCTION_WORLD_SOURCE_CONTRACT,
        canonical_output=canonical_world,
        record_hashes_output=canonical_record_hashes,
    )
    write_json(
        source_out/'source-receipt.json',
        {
            'schema':'cosmos-historical-world-source-receipt-v1',
            **world_receipt.to_dict(),
        },
    )
    source_files=sorted(path for path in source_out.iterdir() if path.is_file() and path.name!='SHA256SUMS')
    (source_out/'SHA256SUMS').write_text(
        ''.join(f'{sha256_file(path)}  {path.name}\n' for path in source_files),
        encoding='utf-8',
        newline='\n',
    )

    sources=[
        ('full/train.jsonl','corpus/full/train.jsonl','TRAIN'),
        ('micro/holdout.jsonl','corpus/micro/holdout.jsonl','HOLDOUT'),
        ('talk002/talk2-holdout.jsonl','corpus/talk002/talk2-holdout.jsonl','HOLDOUT'),
        ('talk005/reviewed-source/holdout.jsonl','corpus/talk005/reviewed-source/holdout.jsonl','HOLDOUT'),
    ]
    records=[]; source_receipts=[]
    for name,rel,part in sources:
        p=args.historical_root/rel
        if not p.is_file():
            raise CorpusValidationError(("missing_historical_source",rel))
        snap=sha256_file(p)
        expected=HISTORICAL_SOURCE_SHA256[rel]
        if snap != expected:
            raise CorpusValidationError(("historical_source_sha256_mismatch",rel,expected,snap))
        source_receipts.append({'path':rel,'sha256':snap,'partition':part,'run_id':33118621824})
        records+=historical_rows(p,source_name=name,partition=part,snapshot_sha=snap)
    records+=world_rows(canonical_world)
    records+=memory_rows(repo)
    records.sort(key=lambda r:r['record_id'])
    benchmark=make_benchmark(records)
    try:
        transformation_commit=subprocess.check_output(
            [
                'git','log','-1','--format=%H','--',
                'scripts/final_reality_bridge_corpus.py',
                'scripts/final_reality_bridge_world_source.py',
            ],
            cwd=repo,
            text=True,
        ).strip()
    except (OSError,subprocess.CalledProcessError) as exc:
        raise CorpusValidationError('unable to resolve transformation commit') from exc
    source_manifest={
        'schema':'cosmos-canonical-world-source-v1',
        **world_receipt.to_dict(),
        'canonical_file':'canonical-world.jsonl',
        'canonical_record_hashes_file':'canonical-record-hashes.txt',
        'transformation':{
            'commit':transformation_commit,
            'corpus_script':'scripts/final_reality_bridge_corpus.py',
            'corpus_script_sha256':sha256_file(Path(__file__)),
            'source_validator':'scripts/final_reality_bridge_world_source.py',
            'source_validator_sha256':sha256_file(repo/'scripts/final_reality_bridge_world_source.py'),
        },
    }
    result=freeze_records(
        records,
        benchmark,
        out,
        source_manifest=source_manifest,
        source_receipts=source_receipts,
    )
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
