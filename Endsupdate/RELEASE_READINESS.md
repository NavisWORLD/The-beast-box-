# Release decision — HOLD

Snapshot and isolated math module exist; source copy is not an independently validated next-generation product. Do **not** merge into `main` or set `corrected` as a runtime default. The corrected candidate changes unit handling and regularizes a singularity, but its information contribution is numerically absent from the binary64 score on this synthetic experiment. No reason has been established to alter dyn12, memory, model weights or policy.

PASS (locally): 10 numerical unit tests, synthetic experiment JSON generation. VERIFY ON GITHUB: reproducible run output and file hashes, full copied test suite. NOT RUN: product model A/B task suite, full A→B→A with new candidate, installation across platforms, optional services/devices/hardware, performance, security gate and actual feature-flag adapter (physically unjustified). No CI or PR result is presumed unless separately observed.

## Follow-up checkpoint

The second math commit adds a source-level 11D comparison, masked-signal observability, and a copied-suite CI matrix. A reference-only local launcher was subsequently introduced to exercise a dedicated, separate state directory without forwarding service credentials. Mathematical unit tests and independent numerical CI pass; these do not establish A/B predictive benefit. Do not promote the candidate solely because packaging and copied-source regression checks pass. The model-level A→B→A, client UI, optional hardware, authorization and real-service gates remain blocked/unrun.
