// Stage 1 of one universe. An empty bag is off. The Next bundle defaults the five flags on, and off clears that bag. Off does not read lw:universe and does not write a surface.
// On copies seed, tick, planets and storms from the one clock. The copy is a read: simulators keep their own state.
// Deterministic. The copy uses the clock document only.
// NEXT_PUBLIC_ONE_UNIVERSE reaches only the Next client bundle, and only after a rebuild that inlines it.
// toy.js and spark/app.mjs do not read it. Their gate is one-universe-gate.mjs (query and localStorage only).
import {pageFlags, ONE_UNIVERSE_FLAG_KEY, ONE_UNIVERSE_QUERY} from './one-universe-gate.mjs';
export {ONE_UNIVERSE_FLAG_KEY, ONE_UNIVERSE_QUERY};
export const ONE_WORLD_KEY = 'lw:universe';

const NAMED = {
  '/': ['home'],
  '/beast-cage': ['cage'],
  '/beast-cage/world': ['tiny'],
  '/universe': ['universe'],
  '/beast-cage/look': ['look', 'pedestal'],
  '/beast-cage/turntable': ['look', 'pedestal'],
  '/beach-two': ['beach'],
  '/beach-two/toy.html': ['beach'],
  '/beast-cage/field': ['field'],
  '/beast-cage/go': ['field'],
  '/beast-cage/play': ['play'],
  '/beast-cage/talk': ['talk'],
  '/beast-cage/guest': ['guest'],
  '/sol-game': ['game'],
  '/workspace': ['workshop'],
  '/spark/index.html': ['spark'],
  '/settings': ['settings'],
  '/try': ['try'],
  '/research': ['research'],
  '/research/stage015': ['stage015'],
  '/brain-bay': ['brain-bay'],
  '/growing': ['growing'],
  '/loop': ['loop'],
  '/messages': ['messages'],
  '/account': ['account'],
  '/classroom': ['classroom'],
  '/mind-room': ['mind-room'],
  '/next': ['next'],
  '/privacy': ['privacy'],
  '/connect/meta-muse': ['meta-muse'],
  '/connect/meta-muse/pair': ['meta-muse-pair'],
};

function envBits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

export function oneUniverseFlags({env = '', storage = null, search = ''} = {}) {
  const flags = [...envBits(env), ...pageFlags({search, storage})];
  if (flags.includes('off')) return [];
  return flags;
}

export function oneUniverseStateOn(sources) {
  return oneUniverseFlags(sources).includes('state');
}

export function browserSources() {
  let storage = null;
  let search = '';
  try { storage = globalThis.localStorage || null; } catch {}
  try { search = (globalThis.location && globalThis.location.search) || ''; } catch {}
  try {
    if (globalThis.parent && globalThis.parent !== globalThis) {
      const ps = (globalThis.parent.location && globalThis.parent.location.search) || '';
      if (ps) search = search ? search + '&' + ps.replace(/^\?/, '') : ps;
    }
  } catch {}
  let env = '';
  // Next inlines this name into the client bundle. The public file served to toy.js and spark/app.mjs has no build-time value.
  try { env = (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_ONE_UNIVERSE) || ''; } catch {}
  return {env, storage, search};
}

export function surfacesForPath(path) {
  const clean = String(path || '/').split('?')[0].split('#')[0] || '/';
  return NAMED[clean] ? NAMED[clean].slice() : [clean];
}

function planetIds(list) {
  if (!Array.isArray(list)) return [];
  const ids = [];
  for (const planet of list) {
    if (planet && typeof planet.id === 'string') ids.push(planet.id);
  }
  return ids;
}

function stormFacts(list) {
  if (!Array.isArray(list)) return [];
  const out = [];
  for (const storm of list) {
    if (!storm || typeof storm !== 'object') continue;
    out.push({
      id: typeof storm.id === 'string' ? storm.id : null,
      planet: typeof storm.planet === 'string' ? storm.planet : null,
      intensity: typeof storm.intensity === 'number' ? storm.intensity : null,
    });
  }
  return out;
}

export function readOneWorld(getClock) {
  let world = null;
  try { world = typeof getClock === 'function' ? getClock() : null; } catch { return null; }
  if (!world || typeof world !== 'object') return null;
  return {
    schema: typeof world.schema === 'string' ? world.schema : null,
    seed: typeof world.seed === 'string' ? world.seed : null,
    tick: typeof world.tick === 'number' ? world.tick : null,
    planets: planetIds(world.planets),
    storms: stormFacts(world.storms),
  };
}

export function storedWorld(storage) {
  try {
    const raw = storage && typeof storage.getItem === 'function' ? storage.getItem(ONE_WORLD_KEY) : null;
    if (!raw) return null;
    const world = JSON.parse(raw);
    return world && typeof world === 'object' ? world : null;
  } catch { return null; }
}

