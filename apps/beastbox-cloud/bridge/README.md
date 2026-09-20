# Owner-only durable Beast Box bridge

This adapter runs the original `beastbox.cosmic_web.CosmicApp` directly, with its real SQLite-backed `DurableRuntime`. It is NOT a replacement for the existing COSMIC application and must NOT run inside an ephemeral Vercel Function.

## Deploy only on durable owner-controlled compute

Provision a persistent Linux VM or container platform with a durable mounted data volume, TLS, restricted inbound firewall, authentication and backup. Install the original Beast Box repo (Python 3.10-3.12, `pip install .`) on that host. Pre-create a stable non-symlink directory, e.g. `/srv/beastbox/data`, on the persistent volume.

Choose a random bridge credential length >=32 and store it in the host environment as `BEASTBOX_CLOUD_BRIDGE_TOKEN` (never in source, logs or chat). Run:

  python apps/beastbox-cloud/bridge/owner_bridge.py --data-dir /srv/beastbox/data --port 11521

The bridge **only** binds to 127.0.0.1. Terminate HTTPS using a trusted reverse proxy, forward only the Vercel server-side BFF to local port 11521, and keep that port firewalled from the public Internet. Protect your TLS/proxy installation separately. Configure Vercel Preview's private `BEASTBOX_CLOUD_BRIDGE_URL` to the exact HTTPS origin and `BEASTBOX_CLOUD_BRIDGE_TOKEN` to the same service token; never send either credential to the browser.

Before attempting a real provider call, choose an actual installed model and configure the host's provider profile and authority according to docs/COSMIC_UI_GUIDE.md. The default reference fixture is **not** trained inference; label it honestly. Changing provider must revoke prior authority. This bridge exposes only GET orbit/memory/trace/provider/conversation/storage/context and POST chat/context, and rejects arbitrary tools, filesystem, authority changes and provider configuration.

## Verification and restrictions

Run `PYTHONPATH=. python -m unittest discover -s apps/beastbox-cloud/bridge/tests -v` at the repo root. The fixture verifies bearer rejection, route allowlist, genuine reference-runtime chat transaction, checkpoint and system ID preservation across fresh CosmicApp instances. It does NOT certify remote TLS, identity/permissions for many users, production storage, paid provider operation, image parsing or production security.

Owner-only preview. For multi-user access, implement separate tenant data roots and verified per-object ownership, a real identity provider, session revocation, rate limits, private storage and independent security review. Never deploy the current bridge as a shared public chat server.

## Explicit Hugging Face cloud inference (persistent host only)

The existing `CompatibleChatProvider` already speaks the official OpenAI-compatible Hugging Face Inference Providers API at `https://router.huggingface.co/v1`. The owner bridge now supports a **single explicitly approved startup model**. On the durable host, set `BEASTBOX_HF_MODEL_ID` to an explicitly selected supported chat model, `BEASTBOX_HF_BILLING_APPROVED=yes` only after reviewing the model's applicable billing, and `HF_TOKEN` to a fine-grained token with Inference Providers permission. Do not put these values in the browser or Vercel frontend.

The host refuses startup when approval or the token is missing and refuses to overwrite an existing provider profile. Only this exact HF router endpoint is configured by the host bootstrap; chat clients cannot submit arbitrary URLs or API-key environment variable names. The normal provider handoff revokes previous tool authority, including cloud. Real inference is **not verified** until the durable service is hosted and an authenticated request receives an actual response. Existing PHOS checkpoints are not compatible chat providers by assumption.

For Vercel configure `BEASTBOX_CLOUD_BRIDGE_URL` and `BEASTBOX_CLOUD_BRIDGE_TOKEN` only after an independently protected TLS ingress to the real persistent host is ready. Keep model tokens on that host; client routes accept temporary context and bounded chat inputs only. Backend service costs require separate explicit approval. There is no production-grade multi-user identity or spending cap in this owner preview.
