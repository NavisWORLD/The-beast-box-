# Security scope

No production runtime, permissions, tool dispatch, state ledger or model checkpoint changed. `cst_candidate` imports only Python's standard library and exposes pure numeric functions; it does not read files, use credentials or perform network/host actions. Invalid/nonfinite inputs fail closed; raw history remains separated. Historical evidence files and shared data must not be writable by experimental services. Clone-level separation **does not** isolate processes, credentials, devices or shared paths automatically; run with a dedicated data directory, least privilege, and no production secrets.

Not run: host-side authority denial suite, full protected-memory hash comparison, sandbox escape testing, live IBM/device security, real model A→B→A continuity on the candidate. Existing historical reports remain historical only. No security certification implied.
