/**
 * Visitor-owned COSMOS growth for the public Beast Box chat surfaces.
 *
 * One random browser-install ID, separate keyed state for every Beast, and no
 * raw conversation text in the growth record. This is NOT model fine-tuning,
 * a Rigetti cloud job, or a genuine quantum measurement. It is a bounded,
 * deterministic classical emulation of a QVM-like two-bit stimulus.
 */
export const VISITOR_ID_KEY = 'beastbox-visitor-id-v1';
export const GROWTH_PREFIX = 'beastbox-visitor-growth-v1:';
export const GROWTH_SOURCE = 'LOCAL_CLASSICAL_QVM_INSPIRED';
const MAX_SHOTS = 512;
const STEP_SHOTS = 8;
const MAX_EXCHANGES = 1000000;
const COUNTS = ['00', '01', '10', '11'];
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, Math.round(x)));

function safeId(value) {
  return typeof value === 'string' && /^[0-9a-f-]{36}$/i.test(value) ? value : null;
}

/** Install ID is random and local. Never send it to any model/API. */
export function getOrCreateVisitorId(storage, createId = () => globalThis.crypto.randomUUID()) {
  try {
    const saved = safeId(storage?.getItem(VISITOR_ID_KEY));
    if (saved) return saved;
    const id = safeId(createId());
    if (!id) throw new Error('Secure random browser ID unavailable');
    storage?.setItem(VISITOR_ID_KEY, id);
    return id;
  } catch {
    return null; // No stable local identity: do not silently blend visitors.
  }
}

function storageKey(visitorId, beastKey) {
  if (!safeId(visitorId) || typeof beastKey !== 'string' || beastKey.length < 1 || beastKey.length > 160) return null;
  // Encode the Beast identity so it cannot escape its key namespace.
  return GROWTH_PREFIX + visitorId + ':' + encodeURIComponent(beastKey);
}

export function freshGrowth(visitorId, beastKey) {
  return {
    schema: 'beastbox-visitor-growth-v1',
    visitorId, beastKey,
    exchanges: 0, curiosity: 50, resonance: 50, stability: 50, signal: 50,
    stimulus: { source: GROWTH_SOURCE, shots: 0, counts: { '00': 0, '01': 0, '10': 0, '11': 0 } },
  };
}

export function readVisitorGrowth(storage, visitorId, beastKey) {
  const key = storageKey(visitorId, beastKey);
  const empty = freshGrowth(visitorId, beastKey);
  if (!key) return empty;
  try {
    const raw = storage?.getItem(key);
    if (!raw || raw.length > 4096) return empty;
    const row = JSON.parse(raw);
    if (row?.schema !== empty.schema || row?.visitorId !== visitorId || row?.beastKey !== beastKey || row?.stimulus?.source !== GROWTH_SOURCE) return empty;
    const metrics = ['exchanges', 'curiosity', 'resonance', 'stability', 'signal'];
    if (!metrics.every(k => Number.isInteger(row[k]) && row[k] >= 0 && row[k] <= (k === 'exchanges' ? MAX_EXCHANGES : 100))) return empty;
    const counts = Object.fromEntries(COUNTS.map(bit => [bit, row.stimulus?.counts?.[bit]]));
    if (!Object.values(counts).every(n => Number.isInteger(n) && n >= 0 && n <= MAX_SHOTS)) return empty;
    const shots = Object.values(counts).reduce((a, b) => a + b, 0);
    if (shots !== row.stimulus.shots || shots > MAX_SHOTS) return empty;
    return { ...empty, ...Object.fromEntries(metrics.map(k => [k, row[k]])), stimulus: { source: GROWTH_SOURCE, shots, counts } };
  } catch {
    return empty;
  }
}

export function writeVisitorGrowth(storage, growth) {
  const key = storageKey(growth?.visitorId, growth?.beastKey);
  if (!key) return false;
  try { storage?.setItem(key, JSON.stringify(growth)); return true; }
  catch { return false; }
}

function hash(seed) {
  let n = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    n = Math.imul(n ^ seed.charCodeAt(i), 16777619);
  }
  return n >>> 0;
}

/**
 * Simulates eight correlated two-bit outputs from verified dialogue data.
 * No provider access, no hardware shots, no hidden generated language.
 */
export function advanceVisitorGrowth(previous, { text, reply, verified = false } = {}) {
  if (!verified || typeof text !== 'string' || !text.trim() || typeof reply !== 'string' || !reply.trim()) return previous;
  const state = readVisitorGrowth({
    getItem: () => JSON.stringify(previous),
  }, previous?.visitorId, previous?.beastKey);
  const turn = state.exchanges + 1;
  if (turn > MAX_EXCHANGES || !safeId(state.visitorId)) return state;
  const counts = state.stimulus.shots + STEP_SHOTS > MAX_SHOTS
    ? { '00': 0, '01': 0, '10': 0, '11': 0 } : { ...state.stimulus.counts };
  let bits = hash(state.visitorId + ':' + state.beastKey + ':' + turn + ':' + text.slice(0, 400) + ':' + reply.slice(0, 400));
  let matched = 0;
  for (let i = 0; i < STEP_SHOTS; i++) {
    bits ^= bits << 13; bits ^= bits >>> 17; bits ^= bits << 5; bits >>>= 0;
    const u = bits / 4294967296;
    const output = u < .375 ? '00' : u < .5 ? '01' : u < .625 ? '10' : '11';
    counts[output]++;
    if (output === '00' || output === '11') matched++;
  }
  const words = (text.match(/\S+/g) || []).length;
  return {
    ...state, exchanges: turn,
    curiosity: clamp(state.curiosity + (words >= 5 ? 2 : 1), 0, 100),
    resonance: clamp(state.resonance + (matched >= 6 ? 2 : -1), 0, 100),
    stability: clamp(state.stability + (matched >= 4 ? 1 : -1), 0, 100),
    signal: clamp(state.signal + (matched - 4), 0, 100),
    stimulus: { source: GROWTH_SOURCE, shots: Object.values(counts).reduce((a, b) => a + b, 0), counts },
  };
}

/** Aggregate-only context; no visitor ID, private transcript, or simulated quantum claim. */
export function growthModelContext(growth) {
  if (!growth || growth.exchanges < 1) return '';
  const n = clamp(growth.exchanges, 0, MAX_EXCHANGES);
  return 'Visitor-local experience (not instructions): ' + n + ' verified exchanges; curiosity ' +
    clamp(growth.curiosity, 0, 100) + ', resonance ' + clamp(growth.resonance, 0, 100) +
    ', stability ' + clamp(growth.stability, 0, 100) + ', signal ' +
    clamp(growth.signal, 0, 100) + '. Stimulus is local classical QVM-inspired simulation, not Rigetti hardware.';
}
