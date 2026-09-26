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
import ast
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

SCHEMA = "ibm-fez-pinned-serialized-bitarray-npy-corrected-v2"
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


def decode_serialized_bitarray(payload: dict) -> tuple[dict[str,int], int, int]:
    """Parse verified zlib-compressed NPY, stripping its HEADER before shots.

    Historical decode_workloads.py had decoded *the whole* NPY file as uint8,
    mistakenly including 128 bytes of NPY metadata as 128 extra outcomes.
    This is a separate re-decode; it does not revise sealed prior experiments.
    """
    if not isinstance(payload,dict) or payload.get("__type__")!="PrimitiveResult":
        raise ValueError("not archived PrimitiveResult JSON")
    pub=payload["__value__"]["pub_results"]
    if not isinstance(pub,list) or len(pub)!=1 or pub[0].get("__type__")!="SamplerPubResult":
        raise ValueError("unexpected published sampler shape")
    field=pub[0]["__value__"]["data"]["__value__"]["fields"]["meas"]
    if field.get("__type__")!="BitArray":
        raise ValueError("archived sampler field is not BitArray")
    data=field["__value__"]
    if data.get("num_bits")!=5:
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
    if not raw.startswith(bytes([0x93])+b"NUMPY") or raw[6:8]!=bytes([1,0]):
        raise ValueError("unexpected compressed NumPy header version or signature")
    head_len=int.from_bytes(raw[8:10],"little")
    offset=10+head_len
    if head_len<16 or head_len>1024 or offset>=len(raw) or offset%16:
        raise ValueError("invalid compressed NumPy envelope size")
    try:
        header=ast.literal_eval(raw[10:offset].decode("latin1").strip())
    except (ValueError,SyntaxError,UnicodeError) as exc:
        raise ValueError("invalid NumPy header") from exc
    if (not isinstance(header,dict) or header.get("descr") not in ("|u1","<u1","u1")
        or header.get("fortran_order") is not False
        or header.get("shape") not in ((4096,1),(4096,))):
        raise ValueError("unexpected archived five-qubit sample dtype or array shape")
    shots=raw[offset:]
    if len(shots)!=4096 or any(value>=32 for value in shots):
        raise ValueError("unexpected true shot count or byte-pack width")
    counts=Counter(format(value,"05b") for value in shots)
    return ({format(x,"05b"):counts.get(format(x,"05b"),0) for x in range(32)},len(shots),offset)


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
        counts,shots,header_bytes=decode_serialized_bitarray(result)
        entropy=historical_entropy(counts)
        summary_top=summary["top_state"]
        highest=max(counts.values())
        if shots + header_bytes != summary["total_shots"]:
            raise ValueError("archived raw-array length could not explain published shot-count discrepancy")
        if header_bytes!=128:
            raise ValueError("unexpected NPY header length in archived source")
        original_top_still_modal=counts.get(summary_top,0)==highest
        original_entropy_matches=abs(round(entropy,4)-float(summary["entropy"]))<=0.00011
        rows.append({
            "job_id":ident,"backend":"ibm_fez","timestamp":summary["timestamp"],
            "source_reported_status":"Completed","shots":shots,
            "original_summary_claimed_entries":summary["total_shots"],
            "npy_container_header_bytes_removed":header_bytes,
            "counts":counts,"entropy_redecoded":entropy,
            "original_summary_entropy":summary["entropy"],
            "original_summary_top_state":summary_top,
            "original_summary_top_still_modal_after_correction":original_top_still_modal,
            "original_summary_entropy_matches_corrected":original_entropy_matches,
            "corrected_modal_states":sorted(key for key,val in counts.items() if val==highest),
            "info_git_blob_sha1":info_sha,"result_git_blob_sha1":result_sha,
            "info_sha256":hashlib.sha256(info_raw).hexdigest(),
            "result_sha256":hashlib.sha256(result_raw).hexdigest(),
            "counts_sha256":sha256_obj(counts),
        })
    return {
        "schema":SCHEMA,
        "classification":"SOURCE_REPORTED_ARCHIVED_SERIALIZED_IBM_PRIMITIVE_EXPORT_INDEPENDENTLY_REDECODED",
        "repository":SOURCE_REPO,"commit":SOURCE_COMMIT,"source_folder":RAW_DIR,
        "pinned_git_blobs_verified":True,
        "archived_metadata_identity_crosscheck_passed":True,
        "original_summary_parser_included_npy_header_bytes":True,
        "original_summary_values_retained_as_historical_only":True,
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
    print("ARCHIVED_IBM_FEZ_PINNED_NPY_CORRECTED_REDECODE_PASS",len(out["records"]),
          "true_shots_total",sum(r["shots"] for r in out["records"]),
          "total_npy_header_bytes_removed",sum(r["npy_container_header_bytes_removed"] for r in out["records"]),
          "original_entropy_matching_rows",sum(r["original_summary_entropy_matches_corrected"] for r in out["records"]),
          "source_commit",SOURCE_COMMIT,flush=True)


if __name__=="__main__":
    main()
