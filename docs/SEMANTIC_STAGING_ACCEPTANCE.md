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
