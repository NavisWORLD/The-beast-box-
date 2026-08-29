# Experimental Engineering / Research Logs

This directory is the chronological public notebook for Beast Box experimental development.

The purpose is not to turn every development thought into a claim. The purpose is to make the engineering trajectory inspectable: what question was being tested, what exact branch/run was used, what failed, what was fixed, what remained null or inconclusive, and what evidence was preserved.

## Log format

Future entries should record, where applicable:

1. date and experiment name;
2. objective;
3. starting branch/commit and scientific anchor;
4. source/provenance state;
5. preregistration or frozen protocol identity;
6. execution path;
7. failures and debugging changes;
8. tests / CI / package / security results;
9. measured outcome;
10. conservative classification;
11. explicit non-claims;
12. exact links or hashes needed to reproduce the state.

Failures, nulls, missing evidence, and negative controls should remain in the public history.

## Entries

- [`2026-08-29-v0.3.2-public-surface-hardening.md`](2026-08-29-v0.3.2-public-surface-hardening.md) — product-surface hardening on live main, CI restoration after PR #43, isolated wheel/source install proofs, and owner-gated remaining decisions. Not a scientific rewrite.
- [`2026-08-29-soul-qbt-final-closed-loop.md`](2026-08-29-soul-qbt-final-closed-loop.md) — recovered historical IBM/QBT provenance, froze the admissible-source boundary, proved the synthetic harness, sealed the historical source gap, fixed CI ancestry/idempotence, and completed the final green closure.
