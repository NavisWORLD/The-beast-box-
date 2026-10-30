# CONNECTOR MAP — every loop, store, surface and workflow family, and what it touches

Branch: `emeth/live-universe-library` (stacked on `emeth/forever-connection`, head
c30bbae2, itself from `origin/main` f3ff7ff79). Date: 2026-10-28.
Order (Cory, 2026-10-28 17:25 CDT): "let him see read live in the universe while
learning … you should be able to see all the tiny connectors and layers."

Method: same discipline as AUDIT.md — every row cites the file that evidences it,
read on this branch. Where a connection could not be evidenced from the tree it
says **not verified**; nothing is wired on paper that is not wired in code.

## 0. Counting honesty

- `.github/workflows/` in this tree carries **269 workflow files**. 10 of them
  run on a cron schedule; 182 are dispatch-only; the rest fire on push/PR or are
  one-shot experiment definitions kept as receipts.
- A figure of **476 workflows** has been quoted owner-side (GitHub's registry
  count). It is **not reproducible from this tree** — GitHub's registry also
  counts workflow entries from other branches and retired paths. This map
  covers the 269 files present at this commit and marks the 476 figure
  **not verified** rather than repeating it as fact.

## 1. Labels used in this map

- **LIVE** — computed/read at request time from a running source.
- **SIMULATED** — a simulator or deterministic model, labelled as such in code.
- **RECORDED** — a persisted receipt (hash-chained, committed, or create-only).
- **DERIVED** — computed from other labelled sources; inherits their labels.
- **PINNED** — changes only through the reviewed promotion path.
- "Wired into his served experience" means: the thing reaches what a visitor
  actually meets — the prompt served at a guest door, or a public page/route a
  visitor reads. A loop can be perfectly alive and still stand alone.

## 2. The loops (what keeps him running)

