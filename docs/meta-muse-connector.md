# Beast Box connector for Meta Muse

Beast Box exposes one paired virtual pet (a "beast") to **Meta Muse**, Meta's personal AI agent
(muse.ai), and to any other MCP client. It is an MCP server over **Streamable HTTP** at
`https://<beast-box-domain>/api/mcp`. This document covers setup, every tool, permissions,
side effects, errors, rate limits and data handling. It is written to double as the
documentation the Muse Connector Platform asks for. This connector has nothing to do with the
Muse EEG headband.

> **Status.** Beast Box has **not** been submitted to Meta. The Muse app lists connectors under
> *Settings > Connectors* only after Meta reviews and approves them, which needs the owner's
> business verification and a test account. Until then, connect with **Muse Code** (below) or any
> MCP client.

## 1. How the pieces fit

| Piece | Where |
| --- | --- |
| MCP endpoint (stateless Streamable HTTP, JSON responses) | `POST /api/mcp` |
| MCP Server Card (v1, `application/mcp-server-card+json`) | `GET /api/mcp/server-card` (and `?device=<id>` for one paired device) |
| AI Catalog (domain discovery entrypoint) | `GET /.well-known/ai-catalog.json`, alias `GET /.well-known/mcp/catalog.json` |
| Server Card at older draft paths | `GET /.well-known/mcp.json`, `GET /.well-known/mcp-server-card` |
| OAuth protected resource metadata (RFC 9728) | `GET /.well-known/oauth-protected-resource/api/mcp` (also without the suffix) |
| OAuth authorization server metadata (RFC 8414) | `GET /.well-known/oauth-authorization-server` |
| Dynamic client registration (RFC 7591) | `POST /api/muse/oauth/register` |
| Authorization (consent) page | `GET /connect/meta-muse` (form posts to `/api/muse/oauth/authorize`) |
| Token endpoint (authorization_code + PKCE S256, refresh_token rotation) | `POST /api/muse/oauth/token` |
| Revocation (RFC 7009) | `POST /api/muse/oauth/revoke` |
| One-tap pairing landing page (QR code target) | `GET /connect/meta-muse/pair#connector=…&code=…&device=…` |
| Browser-only device routes (same-origin, device secret) | `/api/muse/link`, `/code`, `/sync`, `/pat`, `/device`, `/grant`, `/storage` |

Code: `apps/beastbox-cloud/lib/muse/` (`auth.mjs`, `tools.mjs`, `store.mjs`, `rate-limit.mjs`,
`snapshot.mjs`, `discovery.mjs`, `pairing-link.mjs`, `bridge-talk.mjs`), routes under
`apps/beastbox-cloud/app/`, UI in `components/meta-muse-*.tsx`.

### Where the beast lives

The beast is saved **in the owner's browser** (localStorage `beastbox-companion-session-v1`).
Nothing is shared until the owner opens **Pair with Meta Muse** and ticks the consent box. Then
the browser:

