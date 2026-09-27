# Phase B — optional active-product semantic memory (candidate; release hold)

**Status:** source-level opt-in implementation with synthetic offline controls. It
does **not** establish representative learned-model retrieval improvement, full
50k-corpus performance, audited provider identity or a production release.
Follow the unchanged [A–G acceptance gate](https://github.com/NavisWORLD/The-beast-box-/issues/132).

## Contract and boundaries

By default, `DurableRuntime` continues the **unchanged lexical → CNS → frozen
R12** route and makes **no embedding calls**. An owner-controlled Python host
may supply an optional `EmbeddingProvider` at construction. The existing
per-turn active memory snapshot, with archived rows excluded, is reused by
R12 and the semantic plugin. The frozen R12 ranker returns its original scores;
opt-in reciprocal-rank fusion ranks the same exact source rows with a separately
labeled embedding similarity. It neither rewrites R12 weights nor grants the
embedding provider tool, model-swap or owner authority.

The opt-in durable turn now runs its expensive semantic embedding pass
**outside** SQLite's write transaction, after a short validated active-snapshot
read. When it reacquires the write lock, it compares the exact checkpoint tip
and every source snapshot field (including archive metadata and provenance)
before accepting the prefetched scores. If anything changed concurrently,
the turn fails closed with an explicit retry error, discards its cache, and
does not silently switch to lexical-only mode. The in-transaction shared
lexical/CNS/R12 snapshot remains a single materialized read. The frozen R12
ranker still executes inside the transaction; its CPU cost remains a separate
performance consideration. An external peer can archive records during the
unlocked embedding interval: that concurrent change is rejected before
fusion, but already-started embedding calls cannot be retroactively erased
or prevented from seeing their earlier, then-active source snapshot.

No vectors are added to the memory database, historical V1, permanent
checkpoint state, or provider model weights. A bounded per-process cache is
keyed by memory ID and exact text SHA-256. Cache misses are encoded in batches,
up to 8,192 characters per retained record. The default caps are 50,000 rows,
2,048 cached vectors, 32 rows per batch and 4,096 vector dimensions. Exceeding
a cap or returning malformed/nonfinite embeddings raises an error and rolls
back the durable turn. An explicit semantic-provider failure is **not** a
permission to switch silently to an unapproved provider or lexical-only mode.
An empty memory corpus involves no provider call.

Successful opt-in turns record `routing.semantic` with the configured provider
label, local-only declaration, matched-record count, cache-hit count, threshold
and elapsed time. **Labels and flags are declarations, not weight attestation
or proof that an arbitrary host plugin cannot make network requests.**
Original `memory_id`, text, source IDs and historical `r12_score` are
preserved through fusion. Archived records are never candidates. Owner-reviewed
restore makes the original eligible again. Runtime archiving promptly evicts
that source's cached vector; the next active snapshot also prunes vectors for
rows archived or changed by other runtime instances, and shutdown clears the
process cache. Python cache eviction is not a forensic RAM-erasure guarantee.

## Preloaded, offline learned embedding option

Install only if wanted:

```bash
python -m pip install -e .
python -m pip install 'sentence-transformers>=3.4'
```

The operator **separately obtains, licenses, inspects and locally installs**
a compatible sentence-transformers model. The runtime does **not** download a
model from a model name and does not silently make network calls to locate
model weights. Example for an existing preloaded local folder:

```python
from beastbox.durable import DurableRuntime
from beastbox.semantic_retrieval import OfflineSentenceTransformer

embeddings = OfflineSentenceTransformer("/trusted/local/model-folder")
runtime = DurableRuntime("/trusted/runtime-state", embedding_provider=embeddings)
try:
    response = runtime.respond("Where did I leave the vehicle?")
    print(response["routing"])
finally:
    runtime.close()
```

The adapter requests `local_files_only=True` and
`trust_remote_code=False`. Verify your installed library and the model folder
for supply-chain and local data-custody requirements. The optional embedding dependency is installed separately by the owner, rather
than modifying the repository's pinned default dependency lock. It is never
initialized by default.

Other embedding plugins are trusted host Python code, **not isolated tools**.
They must explicitly provide `model_id`, `local_only` and
`embed_many(texts)`. A plugin declaring `local_only=False` is refused unless
the host separately constructs the runtime with
`allow_remote_embeddings=True`. This flag allows sending active personal
memory to that selected plugin; obtain informed owner approval first. It does
not grant blanket permission to spend money or change other services.

## Candidate test and scientific boundaries

`tests/test_finisher_semantic_retrieval.py` tests: default compatibility,
deterministic **synthetic** synonym-ranking controls, immutable source
provenance, archive/restore exclusion, failure rollback, malformed-vector
rejection, no unapproved remote plugin and an offline adapter loading contract.
The synthetic equivalence class is **not** evidence of real learned
embeddings, an accuracy advantage, general-language synonym performance,
or latency at 500/5k/50k rows.

Before closing Phase B: independently run a fixed, licensed,
source-attested learned model with disjoint reviewer-labeled relevance queries;
preregister lexical-only, frozen-R12 and opt-in hybrid baselines; report per-query
relevance metrics, failure/privacy behavior, memory/CPU and replicated
500/5k/50k latency. Keep the production/release hold and the separate Phase A
external trust-root requirement in effect.
