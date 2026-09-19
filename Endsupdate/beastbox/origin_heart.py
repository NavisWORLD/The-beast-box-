from __future__ import annotations
import ast,base64,hashlib,json,struct,zlib
from collections import Counter
from pathlib import Path
from typing import Any,Mapping
from beastbox.bridge import BridgePacket,spark_from_counts
from beastbox.cns import CNS
from beastbox.descendant.quantum import QuantumEvidenceRecord,derive_feature_packet
from beastbox.hashutil import sha256_obj
from beastbox.state import MissionState,StateCapsule
from beastbox.state_family import StateFamily
LINEAGE="ZEREF-ORIGIN-HEART-001"; BRIDGE_VERSION="zeref-origin-heart-cst-bridge-v1"
def _canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha(x): return hashlib.sha256(_canon(x)).hexdigest()
def _fsha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def _source_bytes(p:Path,mode:str)->bytes:
    b=p.read_bytes()
    if mode=="none": return b
    if mode=="strip_exactly_one_final_lf_before_raw_sha_verification":
        if not b.endswith(b"\n") or b.endswith(b"\n\n"): raise ValueError("declared final-LF normalization mismatch")
        return b[:-1]
    raise ValueError(f"unsupported transport normalization: {mode}")
def _npy_u8(payload:bytes)->tuple[bytes,tuple[int,...]]:
    if not payload.startswith(b"\x93NUMPY"): raise ValueError("not an NPY stream")
    major=payload[6]
    if major==1: n=struct.unpack("<H",payload[8:10])[0]; start=10
    elif major in {2,3}: n=struct.unpack("<I",payload[8:12])[0]; start=12
    else: raise ValueError("unsupported NPY version")
    header=ast.literal_eval(payload[start:start+n].decode("latin1").strip())
    if str(header.get("descr")) not in {"|u1","<u1",">u1","u1"}: raise ValueError("unsupported ndarray dtype")
    if header.get("fortran_order"): raise ValueError("Fortran-order array unsupported")
    shape=tuple(int(v) for v in header.get("shape") or ())
    if len(shape)!=2 or any(v<=0 for v in shape): raise ValueError("unexpected ndarray shape")
    body=payload[start+n:]
    if len(body)!=shape[0]*shape[1]: raise ValueError("ndarray length mismatch")
    return body,shape
def decode_sampler_bitarray(result:Mapping[str,Any])->tuple[dict[str,int],int,int]:
    try:
        field=result["__value__"]["pub_results"][0]["__value__"]["data"]["__value__"]["fields"]["c"]
        if field["__type__"]!="BitArray": raise ValueError("field c is not BitArray")
        value=field["__value__"]; bits=int(value["num_bits"]); arr=value["array"]
        if arr["__type__"]!="ndarray": raise ValueError("BitArray is not ndarray")
        npy=zlib.decompress(base64.b64decode(str(arr["__value__"]),validate=True))
    except (KeyError,IndexError,TypeError) as e: raise ValueError("malformed SamplerV2 result") from e
    if bits<=0: raise ValueError("num_bits must be positive")
    body,shape=_npy_u8(npy); shots,row_bytes=shape
    if row_bytes!=(bits+7)//8: raise ValueError("byte width mismatch")
    mask=(1<<bits)-1; counts=Counter()
    for i in range(0,len(body),row_bytes): counts[format(int.from_bytes(body[i:i+row_bytes],"big")&mask,f"0{bits}b")]+=1
    if sum(counts.values())!=shots: raise ValueError("shot total mismatch")
    return dict(sorted(counts.items())),shots,bits
def derive_runtime_seed(origin_heart_sha256:str)->int:
    d=str(origin_heart_sha256).lower()
    if len(d)!=64 or any(c not in "0123456789abcdef" for c in d): raise ValueError("origin heart SHA-256 must be hex")
    return int(hashlib.sha256(f"{BRIDGE_VERSION}:runtime-seed:{d}".encode()).hexdigest()[:16],16)
