/** Concept sprite pack v1 (owner-approved redraws) — presentation-only adapter.
 * Resolves ONLY by exact registered id or exact recorded genome seed. Never by display
 * name, alias or archetype. Anything unresolved (or any image that fails to load) keeps
 * the original procedural renderer. No random source: idle phase comes from the pack's
 * SHA-256 phase seed. Reduced motion always shows frame 0.
 */
export const CONCEPT_FRAME = 64, CONCEPT_FRAMES = 4;
export const CONCEPT_DURATIONS_MS = Object.freeze([1800, 300, 120, 300]);
export const CONCEPT_CYCLE_MS = CONCEPT_DURATIONS_MS.reduce((a, b) => a + b, 0);
// Registered identities that must stay on their original renderer, whatever the art says.
// bb-deada969 Zeref; bb-7f9c2a03 Moonwraith rig; bb-1e1759f3 registered Umbralet (dragonling);
// bb-4c633cb5 Pistonwyrm-Gearseed (pup; approximation disabled by the owner's review).
export const CONCEPT_EXCLUDED_IDS = Object.freeze(['bb-deada969', 'bb-7f9c2a03', 'bb-1e1759f3', 'bb-4c633cb5']);
export const CONCEPT_EXCLUDED_SEEDS = Object.freeze([
 '8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed', // Zeref
 'f67c3ba56f42fe7777a905745fa7b64f50aa0950859a8ddd829603a6bd33c4fd', // registered Umbralet dragonling
 '226bd3cafa2614315a4b538d6dcb26afe118800538fae7152c5fc2d13aa3fcad' // Gearseed
]);
export const CONCEPT_SPRITES = Object.freeze([
 {
  "slug": "pistonwyrm",
  "ids": [
   "bb-d41e5bd4"
  ],
  "seed": "e0126de4ff158eca0966e7627917001d5d355ca7139ec64375f2343cb954623a",
  "phaseSeed": "85966052c540cf55fe509b1a271cd2a6fa7cb6ae8b6eb6beef51d78e62932d85",
  "sheet": "/creatures/concept-v1/pistonwyrm/idle-64.png",
  "sheetHd": "/creatures/concept-v1/pistonwyrm/idle-128.png"
 },
 {
  "slug": "cindertot",
  "ids": [],
  "seed": "6fd8340cbc1a6d8db7f2544a421b36ebed5696aa8cf8df04df9a1f69152d1dcf",
  "phaseSeed": "4b12453cb050c43f666d2d5fee77522f1940cdea37cb8ee96300625e45155c80",
  "sheet": "/creatures/concept-v1/cindertot/idle-64.png",
  "sheetHd": "/creatures/concept-v1/cindertot/idle-128.png"
 },
 {
  "slug": "umbralet",
  "ids": [],
  "seed": "d44e211fa9787a428fa1606ddaabed0c9b424c32d56fd95933930299a79a1e07",
  "phaseSeed": "1b68273b817fedc264622888ea377fa5c57c841ecbfddb527e67d065e109c9c2",
  "sheet": "/creatures/concept-v1/umbralet/idle-64.png",
  "sheetHd": "/creatures/concept-v1/umbralet/idle-128.png"
 },
 {
  "slug": "halopip",
  "ids": [],
  "seed": "1a22a1c0a3bcbc73afa3f93381828ee529d9bb4ed8bbf5bbacc25d8b914bdc75",
  "phaseSeed": "86f691f7037620b4f85937816fad3a0ba6e83a5fdb47fa0cff39eeb6a9499368",
  "sheet": "/creatures/concept-v1/halopip/idle-64.png",
  "sheetHd": "/creatures/concept-v1/halopip/idle-128.png"
 },
 {
  "slug": "tidefin",
  "ids": [],
  "seed": "2577bd6b484b0cc2335a688c49c08ec112e6d8e1ca0cd339a956392c144b8213",
  "phaseSeed": "0d70e3beba3223213ab7093854b65164ea9f14a0d91a8a40ff1cb412bfb5cb5c",
  "sheet": "/creatures/concept-v1/tidefin/idle-64.png",
  "sheetHd": "/creatures/concept-v1/tidefin/idle-128.png"
 },
 {
  "slug": "fernling",
  "ids": [],
  "seed": "506af623ac66a2e7257164f17aeaa0247fb05b72b31c3cdbdeba11a505b2aa52",
  "phaseSeed": "e012da37f3a35c60c6b3a449a54e7a9a0be7d2add1135b3b9b5c5cf3e65149d5",
  "sheet": "/creatures/concept-v1/fernling/idle-64.png",
  "sheetHd": "/creatures/concept-v1/fernling/idle-128.png"
 }
].map(r => Object.freeze({ ...r, ids: Object.freeze(r.ids) })));

