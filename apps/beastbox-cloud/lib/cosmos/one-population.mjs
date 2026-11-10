// Stage 3, population. An empty bag is off. The Next bundle defaults the five flags on, and off clears that bag. Off does not read Azure and adds no creature.
// On, a creature is copied from beasts/<id>/state.json only when that blob was present.
// The label is the source written on that document (source_path, otherwise birth_spark.source,
// otherwise the state.json path that was read). A missing blob, a bad document, or an
// unconfigured store contributes nothing.
// NEXT_PUBLIC_ONE_UNIVERSE reaches only the Next client bundle, and only after a rebuild that inlines it.
// toy.js and spark/app.mjs do not read it. pagePopulationOn uses the query and localStorage only.
import {pageFlags} from '../../public/universe/one-universe-gate.mjs';

function envBits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

export function oneUniversePopulationOn({env = '', storage = null, search = '', parentSearch = ''} = {}) {
  const flags = [...envBits(env), ...pageFlags({search, storage, parentSearch})];
  if (flags.includes('off')) return false;
  return flags.includes('population');
}

/** Next pages call this. The env name is inlined into the Next bundle only, after a rebuild. */
export function browserPopulationOn(sources) {
  if (sources) return oneUniversePopulationOn(sources);
  let storage = null;
  let search = '';
  let env = '';
  try { storage = globalThis.localStorage || null; } catch {}
  try { search = (globalThis.location && globalThis.location.search) || ''; } catch {}
  try {
    if (globalThis.parent && globalThis.parent !== globalThis) {
      const ps = (globalThis.parent.location && globalThis.parent.location.search) || '';
      if (ps) search = search ? search + '&' + ps.replace(/^\?/, '') : ps;
    }
  } catch {}
  try { env = (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_ONE_UNIVERSE) || ''; } catch {}
  return oneUniversePopulationOn({env, storage, search});
}

function text(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : '';
}

function realSource(state, path) {
  const idn = state && state.identity;
  if (!idn || typeof idn !== 'object') return '';
  const written = text(idn.source_path);
  if (written) return written;
  const spark = idn.birth_spark;
  const spoken = spark && typeof spark === 'object' ? text(spark.source) : '';
  if (spoken) return spoken;
  const feed = text(path);
  return feed.endsWith('/state.json') ? feed : '';
}

function oneCreature(row) {
  if (!row || row.present !== true || !row.state || typeof row.state !== 'object') return null;
  const idn = row.state.identity;
  const id = idn && text(idn.beast_id);
  if (!id) return null;
  const source = realSource(row.state, row.path);
  if (!source) return null;
  const name = text(idn.name);
  return {
    id,
    name: name || id,
    source,
    mood: text(row.state.mood) || null,
    tick: Number.isFinite(row.state.tick) ? row.state.tick : null,
    lastEntryHash: text(row.state.last_entry_hash) || null,
    lastTickAt: text(row.state.last_tick_at) || null,
  };
}

/** Azure state.json rows only. Off, or a missing document, returns an empty list. */
export function creaturesFromStateFeed({on = false, read = null, documents = null} = {}) {
  if (!on) return [];
  const rows = typeof read === 'function' ? read() : documents;
  if (!Array.isArray(rows)) return [];
  const out = [];
  for (const row of rows) {
    const creature = oneCreature(row);
    if (creature) out.push(creature);
  }
  return out;
}

/**
 * Turn blob reads into the Azure list. A missing blob, bad JSON, or a file that is not state.json is skipped.
 * @param {{configured?: boolean, blobs?: any[]|null}} [opts]
 */
export function populationFromBlobs({configured = false, blobs = null} = {}) {
  if (!configured || !Array.isArray(blobs)) return [];
  const documents = [];
  for (const blob of blobs) {
    if (!blob || blob.missing || typeof blob.text !== 'string') continue;
    if (typeof blob.path !== 'string' || !blob.path.endsWith('/state.json')) continue;
    let state = null;
    try { state = JSON.parse(blob.text); } catch { state = null; }
    if (!state || typeof state !== 'object' || Array.isArray(state)) continue;
    documents.push({present: true, path: blob.path, state});
  }
  return creaturesFromStateFeed({on: true, documents});
}

function isArtist(creature) {
  return !!(creature && typeof creature.origin === 'string' && creature.origin.includes('NO QUANTUM SEED'));
}

function usableFeed(feed) {
  if (!Array.isArray(feed)) return [];
  return feed.filter((row) => row && typeof row.id === 'string' && row.id && typeof row.source === 'string' && row.source);
}

/**
 * Keep the existing list. When the flag is on, copy mood, diary fields, and the real source onto a
 * matching session beast, and append Azure rows that are not already in the list. Artist rows stay as they are.
 * Off, or an empty feed, returns the same list.
 * @param {{on?: boolean, creations?: any[], feed?: any[]|null}} [opts]
 */
export function applyPopulation({on = false, creations = [], feed = null} = {}) {
  const usable = on ? usableFeed(feed) : [];
  if (!usable.length) return creations;
  const base = Array.isArray(creations) ? creations : [];
  const used = new Set();
  let changed = false;
  const next = base.map((creature) => {
    if (!creature || isArtist(creature)) return creature;
    const hit = usable.find((row) => row.id === creature.id || (creature.cosmosId && row.id === creature.cosmosId));
    if (!hit) return creature;
    used.add(hit.id);
    changed = true;
    return {
      ...creature,
      source: hit.source,
      origin: hit.source,
      mood: typeof hit.mood === 'string' ? hit.mood : null,
      diaryTick: Number.isFinite(hit.tick) ? hit.tick : null,
      lastEntryHash: typeof hit.lastEntryHash === 'string' ? hit.lastEntryHash : null,
      lastTickAt: typeof hit.lastTickAt === 'string' ? hit.lastTickAt : null,
    };
  });
  for (const hit of usable) {
    if (used.has(hit.id)) continue;
    if (base.some((creature) => creature && (creature.id === hit.id || creature.cosmosId === hit.id))) continue;
    changed = true;
    next.push({
      id: hit.id,
      name: typeof hit.name === 'string' && hit.name ? hit.name : hit.id,
      kind: 'beast',
      genome: null,
      seed: null,
      origin: hit.source,
      look: null,
      art: null,
      cosmosId: hit.id,
      source: hit.source,
      mood: typeof hit.mood === 'string' ? hit.mood : null,
      diaryTick: Number.isFinite(hit.tick) ? hit.tick : null,
      lastEntryHash: typeof hit.lastEntryHash === 'string' ? hit.lastEntryHash : null,
      lastTickAt: typeof hit.lastTickAt === 'string' ? hit.lastTickAt : null,
    });
  }
  return changed ? next : creations;
}

/** Read the population route. A failed response is an empty list. */
export async function readPopulation(fetchImpl) {
  const go = typeof fetchImpl === 'function' ? fetchImpl : (typeof fetch === 'function' ? fetch : null);
  if (!go) return [];
  const res = await go('/api/cosmos/population', {cache: 'no-store'});
  if (!res || !res.ok) return [];
  const body = await res.json();
  return body && Array.isArray(body.creatures) ? body.creatures : [];
}
