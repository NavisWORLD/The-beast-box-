# Phase B: Preregistered real learned-embedding evaluation (source-only)

No production deployment, paid Hugging Face Jobs, private owner data, new
secrets, model training or merging. The trigger is limited to changes to this
source-only experiment on the PR #134 feature branch. It runs on a standard
free GitHub-hosted Ubuntu public-repository runner; it does NOT upload an
artifact to avoid expanding potentially billable Actions storage. The
GitHub job log includes the entire source-hashed JSON result receipt.

## Prespecified inputs and methods

- Learned model: sentence-transformers/all-MiniLM-L6-v2, pinned revision
  f5610b47471b118dafc55f4c387822dbfc8413ae; the upstream model card
  *declares* Apache-2.0. This is not a training-source license audit or an
  assertion about suitability for commercial redistribution.
- Source: public BEIR/SciFact scientific retrieval test set. Published
  archive MD5: 5f7d1de60b170fc8027bb7898e2efca1. Record observed archive
  SHA-256 and pinned model safetensors SHA-256. Hugging Face's dataset mirror
  declares CC BY-SA 4.0; upstream evidence/source rights may differ.
  Do not publish or redistribute third-party documents from the run.
- Query IDs: the first 24 eligible TEST relevance-query IDs in sorted order,
  fixed independently of any model answer. No train or development queries
  are used for tuning or scoring. All selected positive source IDs included,
  then fill sorted other source IDs to 500 and 5000 rows. Because positives
  are enriched, these are not unbiased samples.
- Read identical pre-materialized active rows. Compare existing
  lexical_from_snapshot, frozen RefractiveMemoryRouter with zero dyn12 and
  no trained Hebbian associations, and unchanged opt-in R12+semantic reciprocal
  rank fusion. The semantic cosine acceptance threshold is 0.40, fusion
  weight 0.65, output limit 10. No hyperparameter search.
- Always report all three conditions' MRR@10 and Recall@5, plus measured
  first-query semantic+fusion cold latency, median later-query latency,
  overall wall time, peak process resident memory, source checksums,
  execution environment and all 24 test-query IDs, regardless of outcome.
  Fail rather than quietly substituting a mock model or benchmark.

## Boundaries and next gates

This is a real pretrained embedding checkpoint with third-party held-out
scientific-document relevance judgments; it is not a demonstration of a
general intelligence improvement, personally representative Beast Box
memory, cross-domain quality, an end-to-end product speedup, 50k-record
scale, real-model A-B-A routing, science beyond this observed benchmark
or independent production trust-root completion. Full issue #132 remains
open. The frozen V1 and original R12 source remain untouched.

Citations and provenance:
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
https://huggingface.co/datasets/BeIR/scifact
https://github.com/beir-cellar/beir/wiki/Datasets-available
https://docs.github.com/en/actions/reference/runners/github-hosted-runners
