# Optional independently hosted HTTPS anchor (Finisher A)

This follow-on module implements the protocol for a true **separate-process,
CA-authenticated HTTPS** \`ContinuityAnchor\`. It provides a bounded
\`HTTPSAnchorClient\` and an isolated TLS server
(\`python -m beastbox.anchor_service\`) that stores monotonic SQLite CAS
receipts in the **server's** filesystem, not the client's runtime database.

## Operational boundary (mandatory, not faked by CI)

The server **must** be provisioned under an independently administered
user/host whose SQLite database, TLS private key, token file and backups
cannot be rewritten by the Beast Box runtime principal. Each runtime client
must pin the correct server CA and carry a separately provisioned 32+ byte
bearer token. On the host, keep private key and token file mode 0600
where POSIX is available; never commit them, print them or put them into
model prompts, state receipts, app variables accessible to guest users or
public artifacts. Prefer mTLS client certs in addition to the bearer token
when the operator has a certificate authority.

Command for an **already privately provisioned** host (not an instruction to
generate fake credentials or spend money):

\`\`\`bash
python -m beastbox.anchor_service \
  --db /private-operator/authority.sqlite3 \
  --cert /private-operator/tls-server-public.pem \
  --key /private-operator/tls-server-private.key \
  --token-file /private-operator/owner-bearer-token \
  --bind 127.0.0.1 --port 8443
\`\`\`

Remote access requires explicit \`--allow-network\` plus independently
configured firewall/TLS/identity/availability protections. The server uses
strict bounded JSON and one CAS transaction per request; it cannot silently
reset an existing authority. An operator must retain off-host backups and
document stale-CAS/recovery procedures. Use the already verified runtime's
\`DurableRuntime(anchor_authority=HTTPSAnchorClient(...))\` constructor.
Do **not** retroactively autoenroll an existing local runtime: its historical
latest receipt could already have been maliciously rewritten.

## Evidence and limitations

\`tests/test_finisher_remote_anchor.py\` creates ephemeral private CA/leaf
certificates and a test-only API token in a temporary directory, starts the
actual server in a distinct subprocess, checks CA-validated requests,
unauthorized denial, strict schema, stale CAS, service restart and full
coherent local SQLite rollback with a separately retained server witness.
These tests **run as the same CI OS principal** and do not establish actual
independently administered filesystem/host custody or production availability.
No production server or credentials were created or deployed, and no
historical experimental measurements change. External service operation,
secure backups, authenticated owners and additional cross-host/partition
recovery tests remain genuine Phase A release gates.