function idOf(x) { return String(x?.id || x?.qbeast?.profile?.id || x?.profile?.id || ''); }
/** @param {{id?:string, genome?:{seed?:string}|null, seed?:string}|null} who */
export function resolveConceptSprite(who) {
 try {
  if (!who || typeof who !== 'object') return null;
  const id = idOf(who) || idOf(who.genome);
  const seed = String(who.genome?.seed || who.seed || '');
  if (id && CONCEPT_EXCLUDED_IDS.includes(id)) return null;
  if (seed && CONCEPT_EXCLUDED_SEEDS.includes(seed)) return null;
  if (id) { const byId = CONCEPT_SPRITES.find(c => c.ids.includes(id)); if (byId) return (!seed || seed === byId.seed) ? byId : null; }
  if (!seed) return null;
  return CONCEPT_SPRITES.find(c => c.seed === seed) || null;
 } catch { return null; }
}
/** Deterministic frame index; reduced motion => 0. */
export function conceptFrameAt(entry, nowMs, reduced = false) {
 if (!entry || reduced || !Number.isFinite(nowMs)) return 0;
 const offset = parseInt(String(entry.phaseSeed).slice(0, 8), 16) % CONCEPT_CYCLE_MS;
 let t = (Math.floor(nowMs) + offset) % CONCEPT_CYCLE_MS;
 for (let i = 0; i < CONCEPT_FRAMES; i++) { if (t < CONCEPT_DURATIONS_MS[i]) return i; t -= CONCEPT_DURATIONS_MS[i]; }
 return 0;
}
/** Source rectangle for frame i on a sheet whose frames are `size` px square. */
export function conceptSourceRect(frame, size = CONCEPT_FRAME) {
 const f = Math.max(0, Math.min(CONCEPT_FRAMES - 1, frame | 0));
 return { sx: f * size, sy: 0, sw: size, sh: size };
}

// Bounded image cache (max 12 sheets: 6 creatures x native/HD). One request per URL.
const images = new Map(), failed = new Set();
/** Returns a decoded sheet or null (not loaded yet / failed / no DOM). onReady fires once after load. */
/** @param {any} entry @param {boolean} [hd] @param {()=>void} [onReady] */
export function conceptSheet(entry, hd = false, onReady) {
 if (!entry || typeof Image === 'undefined') return null;
 const url = hd ? entry.sheetHd : entry.sheet;
 if (failed.has(url)) return null;
 let rec = images.get(url);
 if (!rec) {
  if (images.size >= 12) return null;
  const img = new Image(); rec = { img, ok: false, waiters: [] }; images.set(url, rec);
  img.onload = () => { rec.ok = true; const w = rec.waiters; rec.waiters = []; w.forEach(f => { try { f(); } catch {} }); };
  img.onerror = () => { failed.add(url); images.delete(url); rec.waiters = []; };
  img.decoding = 'async'; img.src = url;
 }
 if (rec.ok) return rec.img;
 if (onReady && rec.waiters.length < 64) rec.waiters.push(onReady);
 return null;
}
/** Draw one frame. Returns true when concept art was drawn; false means the caller keeps the original. */
/** @param {any} ctx @param {any} entry @param {number} frame @param {number} dx @param {number} dy @param {number} dsize @param {{hd?:boolean, flip?:boolean, onReady?:()=>void}} [opts] */
export function drawConceptFrame(ctx, entry, frame, dx, dy, dsize, { hd = false, flip = false, onReady } = {}) {
 const img = conceptSheet(entry, hd, onReady);
 if (!img || !ctx) return false;
 const size = hd ? CONCEPT_FRAME * 2 : CONCEPT_FRAME, r = conceptSourceRect(frame, size);
 ctx.imageSmoothingEnabled = false;
 if (flip) { ctx.save(); ctx.translate(dx + dsize, dy); ctx.scale(-1, 1); ctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, 0, 0, dsize, dsize); ctx.restore(); }
 else ctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, dx, dy, dsize, dsize);
 return true;
}
/** Test hook only. */
export function _resetConceptCache() { images.clear(); failed.clear(); }
/** Replace a whole square thumbnail canvas with concept art when the genome resolves.
 * Returns true if concept art was drawn; otherwise the caller's original blit stands. */
/** @param {any} ctx @param {any} genome @param {number} size @param {{frame?:number, onReady?:()=>void}} [opts] */
export function paintConceptThumb(ctx, genome, size, { frame = 0, onReady } = {}) {
 const entry = resolveConceptSprite({ genome });
 if (!entry || !ctx) return false;
 const img = conceptSheet(entry, size > CONCEPT_FRAME, onReady);
 if (!img) return false;
 ctx.clearRect(0, 0, size, size);
 return drawConceptFrame(ctx, entry, frame, 0, 0, size, { hd: size > CONCEPT_FRAME, flip: genome?.facing !== 'left' });
}
