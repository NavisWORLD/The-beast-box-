# Phase B — source-only isolated semantic staging acceptance

This addition is an **isolated functional test**, not a production deployment,
a representative scientific comparison, a 50,000-document result, or an
independent Phase A trust root. It does not modify the existing frozen
experiment, real SciFact retrieval benchmark, production Vercel/Railway
configuration, personal memories or published release assets.

## Exact scope

A dedicated public-repository standard CPU workflow on
`feature/semantic-staging-acceptance-001` builds from the candidate code
and uses only the same previously tested, SHA256-pinned public MiniLM safe
weights and independently checksum-checked public SciFact archive.
The fixture deliberately includes the judgment-positive sources; its
single-query measurements cannot establish general retrieval advantage.

It imports 100 public scientific documents in one explicitly labeled fixture
checkpoint into a **new temporary** `DurableRuntime`. Unlike the earlier
retrieval-only benchmark, it invokes the full product turn twice, measures
complete cold/warm turn times, verifies the prewarm write-lock boundary,
verifies that warmed source embeddings were reused, then closes the runtime
and reopens it with semantic routing **OFF** by default. Exact checkpoint,
memory digest and system ID must survive restart. A simulated offline
embedding provider checks the harness without networking in the default
Product CI; a pinned real model runs only in the separate public CPU workflow.

The receipt reports timing, per-query relevant documents among the first
five responses, source/weight fingerprints, process RSS and verified restart.
The 100 records and one public test query are not an owner-memory sample,
a 500/5k/50k end-to-end scaling result, a performance SLA, real adaptive
learning or an independent production security audit.

No third-party paid inference or hosted model endpoint, no new credentials,
no mutation of live Railway/Vercel and no product deployment. This candidate
is unmerged until its exact-head CI and dedicated isolated workflow pass.
[Full A–G acceptance issue](https://github.com/NavisWORLD/The-beast-box-/issues/132)
remains open.

## Recorded first functional experiment and follow-up diagnostic

The first public-CPU end-to-end run completed successfully on
[`019cccb7`](https://github.com/NavisWORLD/The-beast-box-/commit/019cccb7a3d656d46b295eb65273c1462bed77e9),
[Actions run 36353382886](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36353382886).
Its [unaltered machine receipt](SEMANTIC_STAGING_RECEIPT_001.json) records
100 real public source embeddings, a **5,241.42 ms cold full turn**, a
**607.10 ms warm full turn**, 100 warm source-cache hits and exact continuity
after shutdown/restart. This is a single CPU run, not a speed guarantee.

**Quality warning:** on fixed test query `1`, **both lexical and the full
hybrid product returned 0 of the 1 judged-positive sources in their top five**.
A green functional smoke is NOT a retrieval-quality pass. This explicit
failure-to-retrieve must be retained, not hidden by choosing a favorable query.

A second run adds *post-cold diagnostic telemetry*: the direct learned
semantic rank of the judged-positive source, plus an exploratory 24-query
100-row retrieval-layer comparison using the identical source/model
selection. These are follow-up **post-hoc diagnostics, not a new registered
scientific replication or acceptance of a model-ranking SLA**. Never merge
the two receipts as though their software and measurements were identical.
