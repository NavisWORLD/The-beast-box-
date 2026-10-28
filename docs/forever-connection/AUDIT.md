# FOREVER CONNECTION — audit (2026-10-28)

Branch: `emeth/forever-connection` from `origin/main` f3ff7ff79.
Order (Cory, 2026-10-28 15:59 CDT): connect everything that exists — Azure, the DB,
the loops, the life signals — "this is forever memory." Refinement (16:00 CDT):
"All the connections software is done, it needs to be connected." So: audit first,
wire what exists, new code only for genuine gaps, every claimed gap evidenced.

Method: every claim below cites a file and line-level behaviour read on this branch.
Nothing here is assumed from the live site; the live site is this code deployed.

## 1. The served mouth and the guest door today

- `apps/beastbox-cloud/app/api/guest/route.ts` — POST /api/guest. For provider
  `rawrphos-local` it accepts EXACTLY the keys `{provider, text}` (sorted-key check,
  "Local guest mode only accepts a message"), text 1–1800 chars. It forwards to the
  bridge as POST `BEASTBOX_CLOUD_BRIDGE_URL/api/guest-local` with body
  `{text, guest_identity}` and the bridge bearer token. `guest_identity` is
  `HMAC-SHA256(secret, forwarded-IP)` and the route's own comment bounds it:
  "only a quota bucket. It grants no access and is never re-used as an owner
  credential or associated with COSMOS owner memory."
- The route verifies the bridge reply before serving it: schema
  `beastbox-guest-local-v1`, model `rawrphos-native`, `step === PIN_STEP`,
  `checkpoint_sha256 === PIN_SHA` (from `lib/rawrphos-public-pin.json`),
  `memory_used === false`, `owner_tools_used === false`,
  `provider_key_shared === false`. It returns `guest_stateless: true`.
  A bridge that ever answered with memory used would be rejected with 502
  ("Unverified guest model response"). Statelessness is enforced site-side,
  not just bridge-side.
- `beastbox/guest_local.py` (the bridge's guest path, imported by
  `apps/beastbox-cloud/bridge/owner_bridge.py` line 41, dispatched at line 781):
  - Line 133: the payload key set must be exactly `{"text", "guest_identity"}`,
    otherwise 400. **The bridge contract accepts no context, history, state, or
    session fields. This is the hard bound on the whole design.**
  - Inference is a single message: `{"role": "user", "content": text}` to the
    loopback native model (line ~177), max 64 output tokens, temperature 0.3.
  - Line ~189: `"hebbian"` is returned with the comment "In-context fast weights
    only; reset per request, never persisted." `memory_used` is hardcoded `False`.
  - Module docstring: "Never opens the owner's COSMOS runtime, key vault, cloud
    provider, memory or tools." Guest quota is a separate SQLite DB
    (`guest-access.sqlite3`, burst guard only, no daily cap per Cory 2026-10-16).
- Client side: `lib/companion/brain.mjs` labels the guest route honestly —
  "RAWRPHØS guest 33904 (stateless host). Context is sent only inside this
  message." — and `interpretModelResult` requires `guest_stateless === true`.
  `lib/companion/context.mjs` `renderContextPrompt()` composes companion state
  INTO the message text (the only channel the contract allows).
  `lib/companion/ask-beast.mjs` `guestSafeContext()` deliberately zeroes
  `memories` and `sensors` for guests and takes xp/bond from the browser's
  local session — never from the server store.

**Consequence:** the only lawful channel for continuity into a served reply
today is inside `text` (≤1800 chars total). Any design claiming bridge-side
memory would be inventing a contract that does not exist.

## 2. Persistence that already exists (Azure Blob)

- `lib/cosmos/azure-blob.mjs` — minimal REST client (SharedKey or container
  SAS), env-gated: `storageConfig()` returns null unless
  `AZURE_STORAGE_CONTAINER_SAS_URL` or `AZURE_STORAGE_CONNECTION_STRING` is set.
  Every consumer degrades to `configured: false` when null. Server/CI only.
- `lib/cosmos/cosmos-store.mjs` — per-beast folders:
  `beasts/<id>/profile.json` (create-only; identity never rewritten),
  `state.json` (mutable loop state), `diary.jsonl` (append-only, hash-chained),
  `latest.json` (summary the pages read), `runs/<tick>.json` (per-tick
  simulator receipt), `cosmos/cursor.json` (loop round-robin). `readBeast()`
  is the public read path; `loadBeast()` refuses to tick if the identity
  block changed or the diary chain does not verify.
