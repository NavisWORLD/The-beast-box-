# RAILWAY SAME-ACCOUNT ONE-SHOT AUTHORITY ACCEPTANCE PROBE (EXPERIMENTAL)

This is **not** a deployment of the production Beast Box or independently
administered external trust authority. The owner explicitly allowed a
controlled test on their existing Railway account. Run this exact isolated
experimental branch in a **new private Railway project** using a separate
one-shot service with no public domain, no shared volume, no copied secrets,
restart policy NEVER and no touching the existing COSMOS production project.

Its root Dockerfile intentionally overrides the normal production root
Dockerfile **on this disposable branch only**. Do not merge this Dockerfile
to main or point the existing production service to this branch.

The container runs existing real HTTP+TLS, separate-process restart,
monotonic CAS, authenticated denial, rollback-detection and bounded opt-in
semantic privacy/concurrency tests. It emits one structured **observed**
receipt in Railway deploy logs, returns an error on failure, and exits
successfully after completion. Exact source parent:
`c91072270c38c2ec86ee5cc06579d8276d779e89`.

**Crucial security distinction:** client and authority subprocess run
in one temporary Railway container under the same account/OS principal,
so these checks prove behavior on Railway's actual host, not an independent
separate-service, separate-admin or off-host authority. A separate production
trust root, independent owner custody, backup/restore across failures,
representative retrieval testing and other issue #132 requirements remain
open. Temporary short-lived Railway compute can incur usage charges.
