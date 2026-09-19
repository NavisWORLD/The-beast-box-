# Security scope

No production runtime, permissions, tool dispatch, state ledger or model checkpoint changed. `cst_candidate` imports only Python's standard library and exposes pure numeric functions; it does not read files, use credentials or perform network/host actions. Invalid/nonfinite inputs fail closed; raw history remains separated. Historical evidence files and shared data must not be writable by experimental services. Clone-level separation **does not** isolate processes, credentials, devices or shared paths automatically; run with a dedicated data directory, least privilege, and no production secrets.

Not run: host-side authority denial suite, full protected-memory hash comparison, sandbox escape testing, live IBM/device security, real model A→B→A continuity on the candidate. Existing historical reports remain historical only. No security certification implied.

## Source snapshot evidence and reference launcher

The independent candidate's original source evidence is compared to the frozen `8f90e440f0f4ceba502b1a3f8637507491fb23b0` Git blob inventory; the original root evidence must also pass its previous historical-anchor check. The candidate launcher validates a dedicated direct-child data path, rejects a symlink data root, passes a minimal non-secret environment, and enables only the reference provider and init/chat/inspect actions. These controls are software checks, not a credential-independent VM or OS sandbox. The full copied-suite and checked receipt passed on the identified CI run, while privileged/real-service threat modeling and live actuator tests remain unexecuted.

## Latest executed guard checks

At `bb5345e854b9897aaa2612bd1e5904de9bb995b8`, Python 3.10 and 3.12 copied suites passed 1,131 tests each; the guarded reference-only continuity script passed all nine structural checks on both versions, and the exact source evidence receipt guard passed. This is bounded software source validation. It is not a claim that general copied launchers cannot reach the host or that private data cannot leak under an adversarial host. Keep access to production stores and credentials denied in real deployments.