export function readClockState(win, storage) {
  try {
    const clock = win && win.__bbOneWorld;
    if (clock && typeof clock.get === 'function') {
      const live = clock.get();
      if (live && typeof live === 'object') return live;
    }
  } catch {}
  return storedWorld(storage);
}

function publish(node, read, surface) {
  if (!node || !read || !node.dataset) return;
  const data = node.dataset;
  data.oneWorldRead = '1';
  data.oneWorldSurface = surface || '';
  data.oneWorldSeed = read.seed == null ? '' : String(read.seed);
  data.oneWorldTick = read.tick == null ? '' : String(read.tick);
  data.oneWorldPlanets = read.planets.join(',');
  data.oneWorldStorms = read.storms.map((storm) => storm.id || '').filter(Boolean).join(',');
  data.oneWorldSchema = read.schema == null ? '' : String(read.schema);
}

/**
 * @param {{on?: boolean, getClock?: Function, node?: any, nodes?: any[] | null, surface?: string, sim?: any}} [opts]
 */
export function attachOneWorldRead({on = false, getClock, node, nodes, surface, sim} = {}) {
  if (!on) return {subscribed: false, read: null, sim};
  const read = readOneWorld(getClock);
  if (read) {
    publish(node, read, surface);
    if (Array.isArray(nodes)) {
      for (const extra of nodes) publish(extra, read, surface);
    }
  }
  return {subscribed: true, read, sim};
}

/**
 * @param {{on?: boolean, getClock?: Function, node?: any, nodes?: any[] | null, surface?: string, sim?: any, subscribe?: Function}} [opts]
 */
export function watchOneWorldRead({on = false, getClock, node, nodes, surface, sim, subscribe} = {}) {
  attachOneWorldRead({on, getClock, node, nodes, surface, sim});
  if (!on) return () => {};
  let stop = () => {};
  if (typeof subscribe === 'function') {
    try {
      const unsub = subscribe(() => { attachOneWorldRead({on: true, getClock, node, nodes, surface, sim}); });
      if (typeof unsub === 'function') stop = unsub;
    } catch { stop = () => {}; }
  }
  return () => { try { stop(); } catch {} };
}

/**
 * Provider read. Flag off returns before the clock, the subscribe, and any surface write.
 * @param {{on?: boolean, whenClock?: Function, readNode?: Function, nodesFor?: Function, surfaceFor?: Function, subscribe?: Function, observe?: Function}} [opts]
 */
export function beginSurfaceRead({on = false, whenClock, readNode, nodesFor, surfaceFor, subscribe, observe} = {}) {
  if (!on) return () => {};
  let dead = false;
  let stop = () => {};
  let extra = () => {};
  Promise.resolve().then(() => (typeof whenClock === 'function' ? whenClock() : null)).then((clock) => {
    if (dead || !clock || typeof clock.get !== 'function') return;
    const apply = () => {
      attachOneWorldRead({
        on: true,
        getClock: () => clock.get(),
        node: typeof readNode === 'function' ? readNode() : null,
        nodes: typeof nodesFor === 'function' ? nodesFor() : [],
        surface: typeof surfaceFor === 'function' ? surfaceFor() : '',
      });
    };
    apply();
    try {
      const unsub = typeof subscribe === 'function' ? subscribe(clock, apply) : (typeof clock.subscribe === 'function' ? clock.subscribe(apply) : null);
      if (typeof unsub === 'function') stop = unsub;
    } catch {}
    try {
      const unobs = typeof observe === 'function' ? observe(apply) : null;
      if (typeof unobs === 'function') extra = unobs;
    } catch {}
  }).catch(() => {});
  return () => { dead = true; try { stop(); } catch {} try { extra(); } catch {} };
}

/**
 * Standalone page read. Prefers the live clock, then the stored lw:universe record, then the recorded genesis.
 * Does not start grow() and does not write lw:universe.
 * @param {{surface?: string, win?: any, storage?: any, node?: any, fetchGenesis?: Function, subscribe?: Function}} [opts]
 */
export async function publishStandalone({surface, win, storage, node, fetchGenesis, subscribe} = {}) {
  let live = null;
  try { live = win && win.__bbOneWorld; } catch { live = null; }
  if (live && typeof live.get === 'function') {
    watchOneWorldRead({
      on: true,
      getClock: () => readClockState(win, storage),
      node,
      surface,
      subscribe: typeof subscribe === 'function' ? subscribe : (fn) => (typeof live.subscribe === 'function' ? live.subscribe(fn) : () => {}),
    });
    return {source: 'clock'};
  }
  const stored = storedWorld(storage);
  if (stored) {
    attachOneWorldRead({on: true, getClock: () => stored, node, surface});
    return {source: 'stored'};
  }
  let genesis = null;
  try { genesis = typeof fetchGenesis === 'function' ? await fetchGenesis() : null; } catch { genesis = null; }
  if (!genesis) return {source: 'none'};
  attachOneWorldRead({on: true, getClock: () => genesis, node, surface});
  return {source: 'genesis'};
}