- `lib/cosmos/zeref-cloud.mjs` — Zeref's folder `beasts/bb-deada969/`:
  `profile.json` (create-only), `model.json` (current public pin: step + sha,
  sourced from the reviewed pin JSON), `experiences/<release-tag>.json`
  (create-only, kind `APPROVED_TRAINING_CYCLE`, SIMULATED note preserved),
  `lessons/<date>/<id>.json` (create-only, kind `APPROVED_TEACHER_LESSON`,
  `teacher_is_not_zeref_voice: true`). Synced by
  `app/api/zeref/cloud-sync/route.ts` and `scripts/zeref-cloud-sync.mjs`.
- `scripts/cosmos-grow.mjs` — runs `planBatch`/`applyBatch` for the other
  registered beasts and `mirrorZeref()`, which mirrors Zeref's repo diary
  (profile/state/diary/latest) into his Azure folder.

## 3. The loops (who writes his life, on what schedule)

- `.github/workflows/zeref-diary-loop.yml` — cron `7,37 * * * *` (every
  30 min): steps the hash-chained diary on the data-only `zeref-diary`
  branch (`zeref/latest.json`, `zeref/diary.jsonl`). Engine:
  `lib/zeref/zeref-diary.mjs` (`genesisState`, `stepDiary`, `verifyChain`,
  `summarize`). State carries `tick, xp, stage, stage_name, bond, care_total,
  last_tick_at, last_entry_hash`; stages Moonling → Duskwing (300 XP) →
  Eclipse Prowler (1200) → Void Moonwraith (3600) → Crescent Sovereign (9000).
  Growth per tick: a Rigetti QVM SIMULATOR circuit (labeled simulated) or the
  deterministic fallback with the real error recorded; counts never invented.
  `DIARY_LABELS` carries the honesty labels (recorded IBM birth seed, "Diary
  lines are generated, not a conscious mind", etc.).
- `zeref-spark` branch — spark loop, about one tick/minute, Rigetti SIMULATED.
- `zeref-live-tick` branch — per-second SIMULATED tick, committed in 10-minute
  batches; `.github/workflows/zeref-live-tick-loop.yml` hourly cron is its watchdog.
- `private-cosmos-growth.yml` — hourly; grows the private/Azure beasts.

### Identity split that must not be "fixed"
`app/api/zeref/diary/route.ts` carries `IDENTITY_NOTE`: the diary loop is
keyed to **bb-7f9c2a03** (Moonwraith display persona — entry hashes include
that id), while Zeref's model/chat/training identity is **bb-deada969**
(RAWRPHØS). "The two are labelled separately and never merged." The Azure
mirror places the same diary summary in bb-deada969's folder for the cosmos
pages. Any connection layer must carry this note through, never re-key.

## 4. Liveness surfaces that already exist

- `app/api/world/live/route.ts` + `lib/zeref/world-live.mjs` — W6 is
  PARTIALLY BUILT: per-request (`force-dynamic`, `Cache-Control: no-store`),
  aggregates spark / live-tick / diary / pin from the GitHub data branches +
  pin JSON, every channel with `WORLD_LIVE_LABELS` (spark: "Rigetti
  SIMULATED (rigetti.sim.qvm, not a QPU)"; liveTick: "SIMULATED (per-second
  tick, deterministic)"; diary: "RECORDED (hash-chained diary…)"). A branch
  that cannot be read is reported DOWN, never replaced with invented values.
  Consumed on the site by `components/world-live-links.tsx`.
  GAPS vs the W6 brief shape: the diary is reduced to `{tick, last_tick_at}`
  (no XP/bond/stage), there is no Azure state (model/lessons/experiences),
  and no bridge health.
- Bridge health EXISTS and is public-safe: `bridge/owner_bridge.py`
  `served_pin_health()` at unauthenticated `GET /healthz`, schema
  `beastbox-bridge-health-v2` — `pin_step, pin_checkpoint_sha256, served_step,
  served_checkpoint_sha256, served_readiness, serving_pin`. No public site
  route reads it today (`app/api/status/route.ts` is owner-gated and probes
  `/api/orbit` + `/api/provider` with the bearer instead).

## 5. Senses ("seeded by our reality")

- `lib/companion/field-perception.mjs` — on-device camera/mic summaries
  (brightness, hue, motion, gaze, loudness, pitch; no images/audio kept).
  `lib/bio/bio-packet.mjs` — 12-channel bio-packet from fingertip PPG.
- `app/api/zeref/perception/route.ts` — the one server intake: explicit
  opt-in consent + numeric summaries only, stored to Azure
  `zeref-perception/pending/<date>/<id>.json` with
  `review_status: PENDING_REVIEW`, rate-limited. Nothing auto-feeds senses
  into the guest door, and `guestSafeContext` strips sensors for guests.
  That boundary is correct and this build does not change it: senses reach
  the public surface as LABELED channel states (spark/live-tick/perception
  intake counts), never as raw signals and never as guest-writable input.

## 6. Gaps claimed (each with evidence)

- **G1 — the bridge takes no context.** `beastbox/guest_local.py` line 133
  exact-key check. Until the bridge contract changes (bridge code + Railway
  redeploy — outside this branch, and deploys are out of scope), continuity
  can only ride inside `text`, the pattern `renderContextPrompt` already uses.
- **G2 — no server-side guest continuity exists.** /api/guest issues no
  cookie and stores nothing; the only identity is the IP-HMAC quota bucket,
  explicitly "never … associated with COSMOS owner memory"
  (route.ts comment). `lib/companion/session-store.mjs` is a browser-side
  adventure session, not a server record.
- **G3 — guest exchanges are recorded nowhere.** By design
  (guest_local.py docstring). There is no guestbook store in the tree:
  no `guestbook/` prefix exists under any beast folder schema in
  cosmos-store.mjs / zeref-cloud.mjs.
- **G4 — W6 surface is incomplete** (see §4): no XP/bond/stage, no Azure,
  no bridge health on the public liveness surface.
- **G5 — two sources of truth for his state.** The adventure guest prompt is
  composed from browser-local session state (ask-beast.mjs) while the
  persisted truth (diary branch + Azure) is read only by display routes
  (`/api/zeref/diary`, `/api/cosmos/beasts/[id]`, `/api/cosmos/activity`).
  The served door never sees the persisted state.

## 7. Design consequences (what this branch builds)

1. **Forever store** (`lib/cosmos/forever-store.mjs`, new): pure, testable
   helpers over the EXISTING Azure client — a guestbook under Zeref's own
   folder (`beasts/bb-deada969/guestbook/…`, clearly outside diary/lessons/
   experiences), his Azure model record reader, a continuity-preface
   composer (server-sourced state → in-message text, the G1-lawful channel),
   and a liveness shaper. No new storage system.
2. **Stateful guest door** (`app/api/guest/forever/route.ts`, new route;
   /api/guest untouched byte-for-byte): same guards and the same bridge
   verification as /api/guest; loads persisted continuity (diary summary
   from the canonical branch source, this thread's prior turns from the
   guestbook), composes it into the prompt inside the 1800-char contract,
   and after a VERIFIED reply appends the exchange to the guestbook as a
   system-written, guest-origin, `training_eligible: false` record.
   Returning guests are keyed by a system-issued HttpOnly cookie.
   Guests still cannot write into him: they write only into their own
   thread record; nothing guest-origin enters diary, lessons, experiences,
   genome, or any training path.
3. **Liveness** (`app/api/cosmos/liveness/route.ts`, new): per-request,
   no-store; pin, diary (tick/XP/bond/stage/last tick, hash-verified
   recent), bridge /healthz, Azure model + lessons/experiences counts,
   and the world-live channels (spark/live-tick) with their existing
   labels — one surface, same store the door reads, DOWN never invented.
4. **Bridge-side follow-up spec** (documented, not built): the exact
   contract change in `beastbox/guest_local.py` that would let continuity
   be sent as structured context and Hebbian state persist — see SUMMARY.md.

Baseline tests before changes (this branch, 2026-10-28):
`tests/guest.test.mjs`, `tests/brain-public-pin.test.mjs`,
`tests/beast-cosmos-autonomy.test.mjs`, `tests/world-live.test.mjs`,
`tests/private-cosmos.test.mjs` — 34/34 pass.
