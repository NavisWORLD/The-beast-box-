# Finisher E — bounded reviewed-feedback control, not demonstrated adaptive superiority

`beastbox/adaptive_control.py` is an **isolated software evaluation
harness**, not an auto-enabled production behavior. It takes frozen,
existing R12/lexical/Hebbian/integrity/recency score components, accepts
explicit reviewed preference labels, and stages bounded convex-weight
updates only on training queries. Evaluation requires disjoint held-out
queries and reports fixed-versus-adapted mean reciprocal rank (MRR).
The existing historical R12 implementation and frozen measurements are
never modified, and language-model weights never change.

`tests/test_finisher_adaptive_control.py` uses labeled synthetic fixtures
to test parameter validity, trial isolation, nonmutation of source stores,
held-out query leakage denial, deterministic reproducibility and numerical
reporting. Any observed MRR delta applies **only to that declared fixture**.
No general improvement, new model training, scientific adaptation,
consciousness, quantum advantage or biological learning is inferred.

Full Phase E still requires separately preregistered real representative
corpora, adjudicated/reviewed labels, fixed/adaptive/shuffled/zero-state
ablations, repeated seeds, 500/5k/50k latency and withheld final evaluation,
explicit integration safety under model swap, and stable signed receipts.
Results cannot be called superior until those studies actually pass.
