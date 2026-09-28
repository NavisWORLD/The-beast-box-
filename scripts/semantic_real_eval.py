"""Source-attested opt-in real embedding retrieval-layer evaluation; not production."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import resource
import statistics
import sys
import time
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from types import SimpleNamespace

from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.retrieval_snapshot import ReadOnlySnapshotDB, lexical_from_snapshot
from beastbox.semantic_retrieval import OfflineSentenceTransformer, SnapshotSemanticIndex, fuse_r12_semantic

DATASET_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip"
DATASET_MD5 = "5f7d1de60b170fc8027bb7898e2efca1"  # Published BEIR archive checksum
# Independently preserved *previous project run* bytes; not a new external claim.
DATASET_SHA256 = "536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165"
MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "154917cf5a5a0657fddbae9cd0ecd85cb86dc125"
MODEL_WEIGHTS_SHA256 = "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
QUERY_COUNT, SIZES, FIXED_NOW = 24, (500, 5000), 1_800_000_000.0


def load_scifact_zip(blob: bytes):
    """Read exact test members without extracting untrusted archive paths."""
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = ("scifact/corpus.jsonl", "scifact/queries.jsonl", "scifact/qrels/test.tsv")
        if not all(name in zf.namelist() for name in names):
            raise RuntimeError("missing canonical SciFact test members")
        corpus = {
            str(x["_id"]): " ".join(filter(None, (x.get("title", ""), x.get("text", ""))))
            for x in (json.loads(line) for line in zf.read(names[0]).decode().splitlines())
        }
        queries = {
            str(x["_id"]): str(x["text"])
            for x in (json.loads(line) for line in zf.read(names[1]).decode().splitlines())
        }
        judgments = zf.read(names[2]).decode().splitlines()
    if judgments[0].strip() != "query-id\tcorpus-id\tscore":
        raise RuntimeError("test judgment schema mismatch")
    qrels: dict[str, set[str]] = {}
    for line in judgments[1:]:
        qid, doc, score = line.split("\t")
        if int(score) > 0:
            qrels.setdefault(qid, set()).add(doc)
    if len(corpus) < 5000 or len(queries) < QUERY_COUNT or not qrels:
        raise RuntimeError("SciFact data are incomplete")
    return corpus, queries, qrels


def select_queries(queries, qrels, corpus):
    # Fixed lexicographic test IDs before embedding inspection; never train/tune.
    eligible = [q for q in sorted(qrels) if q in queries and qrels[q] <= corpus.keys()]
    if len(eligible) < QUERY_COUNT:
        raise RuntimeError("not enough judged test queries")
    return eligible[:QUERY_COUNT]


def select_documents(corpus, qrels, selected, size):
    # Positive-enriched sampling is deliberately disclosed, never described as random.
    positive = set().union(*(qrels[q] for q in selected))
    if len(positive) > size:
        raise RuntimeError("too many positive sources for chosen size")
    docs = sorted(positive | set(sorted(corpus.keys() - positive)[:size - len(positive)]))
    if len(docs) != size:
        raise RuntimeError("insufficient benchmark rows")
    return docs


def metric_summary(rows):
    mrr = []
    recall = []
    for ids, relevant in rows:
        mrr.append(next((1.0 / rank for rank, doc in enumerate(ids[:10], 1) if doc in relevant), 0.0))
        recall.append(len(set(ids[:5]) & relevant) / len(relevant))
    return {"mrr_at_10": round(statistics.mean(mrr), 6),
            "recall_at_5": round(statistics.mean(recall), 6)}


def load_verified_scifact_archive() -> bytes:
    """Same attested bytes whether HTTPS succeeds or the owner supplies a local cache.

    Transient HTTP 502/503/504 or network errors get at most three bounded
    attempts. A configured cache is NEVER trusted without both hashes. Do not
    modify query selection or substitute a different dataset on failure.
    """
    max_bytes = 12 * 1024 * 1024
    cached = os.environ.get("BEASTBOX_SCIFACT_VERIFIED_CACHE", "")
    if cached:
        path = Path(cached).expanduser()
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("explicit SciFact cache is absent or a symlink")
        with path.open("rb") as stream:
            blob = stream.read(max_bytes + 1)
    else:
        blob = b""
        for attempt in range(3):
            request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "BeastBox-Scientific-Eval/1"})
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    blob = response.read(max_bytes + 1)
                break
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                if isinstance(exc, urllib.error.HTTPError) and exc.code not in (502, 503, 504):
                    raise RuntimeError("SciFact HTTP source rejected the request") from exc
                if attempt == 2:
                    raise RuntimeError("verified SciFact source unavailable after three attempts") from exc
                time.sleep(min(2 ** attempt, 2))
    if len(blob) > max_bytes:
        raise RuntimeError("dataset byte limit exceeded")
    if (hashlib.md5(blob).hexdigest() != DATASET_MD5  # nosec: published archive checksum
            or hashlib.sha256(blob).hexdigest() != DATASET_SHA256):
        raise RuntimeError("SciFact source checksum mismatch; no dataset substitution")
    return blob


def prepare_sources(root):
    blob = load_verified_scifact_archive()
    from huggingface_hub import HfApi, snapshot_download
    info = HfApi().model_info(MODEL_REPO, revision=MODEL_REVISION)
    if info.sha != MODEL_REVISION or info.card_data is None or info.card_data.license != "apache-2.0":
        raise RuntimeError("exact model revision/license metadata mismatch")
    path = Path(snapshot_download(
        repo_id=MODEL_REPO, revision=MODEL_REVISION, local_dir=str(root / "offline-minilm"),
        allow_patterns=["*.json", "vocab.txt", "model.safetensors", "tokenizer.json"],
    ))
    if not (path / "model.safetensors").is_file() or not (path / "modules.json").is_file():
        raise RuntimeError("safe model weights or modules absent; no unsafe pickle fallback")
    fingerprints = {
        name: hashlib.sha256((path / name).read_bytes()).hexdigest()
        for name in ("model.safetensors", "modules.json")
    }
    if fingerprints["model.safetensors"] != MODEL_WEIGHTS_SHA256:
        raise RuntimeError("model weights do not match the independently pinned safetensors SHA-256")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    return load_scifact_zip(blob), hashlib.sha256(blob).hexdigest(), path, fingerprints


def evaluate_size(size, corpus, queries, qrels, selected, provider):
    docs = select_documents(corpus, qrels, selected, size)
    id_by_source = {source: i + 1 for i, source in enumerate(docs)}
    source_by_id = {value: key for key, value in id_by_source.items()}
    rows = [
        {"id": id_by_source[source], "text": corpus[source][:8192], "created_at": FIXED_NOW,
         "kind": "file_context", "source_ids_json": "[]",
         "metadata_json": json.dumps({"benchmark_source_id": source, "archived": False})}
        for source in docs
    ]
    # Reuse the real sealed ranker over the identical pre-materialized active source rows.
    # No fabricated Hebbian learning: association reads deliberately return empty.
    ranker = RefractiveMemoryRouter(SimpleNamespace(memory=SimpleNamespace(
        db=ReadOnlySnapshotDB(rows), associations=lambda concept, limit=10: []
    )))
    semantic = SnapshotSemanticIndex(provider, min_similarity=0.40, cache_records=8192, batch_size=32)
    judged = set(docs)
    scores = {"lexical": [], "frozen_r12": [], "opt_in_hybrid": []}
    cold_ms = None
    warm_ms = []
    for qid in selected:
        query, relevant = queries[qid], qrels[qid] & judged
        if not relevant:
            raise RuntimeError("a held-out query lost its positive source")
        lex = lexical_from_snapshot(rows, query, limit=10, now=FIXED_NOW)
        frozen = ranker.rank(query, sequence=0, dyn12=[0.0] * 12,
                             r12_state=initial_r12_state(), limit=size, now=FIXED_NOW)
        started = time.perf_counter()
        learned = semantic.rank(rows, query)
        fused = fuse_r12_semantic(frozen, learned.scores, limit=10, semantic_weight=0.65)
        latency = (time.perf_counter() - started) * 1000.0
        if cold_ms is None:
            cold_ms = latency
        else:
            warm_ms.append(latency)
        scores["lexical"].append(([source_by_id[hit.id] for hit in lex], relevant))
        scores["frozen_r12"].append(([source_by_id[hit["memory_id"]] for hit in frozen[:10]], relevant))
        scores["opt_in_hybrid"].append(([source_by_id[hit["memory_id"]] for hit in fused], relevant))
    semantic.clear()
    return {
        "corpus_rows": size, "heldout_test_queries": len(selected),
        "judged_positive_count": sum(len(qrels[q] & judged) for q in selected),
        "sampling": "all selected judged positives plus lowest sorted other source IDs",
        "conditions": {name: metric_summary(values) for name, values in scores.items()},
        "semantic_plus_fusion_cold_ms": round(cold_ms, 2),
        "semantic_plus_fusion_warm_p50_ms": round(statistics.median(warm_ms), 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/semantic-real-eval.json"))
    args = parser.parse_args()
    started = time.perf_counter()
    (corpus, queries, qrels), dataset_sha, local_model, weights_sha = prepare_sources(args.output.parent)
    provider = OfflineSentenceTransformer(local_model)
    selected = select_queries(queries, qrels, corpus)
    results = []
    for size in SIZES:
        print(f"Real-model, fixed-source scientific evaluation: {size} rows", flush=True)
        results.append(evaluate_size(size, corpus, queries, qrels, selected, provider))
    receipt = {
        "schema": "beastbox-real-semantic-preregistered-v1",
        "classification": "real-pretrained-model/public-third-party-scientific-test-set",
        "model": {"id": MODEL_REPO, "revision": MODEL_REVISION,
                  "declared_license": "apache-2.0", "files_sha256": weights_sha},
        "dataset": {"url": DATASET_URL, "published_archive_md5": DATASET_MD5,
                    "pinned_previous_observation_sha256": DATASET_SHA256,
                    "verified_transport": "explicit_local_cache" if os.environ.get("BEASTBOX_SCIFACT_VERIFIED_CACHE") else "HTTPS_with_bounded_retry",
                    "observed_archive_sha256": dataset_sha, "mirror_license_label": "cc-by-sa-4.0",
                    "selected_test_query_ids": selected},
        "protocol": {"sizes": SIZES, "threshold": 0.40, "fusion_weight": 0.65,
                     "fixed_dyn12": "zero", "hebbian_associations": "empty",
                     "scope": "pre-materialized retrieval layer; positive-enriched benchmark subsets"},
        "environment": {"python": sys.version.split()[0], "host": platform.platform(),
                        "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "elapsed_s": round(time.perf_counter() - started, 2)},
        "results": results,
        "limits": ["one scientific domain, no independence or cross-domain generalization",
                   "no production user data, no tuning, no inference-model improvement claim",
                   "not a 50k-row or end-to-end runtime test; no production authorization"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BEASTBOX_REAL_EVAL_RECEIPT=" + json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
