# Cloud Beast Box: durable owner bridge hosting

**Status:** this is a deployment runbook, **not** evidence of an existing hosted service.
The current Vercel owner UI is functional, but chat remains disabled until the
original Python `CosmicApp` is running on persistent compute, serving the
authenticated owner bridge, and an actual supported model answers a request.

## Dependencies / owner approvals (do not provision automatically)

- An owner-controlled Linux VM or persistent equivalent with a mounted durable
  filesystem, functioning backups and outbound HTTPS. Azure Blob Storage alone
  does **not** provide the CPU/RAM and persistent runtime required here.
- DNS for a separate bridge hostname (for example,
  `bridge.beastboxcosmos.xyz`), trusted HTTPS certificate and ingress controls.
  Preserve the Vercel frontend DNS entry `beastboxcosmos.xyz`; do not repoint it.
- A random `BEASTBOX_CLOUD_BRIDGE_TOKEN` of at least 32 characters, configured
  *identically* on the VM and Vercel Preview, never in Git, logs or messages.
- For HF inference only: a separate permitted `HF_TOKEN`, reviewed
  `BEASTBOX_HF_MODEL_ID`, and affirmative
  `BEASTBOX_HF_BILLING_APPROVED=yes` after inspecting model charges.
  Default reference inference is **not** a trained chat model. Do not enter HF
  keys in the browser, use this host as a public multi-user service, or buy
  infrastructure without owner cost approval.

## 1. Host, environment, data

On a security-maintained Linux host, install Python 3.10–3.12, the full pinned
repository revision from PR #84, and all dependencies that the real COSMOS
runtime requires. Run its existing relevant tests; do not replace it with a toy
API. Mount persistent storage at `/srv/beastbox/data`, create a dedicated
`beastbox` system user, and grant that user exclusive directory access.
Keep this state volume outside container/OS ephemeral storage and back it up.
Do not clone in `/tmp` or store the SQLite DB in a Vercel Function.

Create a root-owned file `/etc/beastbox/bridge.env`, mode `0600`, containing
the token and any model configuration. Example **names only** (not values):

```dotenv
BEASTBOX_CLOUD_BRIDGE_TOKEN=
# On the persistent host only, when model spending is approved:
# BEASTBOX_HF_MODEL_ID=
# BEASTBOX_HF_BILLING_APPROVED=yes
# HF_TOKEN=
```

The owner bridge rejects missing/weak bearer values and invalid HF setup.
Existing provider profiles cannot be overwritten by a host env toggle.
If the chosen model changes, use the existing audited provider-change
workflow and reauthorize explicitly, rather than silently mutating state.

## 2. Run only on loopback

Use a hardened system service running as `beastbox`, with its exact installed
Python interpreter. Example systemd unit (**adapt interpreter path to host**):

```ini
[Unit]
Description=Beast Box durable owner bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=beastbox
Group=beastbox
WorkingDirectory=/opt/beastbox/repo
EnvironmentFile=/etc/beastbox/bridge.env
ExecStart=/opt/beastbox/venv/bin/python apps/beastbox-cloud/bridge/owner_bridge.py --data-dir /srv/beastbox/data --port 11521
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/srv/beastbox/data
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
```

Before exposing a network endpoint, verify the process binds **only**
`127.0.0.1:11521`, has read/write permissions on the durable volume,
rejects a request without Bearer authentication, returns valid `/api/orbit`
and `/api/provider` for the authorized owner, and survives a restart with
the **same** system ID and checkpoint.

## 3. TLS ingress and Vercel BFF

Place a trusted TLS-terminating proxy on the host in front of the loopback
bridge; allow only the required `/api/` paths, disallow arbitrary CORS and
restrict ingress where possible. Consider Azure NSGs, WAF, audited rate limits
and monitoring. Never forward the original COSMOS loopback web service itself
to the public network; only the restricted authenticated owner bridge may be
proxied. Never expose port 11521 publicly.

In Vercel project `zerefs-end/the-beast-box`, set these **private Preview**
variables for `feature/cosmic-chaos-vercel-app-001`:

```dotenv
BEASTBOX_CLOUD_BRIDGE_URL=https://YOUR-VERIFIED-TLS-BRIDGE-HOST
BEASTBOX_CLOUD_BRIDGE_TOKEN=THE-SAME-PRIVATE-OWNER-BRIDGE-TOKEN
```

Do **not** change `BEASTBOX_OWNER_PASSWORD` or
`BEASTBOX_CLOUD_AUTH_SECRET` to the bridge token. They serve different
authentication purposes.

Trigger a fresh deployment from the *feature branch*; do not redeploy `main`
or a fruit-fly experiment branch. Do not repoint the valid DNS of
`beastboxcosmos.xyz`. Once logged in, inspect owner-only `/api/status`:

- `BRIDGE_SETTINGS_MISSING`: one or both Vercel bridge settings not present.
- `BRIDGE_UNREACHABLE`: DNS, TLS, firewall, proxy or host/network failure.
- `BRIDGE_AUTH_REJECTED`: host and Vercel bridge token differ.
- `BRIDGE_BAD_RESPONSE`: server does not implement the COSMOS contract.
- `REFERENCE_ONLY`: durable bridge works, but model is a deterministic fixture.
- `MODEL_PROFILE_CONFIGURED_NOT_ATTESTED`: genuine provider is configured
  but a real inference turn remains to be tested.

Never disclose secrets or raw owner records while troubleshooting.

## 4. Acceptance and non-claims

From the owner-authenticated deployed BRAIN, verify an actual model turn and
record its provider, revision, latency and output; then refresh, restart the
backend, and confirm history, checkpoint and memory remain consistent. Verify
failed authentication is rejected, and repeat with a genuinely separate model
only after explicit authority revocation/reauthorization. Backups and recovery
must be exercised on an isolated test volume.

Azure private attachment storage, IBM live hardware workloads, GGUF conversion,
hosted PHOS weights, multi-user auth and a public production release remain
separate projects and are NOT automatically enabled by this runbook.
