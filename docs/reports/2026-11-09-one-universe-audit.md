# One Universe audit — 2026-11-09

Step 1 of item 8 only. No consolidation code. Nothing in the app was removed or retargeted.

Source is `main` at `f2b1774b7dfa605182428edb2f5847a55c372fc8` (merge of #901, 2026-11-09 14:45 -0600). App: `apps/beastbox-cloud`. Production build: Next.js 16.3.8 (`npm run build`, exit 0). The live host named in the directive is `www.beastboxcosmos.xyz`. These weights and boot times are from this commit’s production build, served by `next start` on this machine. They are not a capture of the live CDN.

## Headline

The growth document is already one clock. The pictures are not.

`OneWorldProvider` (`components/one-world-provider.tsx`) is mounted from `app/layout.tsx` on every page. It fetches `/universe/tiny-universe-genesis.json` once and starts `oneWorldClock` (`lib/world/one-world-clock.mjs`): one in-memory state, one `localStorage` key `lw:universe`, one `grow()` step every 2000 ms, cap 4000. Living World and Tiny Universe already read that clock. Pocket, Look Closer, Beach Two, the field, and the pedestal do not advance it, and they do not share its sun, its creature list, or its render loop.

First-load JS is the Next build diagnostic `.next/diagnostics/route-bundle-stats.json` (`firstLoadUncompressedJsBytes`). Gzip is the sum of gzip level 9 of those same chunk files. Next 16.3.8 did not print the old “First Load JS” table. Dynamic scene chunks (Living World, the Cage pocket, three.js inside them) are outside first-load and show up in the emulated transfer column.

| | Uncompressed | Gzip |
|---|---:|---:|
| Shared floor (14 chunks: `/sol-game`, `/beach-two`, `/connect/meta-muse`, `/_not-found`) | 1,003,059 B | 338,808 B |
| Heaviest first-load, `/universe` | 1,849,038 B | 562,367 B |
| Largest gzip of a first-load set, `/` | 1,828,180 B | 600,890 B |
| `/beast-cage` (scenes code-split) | 1,164,334 B | 397,626 B |
| `/beast-cage/world` (Living World still dynamic) | 1,008,168 B | 340,818 B |

EMULATED phone profile, not a handset. Playwright device Pixel 5: viewport 393×727, screen 393×851, deviceScaleFactor 2.75, mobile, touch, Chrome/140 Android UA. CPU throttle `Emulation.setCPUThrottlingRate` rate 4. Network labeled Slow 4G: latency 150 ms, download 200,000 B/s (1.6 Mbps), upload 93,750 B/s (750 Kbps). No extra Lighthouse 3.75× latency factor. Rasteriser on this host: `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)`. `isSoftwareGL()` is therefore true, so `/` keeps the Cage pocket and does not mount Living World (`components/home-pocket.tsx`). A phone GPU would take the other branch. Measured 2026-11-09T21:49:08Z, plus a scene pass just after for the WebGL canvas.

EMULATED boot, two signals. “Ready” is `domContentLoadedEventEnd` when no connected canvas framed. “First frame” is two animation frames after `getContext` on a canvas that is in the document. The software-GL probe canvas is not in the document and is not counted.

| Surface | EMULATED |
|---|---|
| Document pages with no scene canvas | ready 1.04–1.21 s |
| `/universe` 2D map (details already open; no WebGL on SwiftShader) | first frame 4.0 s |
| `/beast-cage/world` Living World WebGL, `data-living-world=orbit` | 6.5 s and 6.7 s (two runs) |
| `/beast-cage/look` and `/beast-cage/turntable` pedestal WebGL | 5.9–6.2 s |
| `/beach-two` iframe WebGL | 5.0 s and 5.3 s |
| `/` pocket WebGL (`data-pocket-webgl`) | 10.9 s; pocket `ready` by 15.2 s. An earlier unnamed 2D canvas framed at 4.5 s |
| `/beast-cage` pocket WebGL context | 12.2 s (canvas still 300×150). `data-pocket-state=ready` and laid-out canvas 351×339 at 15.3 s. An earlier 2D canvas framed at 3.8 s |

## What each picture runs

Every Next page also inherits the layout: the one-world clock (after genesis arrives), `CompanionProvider` (session key `beastbox-companion-session-v1`, roaming sprite only on `/` and `/beast-cage`, ambient interval 1600 ms), and `LostCosmosDock` (the V12.2 emulator does not start until Play). Those are named again only where the page adds its own scene.

### `/` — `app/page.tsx` → `components/home-pocket.tsx`

- **World state.** Shared view `beastbox-cage-view-v1` via `useWorldView`. Guest default is the embedded Living World unless this device saved pocket or classic (`lib/world/home-guest-view.mjs`). On a software rasteriser `softHome` forces `CagePocketDimension` instead. “Enter the tiny world” portals a full `LivingWorld` over the page. This run: pocket, no `[data-living-world]`.
- **Store.** `lw:universe` through the layout clock. View key above. Beast from the session, else `public/spark/zeref-live-20261010/unsigned-session.json` (`ZEREF_HOME_DEFAULT`, id `bb-deada969`). Pocket 3D prefs `beastbox-pocket-3d-settings-v1`.
- **Sun and sky.** Pocket path: `createPocketSky` (`lib/pocket-sky.mjs`, seeded orbiting `MeshBasicMaterial` bodies) plus `HemisphereLight(0x94d9ff, 0x20113b)` and two `PointLight`s (`cage-pocket-dimension.tsx` around lines 312–315), plus `addHeaven` (`lib/worlds/heaven.ts`). Heaven’s far disc uses `pocketSunDir()` → `oneSunAt(Date.now()/1000).dir` with a floor on Y. Heaven also adds its own directional and hemisphere. Living path, when a GPU takes it: `oneSunAt` + `p2SkyAt` + `lightRigFor` inside `components/living-world.tsx`.
- **Render loop.** `CagePocketDimension` `animate` (`cage-pocket-dimension.tsx` line 519). Full Living World, when opened, adds `frame` (`living-world.tsx` line 722) and `post.render` / `renderer.render` (line 978).
- **Creatures.** Session beast or the Zeref unsigned JSON. Residents: `ARTIST_RESIDENTS` (`lib/companion/artist-residents.mjs`) via `addPocketResidents`. Artist-drawn, no quantum seed. Not read from Azure.
- **Tick.** Pocket: per-frame `stepLivingCore`, `stepLife`, `life.update` (lines 561–591). Layout clock still grows `lw:universe` every 2 s. The pocket does not step that clock.
- **JS.** First-load 1,828,180 B, gzip 600,890 B, 21 chunks. Emulated script transfer 766,379 B across 29 scripts (includes chunks past first-load).
- **Boot.** EMULATED. 2D canvas 4,530 ms. Pocket WebGL 10,868 ms. Pocket `ready` by 15.2 s wall.

### `/beast-cage` — `app/beast-cage/page.tsx` → `components/beast-cage-portal.tsx`

- **World state.** Same view key as home. `CagePocketDimension` is always mounted (dynamic import). `LivingWorld` mounts embedded when `view==='world'` and a saved QBEAST exists, and again full-screen when expanded. Both loops can run together. Overlay `SparkBeastArena` when the view is classic (sprite) or pocket-with-rig.
- **Store.** View key, `beastbox-cage-mode-v1` (Friendly / Advanced), `beastbox-cage-appearance-v1`, `beastbox.cage.creature.v1`, session. Diary panel reads `/api/zeref/diary`.
- **Sun and sky.** Pocket heaven stack above. CSS class `cage-sky` behind the habitat. Living World, when the view is world, uses the living-world sun (next section).
- **Render loop.** Pocket `animate`. Arena loop in `components/spark-beast-arena.tsx`. Care deck canvas in `BeastCareDeck`. Living `frame` when that view is on.
- **Creatures.** Session QBEAST, else a seeded starter from `generateCreature` (`lib/creature-profile.ts`) and the Zeref profile. Residents are `ARTIST_RESIDENTS`. Azure registration is a separate opt-in (`public/spark/cosmos-optin.mjs`, `components/grow-in-cosmos.tsx` → `POST /api/cosmos/beasts`). The habitat does not place creatures from `beasts/<id>/state.json`.
- **Tick.** Pocket per-frame life brain. Arena `stepPocket` / mind. Diary tick is the GitHub `zeref-diary` branch (`app/api/zeref/diary/route.ts` fetches `zeref/latest.json`). That tick is not `grow()`.
- **JS.** First-load 1,164,334 B, gzip 397,626 B, 19 chunks. Emulated transfer 882,692 B, 43 scripts.
- **Boot.** EMULATED. 2D canvas 3,804 ms. Pocket WebGL context 12,245 ms. `data-pocket-state=ready` and canvas 351×339 at 15.3 s.

### `/beast-cage/world` — `components/living-world-page.tsx` → `components/living-world.tsx`

- **World state.** The living-world scene. Reads `currentWorldClock()` (lines 143–145). Visit `?planet=` derives a seed and does not write `lw:universe`.
- **Store.** `lw:universe` (read; written only when the clock is absent). `lw:traits:<beastKey>`, `lw:spawned` in `sessionStorage`, camera mode `beastbox.world.view.v1` (`lib/world/view-mode.mjs`: `first`, `behind`, `orbit`).
- **Sun and sky.** `oneSunAt(Date.now()/1000, localUp)` then `lightRigFor` drives the existing sun and hemisphere (`sky-view.mjs`). Sky dome `addSkyDome` / `addP2Sky` / `p2SkyAt`. Beach camera replaces that direction with a noon-ish vector built from the shore normal (`living-world.tsx` around line 726) while `__lwNoon` is not `night`. `__lwNoon` is a second override. Companion disc does not light (`COMPANION_DISC.lights` is false in `lib/universe/one-sun.mjs`).
- **Render loop.** `frame` requestAnimationFrame, line 722. Draw at line 978: `post.render`, ASCII, or `renderer.render`.
- **Creatures.** `ARTIST_RESIDENTS` as sprites (line 444) plus the session beast via `createCreatureLoop`, and a Zeref GLB at the second gathering point. Not Azure.
- **Tick.** Per-frame `stepWorldField` (line 337). Every 2 s `applyTick` (line 556) reads the one-world clock when the seed matches, and calls `grow()` only if that clock is missing. Field moisture and weather move on this 2 s cadence even when growth comes from the clock.
- **JS.** First-load 1,008,168 B, gzip 340,818 B, 15 chunks. Emulated transfer 746,227 B, 29 scripts (the dynamic living-world chunk is in the transfer).
- **Boot.** EMULATED. WebGL first frame 6,714 ms on the full pass (`data-living-world=orbit`) and 6,461 ms on the scene pass.

### `/universe` — `components/tiny-universe-view.tsx`

- **World state.** Reads the one-world clock through `useOneWorld` (lines 37–43). Pause freezes this picture only. `↺ Genesis` copies the genesis snapshot into the view state. `localStorage` `u:3d` chooses 2D vs `Universe3D`. On software GL the default is 2D. A door can mount `LivingWorld` with `door` (`?door=1`, or a real GPU).
- **Store.** `lw:universe` via the clock. `u:3d`.
- **Sun and sky.** 2D: radial gradients in the canvas `draw` (line 46) and a planet terminator from the star position. 3D, when on: `genesis-sun.mjs` / `genesis-sun-three.ts` inside `components/universe-3d.tsx` (its own rAF at line 255). This run also showed `[data-seeded-land-2d]`.
- **Render loop.** 2D `draw` rAF, line 77. Optional `Universe3D` `frame`. Optional door uses Living World `frame`.
- **Creatures.** A drawn Zeref marker on the map (`zerefStar`). No Azure beast list. Life worlds are fields on the universe document (`u.life`), simulated by `grow()`.
- **Tick.** `oneWorldClock.step` every 2 s. The HUD prints `u.tick`.
- **JS.** First-load 1,849,038 B, gzip 562,367 B, 18 chunks. Emulated transfer 569,128 B, 18 scripts.
- **Boot.** EMULATED. 2D map canvas 4,004 ms (full pass) and 3,994 ms (scene pass). `[data-universe-details]` was open, so the clock had delivered a universe. No WebGL on this rasteriser.

### `/beast-cage/look` and `/beast-cage/turntable`

`app/beast-cage/look/page.tsx` re-exports the turntable page. Same component, same first-load (1,430,947 B, gzip 457,479 B, 17 chunks).

- **World state.** None of the living-world or pocket scenes. Pedestal markup `data-look-pedestal` (`turntable/page.tsx` line 62). Subject is workshop / moonwraith / dragonling. `?glb=1` swaps in `ZerefGlb3D`.
- **Store.** Companion profile in memory and `beastbox-active-creature-v1`. Labels `lib/look-closer-labels.json`.
- **Sun and sky.** `CosmicCompanion3D` uses `stageRig('thick', stageTimeOfHour(local hour))` (`lib/universe/open-stage-rig.mjs`): hemisphere plus key, fill, rim. `ZerefGlb3D` uses a fixed hemisphere and four directional lights (`zeref-glb-3d.tsx` lines 68–72), the same studio as `beastStudio` in `components/creature-glb-beast.ts`.
- **Render loop.** `CosmicCompanion3D` `animate` (line 92). GLB `tick` rAF (line 229).
- **Creatures.** The profile rig, or the Moonwraith / dragonling dimensional ids. Not `ARTIST_RESIDENTS`. Not Azure state.
- **Tick.** Spin and pose only. No world-field tick and no `grow()`.
- **Boot.** EMULATED. Look WebGL 6,209 ms (full) and 5,932 ms (scene), canvas class `cosmic-creature-canvas`. Turntable full pass 6,173 ms. Transfer 626,321 B, 25 scripts, on both.

### `/beach-two` — iframe `public/beach-two/toy.html` → `public/beach-two/toy.js`

- **World state.** Its own `simTime`. Not `lw:universe`.
- **Store.** In-page seed picker. No session.
- **Sun and sky.** `HemisphereLight(0xcfe8ff, 0xd8b880)` and `DirectionalLight(0xfff2d8)` at a fixed position (`toy.js` lines 30–31). Shader sky `skyTop` / `skyBot`.
- **Render loop.** `frame` rAF lines 496–499, calls `sim(DT)` then `renderer.render`.
- **Creatures.** Volleyball actors seeded from the IBM stream in the toy. Not QBEAST, not Azure.
- **Tick.** `sim(dt)` inside the frame.
- **JS.** Page first-load is the shared floor, 1,003,059 B / gzip 338,808 B. The toy’s scripts are outside that set.
- **Boot.** EMULATED. Iframe WebGL (`canvas#c`) 5,012 ms full pass, 5,325 ms scene pass.

### `/beast-cage/field` and `/beast-cage/go`

- **World state.** Open-field AR (`components/ar-creature-stage.ts`), modes `xr`, `anchored`, `preview`. Not the pocket and not the living world. Go adds the HUD in `components/beast-go.tsx` and CSS from `lib/world-scene.ts`.
- **Store.** Session beast. Go holds trail on the session.
- **Sun and sky.** `beastStudio`: hemisphere plus key, fill, and two rims (`creature-glb-beast.ts` lines 228–231). Fixed positions, then the key is aimed at the anchor.
- **Render loop.** `renderer.setAnimationLoop` (`ar-creature-stage.ts` line 134).
- **Creatures.** Session genome, optional Zeref friend. Life brain is local (`createLife` / `stepLife`). Not Azure.
- **Tick.** Per-frame life brain and hop. Not the 2 s world clock.
- **JS.** Field 1,027,876 B / gzip 348,257 B. Go 1,075,002 B / gzip 364,419 B.
- **Boot.** EMULATED. Field WebGL `data-ar-canvas` 6,423 ms and 6,309 ms. Go 6,841 ms and 6,736 ms. Transfers 832,782 B (field) and 591,350 B (go).

### `/beast-cage/play` — `components/beast-adventure.tsx`

2D trail map (`PixelBeast` canvas). Session beast. CSS background. No world sun. rAF on the pixel canvas. Local session only. First-load 1,063,932 B / gzip 361,645 B. EMULATED 2D first frame 3,201 ms. No WebGL in 50 s.

### `/beast-cage/talk`, `/beast-cage/guest`, `/growing`, `/try`

No world scene.

| Route | What it is | First-load uncompressed / gzip | EMULATED ready |
|---|---|---:|---:|
| `/beast-cage/talk` | Chat. Session. No rAF in the talk component. | 1,473,702 / 473,940 | 1,126 ms |
| `/beast-cage/guest` | GBA guest lab. 2D preview is not created on first paint. | 1,442,860 / 462,527 | 1,207 ms |
| `/growing` | `GrowingChat` text. | 1,004,458 / 339,581 | 1,137 ms |
| `/try` | Guest model form. `POST /api/guest`. | 1,015,886 / 344,004 | 1,117 ms |

Transfers on that run: talk 480,494 B, guest 468,798 B, growing 344,865 B, try 349,289 B.

### `/sol-game`

The page file is the journey copy. The cartridge is the layout dock and stays on its poster until Play. No canvas on this run. First-load is the floor, 1,003,059 / 338,808. EMULATED ready 1,055 ms. Transfer 343,792 B, 14 scripts. The in-ROM tick is not the site world clock.

### `/workspace`

`Studio` can mount `CosmosWorld` (`components/cosmos-world.tsx`), a decorative WebGL nebula (fragment shader, no sun, rAF at line 142) on the COSMOS WORLD panel. This load hit the gate and produced no canvas in 40 s. First-load 1,225,559 / gzip 409,579. EMULATED ready 1,058 ms. Transfer 680,073 B, 23 scripts.

### `/brain-bay`

`BrainBayWorkshop` can show `PixelBeast`. No connected canvas in 40 s on this profile. First-load 1,014,526 / gzip 342,688. EMULATED ready 1,039 ms.

### `/settings`

`UniverseSettings` writes pocket 3D prefs, motion, and sound. No scene. First-load 1,051,929 / gzip 355,992. EMULATED ready 1,070 ms.

### Remaining documents

No scene of their own. Clock still starts from the layout. EMULATED ready is `domContentLoadedEventEnd`.

| Route | First-load uncompressed / gzip | EMULATED ready | Transfer |
|---|---:|---:|---:|
| `/account` | 1,006,016 / 340,224 | 1,158 ms | 345,508 B |
| `/classroom` | 1,007,001 / 340,625 | 1,153 ms | 345,909 B |
| `/connect/meta-muse` | 1,003,059 / 338,808 | 1,046 ms | 343,792 B |
| `/connect/meta-muse/pair` | 1,008,066 / 340,557 | 1,065 ms | 345,844 B |
| `/loop` | 1,012,276 / 342,789 | 1,133 ms | 348,073 B |
| `/messages` | 1,004,479 / 339,542 | 1,149 ms | 344,826 B |
| `/mind-room` | 1,007,134 / 340,539 | 1,132 ms | 345,822 B |
| `/next` | 1,003,383 / 339,076 | 1,116 ms | 344,416 B |
| `/privacy` | 1,003,383 / 339,076 | 1,126 ms | 344,416 B |
| `/research` | 1,014,403 / 343,210 | 1,110 ms | 348,496 B |
| `/research/stage015` | 1,003,383 / 339,076 | 1,055 ms | 344,416 B |

`/_not-found` is in the build stats at the floor (1,003,059 / 338,808) and was not opened.

### `/spark/index.html` (rewrite from `/spark`)

Static habitat. `public/spark/app.mjs` `tick` + rAF `loop` (around lines 627–693). 2D canvas `#view`. Session `beastbox-companion-session-v1`. CSS stars, no three.js sun. Creatures are the local QBEAST / spark session. Not the living-world population and not Azure. Own `tick(dt)`. Not in `route-bundle-stats.json`. EMULATED 2D canvas `#st1` at 5,381 ms. Transfer 148,853 B across 41 scripts. `prebuild` had already copied `lib/companion/emotion.mjs` and `lib/companion/beast-talk.mjs` onto `public/spark/shared/` before this load. Those copies match `lib/` on this commit. They are not part of this PR.

### API and well-known routes

Server handlers. No row in `route-bundle-stats.json`. Not opened as documents. No world, no sun, no render loop, no first-load JS, no phone boot.

`/.well-known/ai-catalog.json`, `/.well-known/mcp-server-card`, `/.well-known/mcp.json`, `/.well-known/mcp/catalog.json`, `/.well-known/oauth-authorization-server/[[...path]]`, `/.well-known/oauth-protected-resource/[[...path]]`, `/api/account`, `/api/account/verify`, `/api/bio-connection`, `/api/bio-connection/packet`, `/api/bridge/[endpoint]`, `/api/classroom`, `/api/companion-release`, `/api/cosmos/activity`, `/api/cosmos/beasts`, `/api/cosmos/beasts/[id]`, `/api/cosmos/liveness`, `/api/cosmos/private/beasts`, `/api/cosmos/private/beasts/[id]`, `/api/cosmos/private/pair`, `/api/cosmos/private/session`, `/api/environment`, `/api/gba-experience`, `/api/gba-release`, `/api/gba-rom`, `/api/genesis-3d-release`, `/api/genesis-release`, `/api/guest`, `/api/guest-growing`, `/api/guest/forever`, `/api/mcp`, `/api/mcp/server-card`, `/api/muse/[action]`, `/api/muse/oauth/[step]`, `/api/release`, `/api/session`, `/api/spark/chat`, `/api/status`, `/api/talk`, `/api/teacher-pairs`, `/api/teacher/ollama`, `/api/voice`, `/api/web-search`, `/api/world/live`, `/api/zeref/cloud-sync`, `/api/zeref/diary` (revalidate 2 min), `/api/zeref/library`, `/api/zeref/library/search`, `/api/zeref/library/training`, `/api/zeref/loop-status`, `/api/zeref/perception`, `/api/zeref/presence`, `/api/zeref/sensorium`, `/api/zeref/spark-pulse`, `/manifest.webmanifest`.

`/api/cosmos/beasts` and `/api/cosmos/beasts/[id]` are the Azure door. `lib/cosmos/cosmos-store.mjs` stores `beasts/<id>/profile.json` (create-only), `state.json`, `diary.jsonl`, `latest.json` in Azure Blob. That state is the registered beast’s diary loop. The living world, the pocket, the pedestal, and the tiny map do not spawn from it. `/api/zeref/diary` reads the GitHub `zeref-diary` branch, not that blob. Zeref’s diary key on that route is the Moonwraith display id `bb-7f9c2a03`; the training identity `bb-deada969` is labeled beside it and is not merged (`app/api/zeref/diary/route.ts`).

## Cameras, as they exist today

| Name in the directive | Where it lives now | Whose state |
|---|---|---|
| Living | Menu id `world`. Scene `LivingWorld`. | `lw:universe` plus the world field |
| Pocket | Menu id `pocket`. Scene `CagePocketDimension`. | Pocket life brain, heaven, session beast |
| Beach | `beachCam` inside Living World, and the separate Beach Two toy | Shore override on the living scene; toy has its own `simTime` |
| Orbit | `beastbox.world.view.v1` value `orbit`, the pre-spawn camera, and `Universe3D` orbit | Living scene, or the tiny 3D scene |
| Look Closer | `/beast-cage/look` (same page as turntable) | Pedestal rig, wall-clock stage rig |
| Pedestal | `data-look-pedestal` on that page | Same page as Look Closer. It is a prop under a separate renderer |
| Tiny | `/universe`, the home button “Enter the tiny world”, and the Cage link “Tiny World” which goes to `/beast-cage/world` | Clock document on `/universe`; Living World scene on the other two |

`lib/world/world-map.mjs` already calls these puzzle pieces of one world. The pieces still own separate renderers.

## Option surfaces

Both sheets are `components/world-menu.tsx`. The model is `lib/world/world-options.mjs`. Home passes `context="home"` (`home-pocket.tsx`). Cage passes `context="cage"` (`beast-cage-portal.tsx`). `place` and `tools` and `about` are portal hosts. The scene fills them.

### Beast Cage menu (`context="cage"`, FAB “Habitat”)

| Item | Section | What it does now |
|---|---|---|
| Living world | View | `writeView('world')`. Hidden until a saved QBEAST exists. |
| Pocket explorer | View | `writeView('pocket')`. |
| Classic pixel sprite | View | `writeView('classic')`. Drives the pixel flag and the arena sprite overlay. |
| Beach view | Place, only while Living World is embedded and not spawned | `setBeachCam`. |
| Spawn in | Place, same guard | `setSpawned(true)`. |
| Watch your beast / Orbit view | Place | `setWatch`. |
| Full screen | Place | `onExpand` → full `LivingWorld`. |
| Spawn in · First person | Place nav | `writeViewMode('first')` and spawn. |
| View: First person / View: Orbit | Place nav, once spawned | `beastbox.world.view.v1`. |
| Weather | Tools | Cycles the pocket god-view weather. |
| Time: live cycle / day / dusk / night | Tools | Cycles the pocket god-view time. Separate from `oneSunAt`. |
| Drop a treat | Tools | `godRef.treat()`. |
| Plant a flower | Tools | `godRef.flower()`. |
| Poke your Beast | Tools | `godRef.poke()`. |
| Who lives here | Tools | Opens the residents list on the scene. |
| Reset 3D camera | Diary | Dispatches `beastbox:pocket-3d-reset-camera`. |
| `{name}’s Diary` | Diary | `#zeref-diary` on this page. |
| Look Closer | Diary | `/beast-cage/look`, or `?with=zeref` when there is no saved beast. |
| Senses (camera & mic) | Senses | `/workspace#senses`. Does not enable the camera or mic. |
| Privacy and info | Senses | `/privacy`. |
| About host | About | Living World ⓘ chips when that view is embedded (`data-lw-info`). |
| Where am I in the one world? | About | Opens the site nav (`beastbox:open-site-nav`). |

On the Cage page, outside the sheet, and still part of this surface for the map: Friendly / Advanced (`beastbox-cage-mode-v1`), the creature switch (`beastbox.cage.creature.v1`), the journey nav, the hero links (Talk, Customize, Lost COSMOS), the quiet links (Tiny World → `/beast-cage/world`, Look Closer, Adventure walk, Field, Catch a Star, public generator, Workshop), geyser controls, the customize look cards, and the site dock. The dock and the site nav are global.

### Pocket options sheet (`context="home"`, FAB “Universe”)

Same rows as the Cage sheet, with these differences.

| Item | Difference |
|---|---|
| Classic pixel sprite | Hidden (`hideViews={['classic']}`). A saved classic choice still displays as pocket. |
| Sheet title | “Pocket universe options”. Diary href is `/beast-cage#zeref-diary`. |
| Enter the tiny world | Extra place row. Portals full `LivingWorld`. `data-open-living-world`. |
| Share my world’s signals | Extra. Opens environment consent. |
| Sound, game & help controls | Extra. Toggles `body` class `lc-tools-open`. |
| Pocket tools | Present when the pocket scene is mounted. Empty when the embedded Living World is showing (the GPU path, or after the guest has not picked pocket). |
| Place rows from Living World | Present on the GPU path and for a guest who has not picked pocket. Sea life stays on the canvas (`!embedded`). |
| About host | Living World ⓘ, and `homepage-creature.tsx` may also portal observatory controls into the same host. |

## Draft old-to-new menu map

Both sheets stay. Rows change job, they do not disappear. Classic, diary, senses, privacy, the world map, Friendly / Advanced, geyser, customize, and the journey links stay as they are.

| Today | On the one state |
|---|---|
| Living world | Camera: Living. Same land, same population. |
| Pocket explorer | Camera: Pocket. The pocket framing of that land. |
| Beach view | Camera: Beach. The shore framing. The noon sun override goes away when the light flag is on. Beach Two stays in the tree. |
| Watch / Orbit / view-mode Orbit | Camera: Orbit. |
| Look Closer | Camera: Look Closer. |
| Pedestal (`data-look-pedestal`) | Framing prop of the Look Closer camera. Turntable yaw buttons (0° / 90° / 180° / 270° / spin) stay as yaw presets. |
| Enter the tiny world, Tiny World link, `/universe` | Camera: Tiny, the expansion. `/universe` keeps drawing this same document. `u:3d` stays a 2D/3D switch of that drawing. |
| Spawn in / First person / Behind | Poses of the Living camera. |
| Full screen | Viewport. Not a new state. |
| Classic pixel sprite | Overlay on the one world. Still opt-in. |
| Weather, time, treat, flower, poke, who lives here | Same controls. They write the one population and the one clock. |
| Reset 3D camera | Resets whichever camera is active. |
| Diary | Still the diary. The recorded diary tick stays the diary tick. |
| Senses, Privacy, world map, Share signals, Sound controls | Unchanged targets. |

## Staged plan

Flags default off. Off means today’s code path. On is additive. No file in this list is deleted in these stages. A later deletion is out of this item until the owner says so, after the flags have been on and the before/after numbers exist. Each stage is its own PR, remeasures first-load JS and this EMULATED profile on the routes it touches, and ships the before numbers from this audit next to the after numbers. Flip is a follow-up, not the same commit as the code.

Suggested flag bag, empty by default: `localStorage` key `beastbox.oneUniverse.flags.v1` (comma list) and `NEXT_PUBLIC_ONE_UNIVERSE` for a deploy default. `?oneUniverse=` is a single-session override for the measurement, not a production flip.

| Stage | Flag | What turns on | What stays |
|---|---|---|---|
| 0 | none | This report. | The app. |
| 1 | `state` | Pocket, Look Closer, Beach Two, field, and the pedestal read `currentWorldClock()` for seed, tick, planets, storms. Living and Tiny already do. | Their own simulators and renderers keep running. |
| 2 | `light` | Key light and sky stops on every camera come from `oneSunAt` + `skyAtElevation` + `lightRigFor`, using that camera’s up vector. | `createPocketSky`, `stageRig`, `beastStudio`, genesis-sun, the beach noon vector, and `toy.js` lights remain in source and run while the flag is off. |
| 3 | `population` | One list: the session beast, plus `ARTIST_RESIDENTS`. If `/api/cosmos/beasts/:id` returns a registered Azure `state.json` / `latest.json`, that beast’s mood and diary fields come from the blob. Unregistered beasts stay on the device session and the UI says so. | Artist residents stay (no quantum seed, not Azure). The opt-in register button stays. |
| 4 | `tick` | World growth advances only in `oneWorldClock.step` (2 s, cap 4000, `grow()`, SIMULATED). Field and pocket presentation sample that tick. | The diary hash chain stays the recorded diary tick (Azure blob or the `zeref-diary` branch). It is not folded into `grow()`. |
| 5 | `cameras` | Living, Pocket, Beach, Orbit, and Look Closer are cameras on the living-world scene. The pedestal is the Look Closer framing. Tiny is the expansion camera of that scene. Both menus keep every row and write the camera id. | `/universe` 2D draw, Beach Two, the classic overlay, and the turntable page stay reachable. |
| 6 | none | Remeasure, then the owner flips. | No deletion in the flip commit. |

Honesty that the later PRs have to keep: world growth is SIMULATED, IBM genesis counts are RECORDED, the diary chain is the recorded diary, artist residents have no quantum seed, and an unregistered beast is a device beast. The beach camera does not get a private sun once `light` is on. Tiny does not get a private `grow()` once `tick` is on.

## Method

Build: `apps/beastbox-cloud`, `npm ci`, `npm run build` (Next.js 16.3.8, exit 0). `prebuild` refreshes `public/spark/shared/` from `lib/`. That refresh was left out of the commit. Next route bundles import `lib/`. Weights from `.next/diagnostics/route-bundle-stats.json`. Gzip computed locally from those chunk paths. `next-env.d.ts` type-path edits from the build were reverted.

Boot: `next start` on 127.0.0.1:3456. Playwright 1.55 Chromium headless, `--use-angle=swiftshader`. One route at a time so the CPU throttle is not shared. Fresh context per route, service workers blocked. Numbers above are that run. They are EMULATED.
