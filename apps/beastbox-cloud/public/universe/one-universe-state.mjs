// Stage 1 of one universe. The flag defaults off. Off does not read lw:universe and does not write a surface.
// On copies seed, tick, planets and storms from the one clock. The copy is a read: simulators keep their own state.
// Deterministic. The copy uses the clock document only.
export const ONE_UNIVERSE_FLAG_KEY = 'beastbox.oneUniverse.flags.v1';
export const ONE_UNIVERSE_QUERY = 'oneUniverse';
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

function bits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

export function oneUniverseFlags({env = '', storage = null, search = ''} = {}) {
  const out = bits(env);
  try {
    out.push(...bits(storage && typeof storage.getItem === 'function' ? storage.getItem(ONE_UNIVERSE_FLAG_KEY) || '' : ''));
  } catch {}
  try {
    const raw = typeof search === 'string' ? search : '';
    const params = new URLSearchParams(raw.charAt(0) === '?' ? raw.slice(1) : raw);
    out.push(...bits(params.get(ONE_UNIVERSE_QUERY) || ''));
  } catch {}
  return out;
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