def build_origin_heart(jobs:list[dict[str,Any]],*,out_dir:Path)->dict[str,Any]:
    if len(jobs)!=2: raise ValueError("Origin Heart v1 requires exactly two source jobs")
    ordered=sorted(jobs,key=lambda r:(str(r["created"]),str(r["job_id"])))
    if len({str(r["job_id"]) for r in ordered})!=2: raise ValueError("source job IDs must be unique")
    family=StateFamily(); cns=CNS(); mission=MissionState(mission_id=LINEAGE,objective="CST Origin Heart hardware measurement bridge",pending_steps=[str(r["job_id"]) for r in ordered]); traces=[]; fhash=[]; bhash=[]; total=0
    for idx,row in enumerate(ordered,1):
        jid=str(row["job_id"]); backend=str(row["backend"])
        if row.get("source_class")!="hardware" or row.get("status")!="Completed": raise ValueError("source must be completed hardware")
        path=Path(str(row["result_path"])); committed=_fsha(path)
        if committed!=str(row["committed_result_sha256"]): raise ValueError(f"committed SHA mismatch: {jid}")
        raw=_source_bytes(path,str(row["transport_normalization"])); raw_sha=hashlib.sha256(raw).hexdigest()
        if raw_sha!=str(row["raw_result_sha256"]): raise ValueError(f"raw SHA mismatch: {jid}")
        obj=json.loads(raw); canonical=hashlib.sha256(_canon(obj)).hexdigest()
        if canonical!=str(row["canonical_result_sha256"]): raise ValueError(f"canonical SHA mismatch: {jid}")
        counts,shots,width=decode_sampler_bitarray(obj)
        if shots!=int(row["shot_count"]): raise ValueError("decoded shots mismatch")
        total+=shots
        evidence=QuantumEvidenceRecord(provider="IBM Quantum",backend=backend,source_class="hardware",shot_count=shots,source_sha256=raw_sha,job_id=jid,circuit_id=f"origin-heart-{idx}",confidence="verified",reason="Completed frozen IBM hardware SamplerV2 result")
        feature=derive_feature_packet(evidence,counts); spark=spark_from_counts(counts,dimensions=12)
        bridge=BridgePacket(quantum_spark=spark,quantum_provenance={"provider":"IBM Quantum","backend":backend,"job_id":jid,"source_class":"hardware","shot_count":shots,"raw_result_sha256":raw_sha,"feature_packet_sha256":feature.packet_sha256},metadata={"lineage":LINEAGE,"bridge_version":BRIDGE_VERSION,"source_index":idx}); bd=bridge.safe_dict(); fs=family.update(spark)
        mission.current_step=idx; mission.pending_steps=[str(x["job_id"]) for x in ordered[idx:]]; mission.completed_steps.append(jid); mission.evidence.append(feature.packet_sha256); mission.quantum_spark=list(spark); mission.provenance={"lineage":LINEAGE,"bridge_version":BRIDGE_VERSION,"last_job_id":jid,"last_backend":backend,"last_feature_packet_sha256":feature.packet_sha256,"last_bridge_packet_sha256":bd["packet_sha256"]}; cs=cns.tick(mission,bd)
        fhash.append(feature.packet_sha256); bhash.append(str(bd["packet_sha256"])); traces.append({"schema":"zeref-origin-heart-bridge-trace-v1","step":idx,"job_id":jid,"backend":backend,"created":str(row["created"]),"source_class":"hardware","shot_count":shots,"bit_width":width,"raw_result_sha256":raw_sha,"canonical_result_sha256":canonical,"counts_sha256":feature.counts_sha256,"feature_packet_sha256":feature.packet_sha256,"features":dict(feature.features),"bridge_packet_sha256":bd["packet_sha256"],"quantum_spark":list(spark),"state_family_sha256":sha256_obj(fs),"mission_state_sha256":mission.digest(),"cns":cs})
    pre=family.preflight()
    if not all(bool(x["live"]) for x in pre.values()): raise RuntimeError("CST state-family preflight not live")
    capsule=StateCapsule.freeze(mission); cap=capsule.to_dict(); StateCapsule.from_dict(cap)
    body={"schema":"zeref-origin-heart-v1","lineage":LINEAGE,"bridge_version":BRIDGE_VERSION,"source_order":[str(r["job_id"]) for r in ordered],"source_backends":[str(r["backend"]) for r in ordered],"source_raw_sha256s":[str(r["raw_result_sha256"]) for r in ordered],"hardware_rounds":2,"observed_shots_total":total,"feature_packet_sha256s":fhash,"bridge_packet_sha256s":bhash,"state_family_step":family.step,"state_family_sha256":sha256_obj(family.as_dict()),"state_family_preflight":pre,"mission_state_sha256":mission.digest(),"state_capsule":cap,"claim_boundary":"Deterministic CST reference state from verified IBM hardware measurements; no quantum-advantage, biological-heartbeat, deceased-person identity, or consciousness claim."}
    oh=_sha(body); out=dict(body); out["origin_heart_sha256"]=oh; out["runtime_seed"]=derive_runtime_seed(oh); out_dir.mkdir(parents=True,exist_ok=True); op=out_dir/"origin-heart.json"; tp=out_dir/"bridge-trace.jsonl"; op.write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); tp.write_text("".join(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n" for r in traces),encoding="utf-8"); (out_dir/"SHA256SUMS").write_text(f"{_fsha(op)}  {op.name}\n{_fsha(tp)}  {tp.name}\n",encoding="utf-8"); return out
