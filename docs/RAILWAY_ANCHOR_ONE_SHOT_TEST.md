# Isolated Railway anchor-process smoke (one-shot; not independent authority)

Owner approved live testing under the existing Railway account, NOT mutation
of the existing COSMOS production service. Use only the separate private
Beast Box anchor acceptance lab project, separate service, no shared volume,
no public domain or copied secrets, restart policy NEVER.

The first exact-branch run on
`93ce2ec1c835c8f2696c7c0643d5cf93b34a2d95`
executed the selected tests with pytest exit code 0, but the receipt was
incorrectly marked failed because double quiet settings omitted the
stdout summary. That discrepancy is preserved in Railway deployment logs
for the original one-shot run; do not claim the original receipt succeeded.

This revision overrides inherited pytest quiet settings and parses an
actual, temporary pytest JUnit XML result, with separate parser regressions.
The original runtime source baseline remains
`c91072270c38c2ec86ee5cc06579d8276d779e89`.

The experimental live Railway check exercises local CA-authenticated HTTPS,
bearer denial, strict CAS and process restart, coherent rollback detection,
and synthetic semantic memory privacy/concurrency boundaries. The TLS
authority process shares the same Railway container and OS principal as the
client and is NOT independently administered. This does not meet full
Phase A production custody, off-host backups or Phase B real-model quality.
Do not merge this branch's root Dockerfile to main.
