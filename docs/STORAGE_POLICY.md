# Storage policy

Do not rewrite Git history to shrink the canonical lab.

Forward-looking rule:

```text
NO NEW LARGE RAW EXPERIMENT DUMPS IN NORMAL PRODUCT PATHS.
```

| Kind | Store in Git | Notes |
| --- | --- | --- |
| Source code | yes | runtime + tests |
| Small manifests / STATUS.json / SHA256SUMS | yes | evidence index |
| Huge generated corpora / raw jsonl transcripts | no (future additions) | release artifact, LFS, or external archive; keep hashes in Git |
| Model weights | no | Hugging Face / local disk |
| Secrets | never | host-side only |

Canonical repo already contains large historical JSONL. Leave it. Do not add more to product paths (`README`, `beastbox/`, `QUANTUM_BEAST_STARTER/`, `tests/` product suites).

Physical repository split is **FUTURE OPTIONAL REPOSITORY TOPOLOGY**, not a current release blocker.