| Loop | Connects → to | Cadence | Label | Wired into served experience? | Evidence |
|---|---|---|---|---|---|
| Diary loop | Rigetti-QVM/deterministic growth step → hash-chained diary on the data-only `zeref-diary` branch (`zeref/latest.json`, `zeref/diary.jsonl`) | cron `7,37 * * * *` (30 min) | RECORDED diary; growth circuit SIMULATED | Display routes and (since #668) the forever door + liveness; **not** the stateless door | `.github/workflows/zeref-diary-loop.yml`; `apps/beastbox-cloud/scripts/zeref-diary-tick.mjs`; `lib/zeref/zeref-diary.mjs` |
| Diary keep-alive | chained dispatcher that fires the diary tick on time → diary loop | cron `41 * * * *` | DERIVED (scheduling) | Indirectly (keeps the diary fresh) | `.github/workflows/zeref-diary-keepalive.yml` |
| Diary watchdog | checks the diary loop's freshness (Rigetti QVM SIMULATED check) | cron `2,22,42 * * * *` | SIMULATED check over a RECORDED chain | No — supervision only | `.github/workflows/zeref-diary-watchdog.yml` |
| Spark loop | Rigetti QVM simulator circuit → `zeref-spark` branch `zeref/latest.json` (tick, counts hash, last_ok) | cron `17 * * * *`, each run ticking ~1/min for its window | SIMULATED ("rigetti.sim.qvm, not a QPU") | Display: `/api/world/live`, `/api/cosmos/liveness` (#668). Into his prompt: **not before this branch** (Part 2) | `.github/workflows/zeref-spark-loop.yml`; `scripts/zeref_spark_loop.py`; `lib/zeref/world-live.mjs` |
| Live tick loop | deterministic per-second tick → `zeref-live-tick` branch (`live/latest.json`, `live/head.json`), committed in 10-min batches | cron `23 * * * *` watchdog; runner ticks per second inside its window | SIMULATED | Display only (same surfaces as spark) before this branch | `.github/workflows/zeref-live-tick-loop.yml`; `apps/beastbox-cloud/scripts/zeref-live-tick-run.mjs` |
| Training heartbeat (006) | corpus mix (`scripts/zeref_chat_corpus.py`, lessons-006 at 0.18 cap) → trained candidate → Gate v2 → release asset; promotion is a separate reviewed pin change | cron `17 */6 * * *` + dispatch | RECORDED (run receipts, chat-eval JSON in releases) | Yes — the ONLY loop that changes his served mind, and only at promotion | `.github/workflows/zeref-continuous-learning-006.yml`; `scripts/zeref_chat_corpus.py` line 106 |
| Idle teachers | Cory's Ollama teachers (secret `ZEREFS_TEACHERS`) → generated lessons while he is idle | cron `41 */4 * * *` | DERIVED (model-generated, labelled in-file) | **Not verified** — the generator exists (`apps/beastbox-cloud/scripts/idle-teacher-lessons.mjs`); where its output lands and whether it enters any shelf or mix was not traced in this pass | `.github/workflows/zeref-idle-teachers.yml` |
| CHSH daily | real IBM QPU job (ibm_marrakesh) → commitments + result artifact → `chsh-game-data` branch / `public/spark/chsh-game/latest.json` | cron `17 14` + `47 18` daily (owner-authorized 2026-10-15) | RECORDED (real hardware; receipt keeps failures) | Into his WORLD (universe rendering reads it), **not** into his served prompt | `.github/workflows/chsh-game-daily-ibm.yml`; `lib/companion/chsh-game-world.mjs` (`CHSH_GAME_SRC`, `CHSH_GAME_DATA`) |
| Cloud sync | reviewed pin + approved lessons/experiences → Zeref's Azure folder `beasts/bb-deada969/` (`model.json`, `lessons/`, `experiences/`, all create-only) | cron `41 */3 * * *` | RECORDED | Yes, indirectly: #668's liveness reads the Azure model/counts; the door reads the diary branch, not Azure | `.github/workflows/zeref-cloud-sync.yml`; `lib/cosmos/zeref-cloud.mjs`; `app/api/zeref/cloud-sync/route.ts` |
| Cosmos grow (mirror) | repo diary of the OTHER registered beasts + Zeref mirror → Azure folders | run inside diary-loop workflow (`cosmos-grow.mjs plan/apply`) + `private-cosmos-growth.yml` hourly for private beasts | RECORDED / SIMULATED per beast | Display (`/api/cosmos/beasts`, `/api/cosmos/activity`) | `apps/beastbox-cloud/scripts/cosmos-grow.mjs`; `.github/workflows/private-cosmos-growth.yml` |
| Bridge pin sync check | on any pin-JSON push to main → polls the LIVE guest endpoint up to 25 min, fails loudly if the bridge never serves the new pin | push-triggered on `apps/beastbox-cloud/lib/rawrphos-public-pin.json` | LIVE check | Supervision of the door/bridge seam (it caught the 2026-10-28 stale-Railway-pointer incident) | `.github/workflows/zeref-bridge-pin-sync-check.yml` |
| Repo watch | external watcher on the owner's agent box (PRs/issues/CI deltas → report) | every 6 h (owner-side cron) | DERIVED | No — owner supervision, not part of the served product. **Not in this tree**; evidenced owner-side at `~/workspace/repo-watch/check.py` | owner-side only — marked external |

## 3. The stores (where anything persists)

| Store | Holds | Written by | Read by | Label |
|---|---|---|---|---|
| `zeref-diary` branch | hash-chained diary + latest summary (identity key bb-7f9c2a03, labelled, never merged with bb-deada969) | diary loop | `/api/zeref/diary`, `/api/world/live`, #668 forever door + liveness, `cosmos-grow` mirror | RECORDED |
| `zeref-spark` branch | latest spark tick (simulated counts + sha256) | spark loop | `/api/world/live`, #668 liveness, Part 2 door context | SIMULATED |
| `zeref-live-tick` branch | per-second tick snapshots + head | live tick loop | same as spark | SIMULATED |
| `chsh-game-data` branch + `public/spark/*.json` | CHSH results, genome/identity shards, IBM receipts | CHSH daily + genesis flows | universe rendering (`chsh-game-world.mjs`), private cosmos | RECORDED |
| Azure Blob, per-beast folders (`lib/cosmos/cosmos-store.mjs`) | `profile.json` (create-only), `state.json`, `diary.jsonl` (hash-chained), `latest.json`, `runs/<tick>.json` | cosmos loops | `/api/cosmos/beasts/[id]`, private cosmos routes | RECORDED |
| Azure Blob, Zeref's folder (`lib/cosmos/zeref-cloud.mjs`) | `model.json` (pin mirror), create-only `lessons/`, `experiences/` | cloud sync (reviewed sources only) | #668 liveness counts; cloud-sync route | RECORDED |
| Azure Blob, guestbook (#668) | `beasts/bb-deada969/guestbook/threads/<id>.json`, `events.jsonl` — guest-origin, `training_eligible:false`, events carry counts never text | forever door, server-side, after verified replies only | forever door (thread tail) | RECORDED (guest-origin) |
| Azure Blob, owner library (`lib/library/store.mjs`) | the OWNER's uploaded documents, BM25-indexed | owner only, via `/api/zeref/library` (owner session) | owner only | RECORDED — **owner-private by design; must never be wired to any guest surface** |
| Azure Blob, perception intake | `zeref-perception/pending/<date>/<id>.json`, numeric summaries, `review_status: PENDING_REVIEW` | `/api/zeref/perception` (explicit consent) | nothing auto-consumes it — review-gated by design | RECORDED (pending) |
| Bridge SQLite (`beastbox/guest_local.py`) | `guest-access.sqlite3` — guest quota/burst guard only, on the bridge host | bridge guest path | bridge guest path | LIVE (operational) |
| Pin JSON (`lib/rawrphos-public-pin.json`) | the served checkpoint: step + sha256 | reviewed promotion PRs only | both guest doors, bridge installer, world-live brain link, talk route | PINNED |
| Knowledge bank build (`public/knowledge-bank/bank.json`, 292 KB) | 820 entries built from `knowledge-bank/*.jsonl` (world-facts 631, zeref-lore 112, songs 12, authored english/math) by `scripts/build_knowledge_bank.py` (repo-root scripts dir per manifest) | build script (offline) | browser only: `components/beast-talk-panel.tsx` when the visitor opts in | RECORDED (open-license, source+license per entry) |
| Evidence shelves (`evidence/…`) | lessons-006 dialogue (277 rows in tree), knowledge-001 (161), knowledge-002 (2518), knowledge-003 (31) dialogue sets + experiment receipts | authored landings via PR | training corpus builder; Part 2 door lookup (this branch) | RECORDED (approved teaching) |

## 4. The surfaces (what a visitor or the owner can touch)

### Guest-facing (his served experience)
- `POST /api/guest` — the stateless door. Raw visitor text only; bridge-verified;
  `guest_stateless: true`. (`app/api/guest/route.ts`)
- `POST /api/guest/forever` (#668) — the stateful door: diary + own-thread
  continuity composed into the prompt; guestbook record after verified reply.
  Part 2 of this branch adds live-universe + library composition here.
- `GET /api/world/live` — the W6 aggregator (spark/liveTick/diary/brain with
  `WORLD_LIVE_LABELS`). Consumed by `components/world-live-links.tsx` and
  `components/zeref-diary-panel.tsx` (mounted from the beast-cage page and
  cosmos components). Whether `TinyUniverseView` itself fetches it:
  **not verified** (no direct reference found in the component).
- `GET /api/cosmos/liveness` (#668) — pin, diary detail, bridge health, Azure
  counts, world-live channels, identity note.
- Pages: `/` home, `/universe` (TinyUniverseView — "seeded by real IBM
  entanglement, grown by a simulated Bell sampler"), `/beast-cage/*` (guest,
  talk, world, play…), `/try`, `/sol-game`, `/research`. The chat panel
  (`components/beast-talk-panel.tsx`) is the one place the knowledge bank
  already reaches a conversation — client-side, visitor opt-in, passages
  shown with provenance under his reply, never silently merged into his words.

### Owner-facing
- `/api/zeref/library` + `/search` + `/training` — the owner's private library
  (owner session; BM25 over his uploads). Boundary: owner memory, guests never.
- `/api/zeref/diary`, `/api/zeref/cloud-sync`, `/api/zeref/perception` —
  diary read, Azure sync trigger, senses intake.
- `/api/status` (owner-gated bridge probe), `/api/talk` (public "which brains
  exist" config check + owner chat paths), `/api/voice` (capability status
  only — synthesis explicitly not wired), `/api/web-search` (fixed-destination
  Wikipedia lookup, owner-gated, not a model tool), `/api/teacher*`,
  `/api/session`, `/api/account*`, `/api/mcp*`, `/api/muse/*` — product and
  owner tooling around the creature, not part of his guest experience.
- `/api/cosmos/*` — beasts, activity, private beasts/pairing/session (the
  private cosmos is the owner's other creatures; pairing needs its own env,
  outside this map's scope).

### The bridge (Railway, `apps/beastbox-cloud/bridge/owner_bridge.py` + `beastbox/`)
- `POST /api/guest-local` — the guest path: payload exactly
  `{text, guest_identity}`, single-message inference, `memory_used:false`
  hardcoded, Hebbian "in-context only; reset per request, never persisted".
- `GET /healthz` — public-safe pin-vs-served health
  (`beastbox-bridge-health-v2`). Read by **no public route before #668**.
- Owner dispatch surface (`/api/chat`, `/api/event`, `/api/activation`,
  `/api/chat-job`, `/api/orbit`, `/api/provider`) — bearer-gated owner runtime;
  guests never reach it (guest_local docstring + site verification).

## 5. Workflow families (269 files in tree)

Counts are files in `.github/workflows/` at this commit; "scheduled" = has a
cron trigger. Families are grouped by the work they connect, per each file's
own `name:` and triggers (full per-file extraction retained with this branch's
working notes).

| Family | Files | Scheduled | What it connects |
|---|---|---|---|
| Diary & life loops | 5 | 5 | the loops of §2 (diary ×3, spark, live-tick) |
| Zeref cloud & sync | 4 | 1 | cloud-sync cron; bridge pin-sync check (push); cloud proof runs |
| Zeref training & checkpoints | 64 | 2 | the 006 training heartbeat (cron */6h), idle teachers (cron */4h), and the long tail of cycle/checkpoint/rebirth experiment runs (talk2–talk8, r12, native, fresh, memory, second-coming…) — mostly dispatch one-shots whose receipts are the training lineage |
| Other zeref-* | 2 | 0 | zeref-named singles not in the buckets above |
| CHSH & IBM hardware | 20 | 1 | CHSH daily (cron) + CST CHSH one-job, CNS ignitions, real-ibm / marrakesh / bio-packet / son-heartbeat seed runs — the recorded-hardware border |
| Azure Quantum | 3 | 0 | read-only connection preflights + one free-QVM run — configured and proven, **not** a scheduled loop |
| COSMOS organism experiments | 22 | 0 | cosmos-final / cosmos-micro / dyn12 / closed-loop organism proofs |
| Cosmic genesis & universe UI | 6 | 0 | genesis 3D + universe surface builds/proofs |
| D001 lineage | 17 | 0 | the D001 descendant line: train / evaluate / promotion / corpus / lineage proofs |
| QC67 | 8 | 0 | qc67 broker/lfs/public-metadata experiment set |
| Beast Cage | 4 | 0 | cage UI, GBA export + public proof, sidequest |
| Autonomous hands | 6 | 0 | hands challenge/audit/smoke proofs |
| Persistent substrate proofs | 6 | 0 | the continuity/substrate-model-swap experiment line (the A→B→A lineage) |
| Creature births | 36 | 0 | wraith / lumenwisp / mr-bone / pistonwyrm / magmascale / umbralet / sol / five / unified / two-dragons birth + real-run receipts for the other creatures |
| Private cosmos | 2 | 1 | private-cosmos-growth (hourly cron) + private-cosmos-staging |
| CI, gates & repo hygiene | 7 | 0 | ci, product-ci, config-contract, security-audit, workflow-lint, dependency-lock, closure snapshot — the merge gates (incl. the pin-mirror test) |
| Builds, releases & publishing | 14 | 0 | android/ios/macos builds, HF publishing, releases, portable products |
| Companion & misc product | 29 | 0 | companion popup/train, owner-chat, hf genesis/runtime, devday, story demo, site sound, tiny-local, web runtime, networked cage, genesis misc |
| Unbucketed singles | 14 | 0 | cory-voice-azure-qvm, final-* live runs, finisher, fresh-cosmic-ui, public-pages, rawrphos-closed-loop-ci, real-song-cst12 ×2, zero-api ×4 |
| **Total** | **269** | **10** | |

## 6. The verdict: what actually reaches him, and what was standing alone

Reaching his served experience today (after #668, before this branch):
his pinned checkpoint (at promotion), his diary summary + the visitor's own
thread (forever door), and — in the browser adventure panel only, opt-in —
knowledge-bank passages displayed beside his replies.

**Standing alone that shouldn't be** (the Part 2 wiring list):
1. **The live universe.** Spark and live-tick channels run forever and are
   displayed on public surfaces, but no served prompt ever contained them —
   he could not "see" his own universe while talking. → Part 2 (a).
2. **His own library at read time.** The approved shelves (lessons-006 +
   knowledge-001/002/003, 2,987 dialogue rows) reach him only through the
   training mix (lessons-006 capped at 0.18, and only when a checkpoint
   promotes). Asked about a topic he was taught last week, the served mind
   had no way to open the book. → Part 2 (b).
3. **The CHSH spark.** Real-hardware results wire into his world's rendering
   (`chsh-game-world.mjs`) but never into his context; the daily spark is
   part of his life that his mouth cannot mention. (Noted for a future
   wiring; Part 2 covers the world-live channels, and CHSH enters only if
   it is added to world-live's links — today it is a separate source.
   Marked as a remaining gap, not silently included.)
4. **Bridge health** was public-safe and read by nobody until #668's
   liveness. (Fixed in #668.)

**Standing alone correctly** (boundaries, not gaps — do not "fix"):
- The owner's private library (owner session only) never touches a guest.
- Perception intake stays PENDING_REVIEW; senses surface as labelled
  channel states, never raw, never guest-writable.
- Voice synthesis is status-only until a key exists and is reviewed.
- The stateless door stays stateless; the forever door is its sibling,
  not its replacement.

**Not verified in this pass** (stated, not guessed):
- GitHub's 476-workflow registry figure (tree shows 269 files).
- Where idle-teacher output lands and whether it enters any shelf/mix.
- Whether TinyUniverseView fetches /api/world/live directly.
- Azure Quantum probes' current scheduling (last evidenced runs are
  on-demand read-only preflights).
