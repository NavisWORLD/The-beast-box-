"""Real-model, isolated end-to-end semantic product smoke. No production data or authority.

This is a *functional* staging acceptance check over a deliberately
positive-enriched public scientific subset, not an unbiased ranking benchmark,
a 50k proof, a live deployment, or an independent trust-root acceptance.
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from beastbox.durable import DurableRuntime
from beastbox.hashutil import sha256_obj
from beastbox.providers import ReferenceTextProvider
from beastbox.retrieval_snapshot import capture_snapshot, lexical_from_snapshot
from beastbox.semantic_retrieval import OfflineSentenceTransformer
from scripts.semantic_real_eval import prepare_sources, select_documents, select_queries


def run_staging(corpus, queries, qrels, selected, embedding_provider, *,
                root: Path, records: int = 100) -> dict:
    """Use one isolated real DurableRuntime, then cold-reopen as default-off.

    The caller supplies public third-party inputs and an already installed
    embedding adapter. No network, external host, owner data, or extra resource
    allocation occurs in this function.
    """
    if type(records) is not int or records not in (100, 500):
        raise ValueError("staging smoke supports only 100 or 500 records")
    if not selected or selected[0] not in queries or selected[0] not in qrels:
        raise ValueError("a judged public test query is required")
    documents = select_documents(corpus, qrels, selected, records)
    source_digest = sha256_obj({source: corpus[source][:8192] for source in documents})
    query_id = selected[0]
    query = queries[query_id]
    relevant = qrels[query_id] & set(documents)
    if not relevant:
        raise RuntimeError("selected query has no judged source in staging corpus")
    memory_to_source = {}
    runtime = DurableRuntime(
        root, ReferenceTextProvider(prefix="isolated-stage-fixture"),
        embedding_provider=embedding_provider,
    )
    try:
        seed_start = time.perf_counter()
        # This one checkpointed bulk import is exclusively for isolated
        # benchmark staging. It does not fake 100 real conversational turns.
        with runtime.memory.transaction():
            before = runtime.continuity.verify()
            for source in documents:
                memory_id = runtime.memory.store(
                    corpus[source][:8192], kind="public_scientific_staging",
                    metadata={"origin": "public-third-party-SciFact", "source_id": source},
                )
                memory_to_source[memory_id] = source
            runtime.continuity.append(
                runtime._state(), system_id=runtime.system_id,
                receipt={"kind": "public-scientific-staging-bulk-fixture",
                         "source_rows": records, "source_digest": source_digest,
                         "previous_checkpoint_sha256": before["sha256"]},
            )
        seed_ms = (time.perf_counter() - seed_start) * 1000
        original = runtime.inspect()
        if original["memory"]["memories"] != records:
            raise RuntimeError("isolated source corpus was not fully imported")

        snapshot = capture_snapshot(runtime.memory)
        baseline = lexical_from_snapshot(snapshot, query, limit=5)
        baseline_sources = [memory_to_source[hit.id] for hit in baseline]
        cold_start = time.perf_counter()
        cold = runtime.respond(query)
        cold_ms = (time.perf_counter() - cold_start) * 1000
        if cold["metrics"]["status"] != "committed" or cold["routing"]["router"] != "R12+opt_in_semantic_rrf":
            raise RuntimeError("actual semantic product turn did not commit")
        if "semantic_prewarm" not in cold["trace"]:
            raise RuntimeError("real embedding prewarm did not execute")
        if cold["routing"]["semantic"].get("outside_write_transaction") is not True:
            raise RuntimeError("embedding write-lock boundary not confirmed")
        if cold["routing"]["semantic"]["embedded_records"] < records:
            raise RuntimeError("cold run did not embed the declared real sources")
        cold_sources = [
            memory_to_source[hit["id"]] for hit in cold["memory_hits"]
            if hit["id"] in memory_to_source
        ]
        warm_start = time.perf_counter()
        warm = runtime.respond(query)
        warm_ms = (time.perf_counter() - warm_start) * 1000
        if warm["metrics"]["status"] != "committed":
            raise RuntimeError("warm turn failed")
        if warm["routing"]["semantic"]["cache_hits"] < records:
            raise RuntimeError("warm run did not reuse source embeddings")
        last = runtime.inspect()
        if last["turn"] != 2 or last["sequence"] != original["sequence"] + 2:
            raise RuntimeError("stage fixture lost turn continuity")
        checkpoint = last["checkpoint_sha256"]
        digest = last["memory_digest"]
        system_id = last["system_id"]
    finally:
        runtime.close()
    # Brand-new runtime and provider: no hidden semantic cache or implicit opt-in.
    reopened = DurableRuntime(root, ReferenceTextProvider(prefix="fresh-default-off"))
    try:
        recovered = reopened.inspect()
        if (recovered["checkpoint_sha256"], recovered["memory_digest"], recovered["system_id"]) != (
                checkpoint, digest, system_id):
            raise RuntimeError("restart did not reproduce the exact durable state")
        if reopened.semantic_index is not None or not recovered["valid"]:
            raise RuntimeError("implicit semantic opt-in after restart")
    finally:
        reopened.close()
    return {
        "schema": "beastbox-isolated-real-semantic-staging-v1",
        "classification": "real-pretrained-embeddings-isolated-public-fixture-end-to-end-smoke",
        "records": records, "query_id": query_id,
        "sampling": "positive-enriched; NOT representative and NOT 50k",
        "public_source_digest": source_digest,
        "judged_positives_available": len(relevant),
        "lexical_relevant_in_top_5": len(set(baseline_sources) & relevant),
        "hybrid_relevant_in_top_5": len(set(cold_sources) & relevant),
        "configured_embedding_provider": embedding_provider.model_id,
        "embedding_outside_write_transaction": True,
        "warm_source_cache_hits": warm["routing"]["semantic"]["cache_hits"],
        "cold_embedded_records": cold["routing"]["semantic"]["embedded_records"],
        "seed_ms": round(seed_ms, 2),
        "end_to_end_cold_turn_ms": round(cold_ms, 2),
        "end_to_end_warm_turn_ms": round(warm_ms, 2),
        "exact_checkpoint_verified_after_restart": True,
        "default_semantic_disabled_after_restart": True,
        "production_or_external_authority_deployed": False,
        "claims": "one fixed public test query; does not establish ranking superiority or SLA",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(100, 500), default=100)
    parser.add_argument("--output", type=Path, default=Path("build/semantic-staging-acceptance.json"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("receipt already exists; never replace previous measurement")
    # No model/dataset bytes are uploaded as workflow artifacts. Never use
    # owner memory, secrets or live infrastructure in this isolated fixture.
    with TemporaryDirectory(prefix="beastbox-public-staging-") as work:
        (corpus, queries, qrels), data_sha, model_path, model_hashes = prepare_sources(Path(work))
        provider = OfflineSentenceTransformer(model_path)
        selected = select_queries(queries, qrels, corpus)
        result = run_staging(
            corpus, queries, qrels, selected, provider,
            root=Path(work) / "clean-durable-runtime", records=args.records,
        )
    result.update({
        "model": {"repo": "sentence-transformers/all-MiniLM-L6-v2",
                  "revision": "154917cf5a5a0657fddbae9cd0ecd85cb86dc125",
                  "verified_files_sha256": model_hashes},
        "dataset": {"name": "BEIR SciFact", "archive_sha256": data_sha},
        "environment": {"python": platform.python_version(),
                        "host": platform.platform(),
                        "peak_process_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BEASTBOX_STAGING_RECEIPT=" + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