1. creates a pairing on the server and keeps a device secret (`bbm_dev_…`) in localStorage
   (`beastbox-muse-link-v1`; it never leaves that browser except to Beast Box's own `/api/muse/*`);
2. pushes a **minimal snapshot** about every 20 s while the page is open, and a few seconds after
   any local care change;
3. pulls back care actions Muse made and applies them with the same rules the cage uses, then
   acknowledges them.

Read tools answer from the last synced snapshot (each answer carries `last_synced_at`). Write tools
update the connector copy immediately and queue the action; the beast in the browser changes on
its next sync. If the owner switches to a different beast before syncing, queued actions for the
old beast are dropped, not applied to the new one.

## 2. Setup

### 2.1 Storage (required in production)

The connector needs a Redis REST store. Production without one answers `503
storage_not_configured` and the Pair panel says so; nothing is faked.

* Vercel: *Storage → Marketplace → Upstash for Redis*, connect it to the project. That sets
  `KV_REST_API_URL` and `KV_REST_API_TOKEN`.
* Or set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.

`next dev` and tests use an in-memory store; it is never used in production.

`talk_to_beast` additionally needs the existing guest model host (`BEASTBOX_CLOUD_BRIDGE_URL`,
`BEASTBOX_CLOUD_BRIDGE_TOKEN`, `BEASTBOX_CLOUD_AUTH_SECRET`). Without it the tool returns
`companion_unavailable` and invents nothing.

### 2.2 Make the endpoint reachable

Meta Muse calls the connector from Meta's servers, so `/api/mcp`, the `/.well-known/*` documents
and `/connect/meta-muse` must be publicly reachable. Vercel Deployment Protection is **not
path-based**: `vercel.json` cannot exempt one route, Deployment Protection Exceptions apply to
preview domains only, and the OPTIONS Allowlist only covers CORS preflight. The owner's choices:

* **Recommended:** *Project → Settings → Deployment Protection → Vercel Authentication* set to
  **Standard Protection** (protects previews, leaves the production domain public). Owner pages
  stay behind the Beast Box owner login, and the connector has its own OAuth.
* **Muse Code only:** enable *Protection Bypass for Automation* and add its secret as an
  `x-vercel-protection-bypass` header in the Muse Code snippet. This does not help the Muse app,
  which cannot send that header.

### 2.3 Pair from Beast Box

Open Beast Box → owner deck **META MUSE** (next to LOST COSMOS), or `/beast-cage/go` → **Menu →
Pair with Meta Muse** (also in **Settings**, and linked from the Brain Bay companion card).

1. Check the device name (default `Beast Box · <beast name>`; it appears in the server card and as
   the MCP server title).
2. Tick the consent box and press **Pair this beast**.
3. Then either:
   * **Muse app / any OAuth MCP client:** press **Show pairing code**. The panel shows a one-time
     code (`XXXX-XXXX`, 10 minutes, single use), a QR code and a one-tap link. When the client
     opens the Beast Box consent page, type the code and choose **Read only** or **Read + care
     actions**.
   * **Muse Code:** choose Read only or Read + care actions, press **Make token**, and copy the
     snippet:

```json
{
  "mcp_servers": {
    "beastbox": {
      "transport": "streamable_http",
      "url": "https://<beast-box-domain>/api/mcp",
      "headers": { "Authorization": "Bearer <Beast Box token>" },
      "mode": "optional"
    }
  }
}
```

The panel shows connection status, each connection (OAuth client or token) with its access level
and last use, last activity, last sync, pending actions, **Revoke** per connection and **Unpair**.
Unpair revokes every token, removes the device link and deletes the server copy.

### 2.4 Discovery: what can and cannot find this device

A client given only the site's base URL can find everything by standard discovery:
`/.well-known/ai-catalog.json` → Server Card → `remotes[0].url` (`/api/mcp`) → `401` with
`WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource/api/mcp"` →
authorization server metadata → `registration_endpoint` (RFC 7591) → consent page → token. The
MCP SDK's `discoverOAuthServerInfo` and `registerClient` work against it (tested).

**Meta Muse does not discover third-party devices on its own.** Meta has no public API for
third-party device discovery or pairing in Muse; only Meta hardware pairs that way. Beast Box does
not pretend otherwise. The QR code and one-tap link only carry the connector URL, the device id and
the pairing code to the phone where Muse runs. The code rides in the URL **#fragment**, which
browsers do not send to servers, and the landing page only ever shows this site's own connector.
Pairing paths are listed in one registry (`PAIRING_METHODS` in `lib/muse/discovery.mjs`) with
`meta-muse-device-pairing` marked unavailable, so an official Muse device-pairing API can be added
later without touching the MCP server or OAuth code.

## 3. Authorization

* OAuth 2.1 authorization code flow with **PKCE S256 only** (plain is rejected), public clients
  (`token_endpoint_auth_method: none`), exact redirect URI match (https, or http on
  localhost/127.0.0.1/[::1]), `resource` parameter checked against `/api/mcp`.
* Scopes: `beast.read` (Read only) and `beast.care` (Read + care actions; always granted together
  with `beast.read`). The owner's choice on the consent page wins; a client that asked only for
  `beast.read` cannot be given care.
* Tokens: access `bbm_at_…` (1 hour), refresh `bbm_rt_…` (30 days, rotated on use, never widens
  scope), Muse Code token `bbm_pat_…` (180 days). Only SHA-256 hashes are stored. Refresh tokens
  and device secrets are rejected at `/api/mcp`.
* Revocation: `/api/muse/oauth/revoke` (RFC 7009; revoking an access token also revokes its refresh
  token and the reverse), per-connection **Revoke** in the panel, or **Unpair**.
* Each pairing is its own account; a token can only reach the beast of the pairing that issued it.

## 4. Tools

All tool results return `structuredContent` and the same JSON as text. Errors return
`isError: true` with `{ "error": { "code", "message", … } }`. Every result from a paired beast
includes `last_synced_at` and `pending_actions`.

No tool is **Sensitive write**: nothing buys, sends, posts, shares, deletes or contacts anyone.

| Tool | Class | Annotations |
| --- | --- | --- |
| `get_beast` | Read | readOnly, not destructive, idempotent, closed world |
| `get_care_status` | Read | readOnly, not destructive, idempotent, closed world |
| `get_lost_cosmos_progress` | Read | readOnly, not destructive, idempotent, closed world |
| `list_moves` | Read | readOnly, not destructive, idempotent, closed world |
| `feed_beast` | Write | not readOnly, not destructive, not idempotent (use `request_id`) |
| `play_with_beast` | Write | not readOnly, not destructive, not idempotent (use `request_id`) |
| `rename_beast` | Write | not readOnly, not destructive, idempotent |
| `talk_to_beast` | Write | not readOnly, not destructive, not idempotent, open world (calls the companion model host) |

### Read tools (scope `beast.read`)

**`get_beast`** — no input. Output `beast`: `name`, `species` (stage name), `body`, `element`,
`temperament`, `stage` (1-3), `mood`, `stats` (`hp`, `atk`, `def`, `spd`, `spark` for the current
stage) and `seed_provenance` (`seed`, `backend`, `job_id`, `top_state`, `counts_sha256`, `note`).
The note states the beast was seeded from **recorded** IBM Quantum measurement counts saved in Beast
Box and that there is **no live quantum link**. Side effects: none.

**`get_care_status`** — no input. Output `care`: `experience`, `bond` (0-100), `energy` (0-100),
`stage`, `next_stage_at_experience` (40, 120 or null), `mood`, `stage_source`. Side effects: none.

**`get_lost_cosmos_progress`** — no input. Output `lost_cosmos`: `linked_qbeast` (`profile_id`,
`name`, or null), `native_stage`, `field_location`, `training` (`rounds`, `score`),
`cartridge_booted`, `beasts_met`, `note`. In-cartridge story progress and items live in the
emulator's own save and are **not** shared. Side effects: none.

**`list_moves`** — no input. Output `element`, `moves[]` (`name`, `style`, `charge_ms`,
`strike_ms`, `power` 0-1), `note`. Moves are derived from the recorded seed and genome. Side
effects: none.

### Write tools (scope `beast.care`)

With a Read only connection every write tool returns `insufficient_scope` and changes nothing.
Writes change only this beast's care save. Each returns `action` (`id`, `type`, `status`), `care`
(`experience`, `bond`, `energy`, `stage`, `mood`, `name`, `evolved`) and `pending_actions`. Optional
`request_id` (1-64 chars): repeating a call with the same id within 24 h returns the first result
(`repeated_request: true`) instead of acting twice.

**`feed_beast`** — input `{ request_id? }`. Effect: +6 experience, +1 bond, energy -4, may evolve
(non-Lost-Cosmos beasts evolve at 40 and 120 experience).

**`play_with_beast`** — input `{ activity?: "pet" | "spark" (default "pet"), request_id? }`.
Effect: pet +4 experience, +2 bond; spark +3 experience, +1 bond; energy -4.

**`rename_beast`** — input `{ name (1-24 chars), request_id? }`. Keeps letters, digits, spaces and
`. ' -`. Changes the display name only; species and seed stay.

**`talk_to_beast`** — input `{ message (1-400 chars), request_id? }`. Output adds `speaker`
(`<name> (Beast Box game companion)`), `reply`, `model` (`rawrphos-native`) and `label`. The reply
comes from the Beast Box **game companion model** (the RAWRPHØS guest-safe host also used by
`/api/guest`): it gets only the beast's name, place, mood and care numbers, never owner Brain Bay
memory, chat history or sensors, and it is a **game character, not a conscious mind**. The exchange
is added to the beast's chat on the next sync (+3 experience, +1 bond when kid-safe). If the host is
not configured, rate limited or returns an unverified reply, the tool returns
`companion_unavailable` and saves nothing.

### Error codes

| Code | Meaning |
| --- | --- |
| `insufficient_scope` | Read only connection called a write tool. |
| `no_beast` | The paired browser has not synced a beast yet. |
| `not_paired` | The pairing was removed. |
| `invalid_input` | Bad `activity`, empty/invalid `name` or `message`. |
| `rate_limited` | Category limit hit; `retry_after_seconds` included. |
| `sync_backlog` | 50 actions are waiting for the browser; open Beast Box to apply them. |
| `companion_unavailable` | Talk model host missing or did not answer; nothing was saved. |
| `unknown_tool` | Not one of the eight tools. |

HTTP level: `401` + `WWW-Authenticate` (missing/invalid/revoked/expired token), `403` (foreign
`Origin`), `405` (GET/DELETE on `/api/mcp`; the server is stateless and JSON-only), `413` (body over
64 kB), `429` + `Retry-After`, `503 storage_not_configured`.

## 5. Rate limits

Fixed one-minute windows per pairing unless noted (`lib/muse/rate-limit.mjs`):

| Bucket | Limit |
| --- | --- |
| All `/api/mcp` requests | 120 / min |
| Read tool calls | 60 / min |
| Write tool calls (feed, play, rename) | 20 / min |
| `talk_to_beast` | 6 / min |
| OAuth endpoints and per-device server card (per client IP hash) | 30 / min |
| Browser sync | 30 / min |
| New pairings (per client IP hash), pairing codes, tokens | 10 / hour each |

## 6. Data handling

* **Collected:** only the minimal snapshot: beast seed, display name, experience, bond, energy,
  stage, mood, Lost Cosmos profile id/name and native stage, genome traits needed for the tools
  (element, body, island, temperament, glow, stats, stage names, recorded quantum run ids/hash),
  bestiary count, training totals, cartridge booted flag, field location; plus the device name,
  connections (client name, scope, timestamps) and queued actions. **Not collected:** chat history,
  pattern memory, sensors, photos, owner Brain Bay memory, account or contact data.
* **Use:** only to answer this pairing's tool calls. No secondary use, no advertising, **no model
  training**.
* **Isolation:** one account per pairing; tokens resolve to exactly one account.
* **Secrets:** tokens and device secrets are random 256-bit values stored only as SHA-256 hashes,
  never logged and never put in URLs. The pairing code in the one-tap link sits in the #fragment.
  Public documents (server card, catalogs, metadata) contain no secrets.
* **Retention:** a pairing lasts up to 180 days, then the owner pairs again; Unpair deletes
  everything at once. Storage is the owner's Redis REST provider, reached over HTTPS.

## 7. Testing

* Unit: `cd apps/beastbox-cloud && node --test tests/meta-muse.test.mjs` (PKCE, scopes, read-only
  blocks writes, revoked/refresh/expired/unpaired tokens rejected, isolation, rate limits, sync,
  minimal snapshot, tool classes, storage status, companion host verification, discovery documents,
  device name, dynamic client registration, UI wiring).
* End to end with the MCP SDK client over Streamable HTTP (skipped unless a URL is given):
  `BEASTBOX_E2E_URL=http://localhost:3100 node --test tests/meta-muse-e2e.test.mjs`.

## 8. Submitting to the Muse Connector Platform (owner only)

Beast Box has not submitted anything. When the production domain is public and storage is
configured, the owner can submit through the Muse Connector Platform with: connector URL
`https://<domain>/api/mcp`, OAuth metadata URL `https://<domain>/.well-known/oauth-authorization-server`,
scopes `beast.read` / `beast.care`, this document, a test account (a browser with a paired test
beast and a pairing code or token), and Meta's business verification.
