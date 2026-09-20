# BEAST BOX // COSMIC CHAOS 🌌

**Owner:** Cory Davis / NavisWORLD. **Scope:** isolated Vercel frontend, NOT a new Beast Box runtime.

This app resides in apps/beastbox-cloud/. It is an owner-gated responsive frontend for the existing beastbox/cosmic_web.py API contract. BRAIN, ORBIT, BRAIN BAY, MEMORY VAULT, SYNAPSE TRACE, FILES, AUTHORITY and SETTINGS display actual backend data when available. No fake model responses or memory.

## Existing backend boundary
The original CosmicHTTPServer is loopback-only with an X-Beast-Session process token. Never expose that server directly to the Internet, leak its token to browsers, or use Vercel ephemeral filesystem as the persistent SQLite substrate.
The separate durable HTTPS bridge is NOT currently provisioned. It must authenticate the fixed BFF bearer credential, map to an owner-isolated persistent runtime and preserve all existing authority and checkpoint behavior. Setting a URL is not proof of integration. This repo does not yet contain an independently audited cloud bridge.

## Development
From apps/beastbox-cloud/: npm install; npm run test; npm run typecheck; npm run build; npm run dev. No credentials are required to compile; without credentials owner access fails closed.

## Correct Vercel setup
Import the GitHub repo with Framework Preset Next.js and **Root Directory: apps/beastbox-cloud**. Deploy a protected PRIVATE PREVIEW. Do not set an arbitrary Python entrypoint, and do not deploy the repository root.
Set BEASTBOX_OWNER_PASSWORD and BEASTBOX_CLOUD_AUTH_SECRET (random secret length >=32) as private Preview environment variables. Only after the durable bridge is deployed, add BEASTBOX_CLOUD_BRIDGE_URL (fixed HTTPS origin) and BEASTBOX_CLOUD_BRIDGE_TOKEN (scoped secret). Never commit or print secrets.

## Honesty boundaries
- Owner login: HMAC-signed HttpOnly SameSite Strict 8-hour cookie; must add rate limits, revocation, an identity provider and security review before opening multi-user signups.
- BFF: owner-authenticated allowlisted JSON requests for orbit, memory, trace, provider, conversation, storage, context and chat. The original backend returns JSON, not streaming.
- Chat: real backend responds via /api/chat and durable /api/conversation. If absent, send is disabled; no mock.
- Text/code attachments: local staging; on send, forward owner-selected text to temporary context where the verified bridge exists. PDFs and photos are preview/staging ONLY. No claim of parsing, durable upload or vision inference until storage, ownership and model support are integrated.
- BRAIN BAY provider settings read-only; cloud model swaps and tool authority unavailable until separately secured.
- Cloud persistence, export/import, private object storage, image processing, remote PHOS, billing and multi-user isolation are NOT implemented. Runtime code, licensed assets and historical receipts remain unchanged.

MODEL ≠ MEMORY · MODEL ≠ STATE · MODEL ≠ PROVENANCE · MODEL ≠ AUTHORITY.

## Release gate
CI runs isolated preflight, TypeScript and Next build. Browser/iPhone acceptance, authenticated bridge, durable restart, attachment security and real inference still require independent validation. Do not merge unfinished work or fabricate a Vercel URL.

## Redeploying the correct branch after changing Preview secrets

Vercel's **production** branch remains `main`, and this isolated web folder does not yet exist there. Changing the project Root Directory to `apps/beastbox-cloud` therefore makes a redeployment of `main` fail with `The specified Root Directory does not exist`. This is unrelated to the owner password. Do **not** redeploy the latest `main` build or change the Root Directory back to the Python monorepo.

After storing `BEASTBOX_OWNER_PASSWORD` and `BEASTBOX_CLOUD_AUTH_SECRET` under **Preview**, deploy a fresh commit from `feature/cosmic-chaos-vercel-app-001` and verify that the Vercel deployment **Source** is this feature branch—not `main`. Check its `/api/session` response for `configured: true` using an authorized browser session, without printing the secret. If that value is false, inspect the Preview variable scope and redeploy the correct feature branch again. Do not merge into main or promote the private preview to public production until backend and security gates pass.

## September 2026 cloud recovery notes

The verified feature-branch deployment is a *protected Preview*, not the Python `main` branch. Missing credentials on its login screen are diagnosed by **missing key names only** through `/api/session`; secret values, lengths and hashes remain private. A variable added to Vercel Production does not provision Preview. After correcting Preview scope create a **new feature-branch deployment**; do not redeploy `main`, change valid DNS, or commit secrets.

The cloud bridge supports a guarded host-only Hugging Face compatible provider bootstrap; it is not a live Hugging Face test. The connection to HF account `phera-ra` grants read-repos/jobs but does not itself authorize paid inference. Azure private Blob storage, IBM live Quantum, hosted compute, cloud GGUF conversion and all related end-to-end tests remain unprovisioned. The original portable substrate `beastbox/portable_state.py` already supports verified state export/import but is not yet exposed as a safe cloud download. Do not confuse this archive with model weights or a compatible GGUF. Reference fixture chat is disabled on the browser UI so users cannot mistake it for trained inference.
