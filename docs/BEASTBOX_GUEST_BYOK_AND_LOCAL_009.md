# Public Guest Lab — staged implementation (009)

## Exact guest contract

Public route: `/try` on the existing Beast Box frontend, with two explicit options.

**RAWRPHØS · Local CPU** (Cory's existing Railway resource): frontend POST `/api/guest` forwards through the server-held `BEASTBOX_CLOUD_BRIDGE_TOKEN` only to a fixed `/api/guest-local` route on the same owner bridge host. That route is not part of the owner-session BFF allowlist, and its own private host bearer is mandatory. The guest handler calls **only** private `127.0.0.1:8767` pinned 14K inference, with bounded 700-character input and 64 output tokens, after checking the SHA and actual model readiness. It does not use `CosmicApp`, `DurableRuntime`, the user's selected provider, memory, tools, sensors, Azure, or any remote-model credential. Owner chat and guest chat share a CPU and are serialized with an explicit busy response; an owner job already in flight takes priority. A temporary, separate SQLite guest-access DB on the existing durable volume holds **quota counters and anonymous HMAC identity digests only**, never messages, raw IP addresses, tokens or model replies.

**Hugging Face · Guest BYOK**: user enters their own API token in a password input and model ID; after separately approving possible charges the browser sends them over HTTPS to the frontend Next.js API, which uses only the fixed `https://router.huggingface.co/v1/chat/completions` endpoint. It does not read or use the owner HF key/vault and does not fall back to the owner's account. The form clears the key immediately after submission. Application code does not persist or log it, but it transits the website's server and Hugging Face; users should supply a least-privilege token with their own usage limits. Model access and cost depend on their HF account. No HF token is saved into COSMOS memory or guest storage.

## Fail-closed limits and owner approval

`BEASTBOX_GUEST_LOCAL_ENABLED=no` by default. Before enabling on Railway, verify live frontend production assignment and a real guest prompt; do not expose an owner API key. Local default caps: **5 requests per guest per UTC day, 30 globally per UTC day, 300 per 30-day trial, one guest CPU request at a time**. They can be lowered/raised by explicit owner host configuration: `BEASTBOX_GUEST_PER_CLIENT_DAILY_MAX` (1–100), `BEASTBOX_GUEST_DAILY_MAX` (1–500), `BEASTBOX_GUEST_TOTAL_MAX` (1–5000). SQLite transactions atomically reserve a slot, and exhausted or expired trials fail closed. Quota is counted at admission, including timeouts. An active reservation expires after 180 seconds if a process dies. On one service instance a separate owner gate prevents intentional chat concurrency, but public access may still compete for CPU with administrative/health work; a separately scaled guest service is recommended before heavy traffic.

Current quota identity derives from a Vercel-supplied forwarding header and a host HMAC secret. It is only a best-effort **per-client limiter**, not authentication or a guarantee of a distinct person (NAT/proxies can share limits and clients may change apparent IP). The persistent **global cap** is authoritative. Neither anonymous visitors nor a publicly posted provider key receives an unlimited privilege.

**Important:** Connecting the website to the domain does not automatically promote a ready Preview deployment. Vercel production, iPhone mobile testing and Railway image completion require independent verification before telling visitors guest chat is live. This stage does not install 19K/20K research weights and does not grant public use of owner COSMOS memory or paid provider tokens. No extra paid plan or hosting service is created.

## Live acceptance

- GET /try on the actual custom-domain production deployment; switch choices and verify password field, mobile viewport and no browser persistence.
- Anonymous POST /api/guest reject cross-origin, large requests, malformed model/key. Wrong HF token reports failure without echoing it. Actual guest HF inference only on explicit account consent; no owner key reads.
- Public local disabled until `BEASTBOX_GUEST_LOCAL_ENABLED=yes`. With enabled: verify 14K checkpoint hash, one actual local non-mocked response, quota and busy denial, explicit host bearer denial, no owner checkpoint or memory changes, no cloud provider selection, and 30-day expiry.
- Keep private owner chat regression and production rollback readiness. `BEASTBOX_GUEST_LOCAL_ENABLED=no` is the emergency kill switch; if service reconfigures, recheck that the model and private volume remain unchanged.
