"""Pinned independent recovery of nine published IBM Fez serialized 5-bit results.

Historical public Git blobs exist at the exact source commit despite a later
summary-only adapter. Verify EACH exact git-blob SHA-1 before parsing. Decode
the archived serialized sampler BitArray bytes, then independently compare
histogram-derived totals, entropy and highest-frequency state against the
existing published summary. Never connect to IBM, submit hardware jobs,
authenticate an original result with IBM, or modify the sealed historic null.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
import zlib

from beastbox.hashutil import sha256_obj
from beastbox.soul.archive_summary import (
    IBM_FEZ_REPORTED_SUMMARIES, SOURCE_COMMIT, SOURCE_REPO,
)

SCHEMA = "ibm-fez-pinned-serialized-bitarray-redecode-v1"
RAW_DIR = "workloads (5)"
# Exact original Git blob identities fetched from the historical source tree at
# SOURCE_COMMIT; do not trust path/name alone.
BLOBS = {
    "d6p6l343pels73a3jvc0": ("d3821b61b53f404dd58209906aff7dc67bae80ef","4dcf223f6314cd70997404c7e0427e9dcc17b45d"),
    "d6p6l8gbfi7c73a6n73g": ("9f8b1a094b697ff1779eb2a092fd2e313102c7b1","2357f68169602cc002e1a9a7a6c5a8fde4ae6f53"),
    "d6p6lpobfi7c73a6n7rg": ("25db6ab24b61cd05b10020f86a2a1511a4adad4d","938e60f8f59c06f4db0a91f7428293d7e87a4c17"),
    "d6p6m269td6c73aq5jl0": ("5b5e2717c85a7867d3243f556a93b3e90ee82078","123a274097d8c171e9fd12bd957f1f798d7acc02"),
    "d6p6m6e9td6c73aq5jqg": ("4e8e568b462cd7786726281fba8d159fbccac908","c08abf0b9533a407b3ee5575bee3ff59ba600b9b"),
    "d6p6mbgbfi7c73a6n8ig": ("84c857e26e3bdca0a8303ddec8a98ea3d3e4d298","0e99a664d741333921ba3ceb02272d4a186e0b55"),
    "d6p6mfs3pels73a3k110": ("dcb5c0a172d419cd4616268718ce5353f0772aaa","e60c43a8e073d15fbc4ffc828a07541dbb5b557f"),
    "d6p6mlc3pels73a3k190": ("05d343ac9dc0859bc902ebf9b5c72bfe577f2681","2cc36e67a6c9f2245937ccbb8e5067b8e2e17dc7"),
    "d6p6mrc3pels73a3k1f0": ("5d72d873936e69425bc24a63a1befaec0683ff81","83918e23df97051ab261163bc2f827d22aeda003"),
}


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}".encode("ascii") + bytes([0]) + raw).hexdigest()


def decode_serialized_bitarray(payload: dict) -> tuple[dict[str,int], int]:
    """Decode source-export BitArray (byte-packed 5 bits per 4224 shots)."""
    if not isinstance(payload,dict) or payload.get("__type__")!="PrimitiveResult":
        raise ValueError("not archived PrimitiveResult JSON")
    pub=payload["__value__"]["pub_results"]
    if not isinstance(pub,list) or len(pub)!=1 or pub[0].get("__type__")!="SamplerPubResult":
        raise ValueError("unexpected published sampler shape")
    data=pub[0]["__value__"]["data"]["__value__"]["fields"]["meas"]["__value__"]
    if data.get("__type__")!="BitArray" or data.get("num_bits")!=5:
        raise ValueError("historical experiment width must be five bits")
    array=data["array"]
    if array.get("__type__")!="ndarray":
        raise ValueError("unknown serialized ndarray")
    encoded=array["__value__"]
    if not isinstance(encoded,str) or not 1<=len(encoded)<=20_000:
        raise ValueError("invalid archived payload size")
    compressed=base64.b64decode(encoded,validate=True)
    decompressor=zlib.decompressobj()
    raw=decompressor.decompress(compressed,65536)
    if not decompressor.eof or decompressor.unconsumed_tail or decompressor.unused_data:
        raise ValueError("invalid or unbounded packed BitArray compression")
    if len(raw)!=4224:
        raise ValueError("unexpected shot count or byte-pack width")
    if any(value>=32 for value in raw):
        raise ValueError("non-five-bit measurement present")
    counts=Counter(format(value,"05b") for value in raw)
    return ({format(x,"05b"):counts.get(format(x,"05b"),0) for x in range(32)},len(raw))


def historical_entropy(counts: dict[str,int]) -> float:
    positive=[v for v in counts.values() if v]
    if len(positive)<=1:
        return 0.0
    total=sum(positive)
    return -sum((v/total)*math.log2(v/total) for v in positive)/math.log2(len(positive))


def _download_exact(id_:str, suffix:str, expected_git_sha:str)->bytes:
    path=f"{RAW_DIR}/job-{id_}-{suffix}.json"
    # Raw URL, immutable commit+tree+blob integrity, no Azure/IBM credentials.
    url=f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{quote(path,safe='/')}"
    with urlopen(url,timeout=15) as response:
        if response.status != 200:
            raise ValueError("pinned historical source unavailable")
        raw=response.read(9000)
    if not 1<=len(raw)<9000 or git_blob_sha1(raw)!=expected_git_sha:
        raise ValueError("historical Git blob SHA did not match pinned record")
    return raw


def recover()->dict:
    if len(IBM_FEZ_REPORTED_SUMMARIES)!=len(BLOBS):
        raise ValueError("source catalog and pinned result files do not match")
    rows=[]
    for summary in IBM_FEZ_REPORTED_SUMMARIES:
        ident=summary["job_id"]
        if ident not in BLOBS:
            raise ValueError("unrecognized historical source ID")
        result_sha,info_sha=BLOBS[ident]
        result_raw=_download_exact(ident,"result",result_sha)
        info_raw=_download_exact(ident,"info",info_sha)
        result=json.loads(result_raw)
        info=json.loads(info_raw)
        if (info.get("id")!=ident or info.get("backend")!="ibm_fez"
            or info.get("status")!="Completed" or info.get("created")!=summary["timestamp"]):
            raise ValueError("archived provider-export metadata did not match summary")
        counts,shots=decode_serialized_bitarray(result)
        entropy=historical_entropy(counts)
        # The original converter rounds normalized Shannon entropy to 4 decimals.
        # Independent recovery MUST match, not overwrite, the published summary.
        summary_top=summary["top_state"]
        highest=max(counts.values())
        if (shots!=summary["total_shots"]
            or abs(round(entropy,4)-float(summary["entropy"]))>0.00011
            or counts.get(summary_top,0)!=highest):
            raise ValueError("raw exported measurement and historical published summary disagree")
        rows.append({
            "job_id":ident,"backend":"ibm_fez","timestamp":summary["timestamp"],
            "source_reported_status":"Completed","shots":shots,
            "counts":counts,"entropy_redecoded":entropy,
            "original_summary_entropy":summary["entropy"],
            "original_summary_top_state":summary_top,
            "original_top_is_modal_state":True,
            "info_git_blob_sha1":info_sha,"result_git_blob_sha1":result_sha,
            "info_sha256":hashlib.sha256(info_raw).hexdigest(),
            "result_sha256":hashlib.sha256(result_raw).hexdigest(),
            "counts_sha256":sha256_obj(counts),
        })
    return {
        "schema":SCHEMA,
        "classification":"SOURCE_REPORTED_ARCHIVED_SERIALIZED_IBM_PRIMITIVE_EXPORT_INDEPENDENTLY_REDECODED",
        "repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"source_folder":RAW_DIR,
        "pinned_git_blobs_verified":True,"original_summary_crosscheck_passed":True,
        "independent_provider_api_confirmation":False,
        "new_ibm_hardware_jobs":0,
        "new_azure_qvm_jobs":0,
        "historical_closed_four_state_experiment_reinterpreted":False,
        "records":rows,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("build/rigetti-qvm-cosmos-012-redecoded-raw.json"))
    args=parser.parse_args()
    out=recover()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("ARCHIVED_IBM_FEZ_PINNED_RAW_5BIT_REDECODE_PASS",len(out["records"]),
          "shots_total",sum(r["shots"] for r in out["records"]),
          "source_commit",SOURCE_COMMIT,flush=True)


if __name__=="__main__":
    main()
