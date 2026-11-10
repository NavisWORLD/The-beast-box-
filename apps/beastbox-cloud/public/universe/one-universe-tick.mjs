// Stage 4, tick. The flag defaults off. Off does not read the one clock and does not change a surface's own step.
// On, a surface shows the one clock's tick. A missing clock is no number.
// The diary tick and the heartbeat's recorded_tick stay on those records. They are not copied from the world tick.
// NEXT_PUBLIC_ONE_UNIVERSE reaches only the Next client bundle, and only after a rebuild that inlines it.
// toy.js and spark/app.mjs do not read it. pageTickOn uses the query and localStorage only.
import {pageFlags} from './one-universe-gate.mjs';

function envBits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

export function oneUniverseTickOn({env = '', storage = null, search = '', parentSearch = ''} = {}) {
  return [...envBits(env), ...pageFlags({search, storage, parentSearch})].includes('tick');
}

/** Next pages call this. The env name is inlined into the Next bundle only, after a rebuild. */
export function browserTickOn(sources) {
  if (sources) return oneUniverseTickOn(sources);
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
  return oneUniverseTickOn({env, storage, search});
}

/** An integer tick from a record. Anything else is no tick. */
export function displayTick(value) {
  return Number.isInteger(value) ? value : null;
}

/**
 * When the flag is on, the surface takes the clock document. It does not advance anything.
 * Off returns the same state and does not read the clock.
 * @param {{on?: boolean, state?: any, clock?: any}} [opts]
 */
export function nextWorldState({on = false, state = null, clock = null} = {}) {
  if (!on) return {read: false, state, grew: false, tick: null};
  const doc = clock && typeof clock.get === 'function' ? clock.get() : null;
  const tick = displayTick(doc && doc.tick);
  if (tick == null || doc == null) return {read: true, state, grew: false, tick: null};
  return {read: true, state: doc, grew: false, tick};
}

/**
 * Diary and heartbeat ticks come only from those records.
 * A world tick passed beside them is ignored.
 * @param {{diary?: any, heartbeat?: any, worldTick?: any}} [opts]
 */
export function progressionTicks({diary = null, heartbeat = null} = {}) {
  return {
    diary: diary && Number.isInteger(diary.tick) ? diary.tick : null,
    heartbeat: heartbeat && Number.isInteger(heartbeat.recorded_tick) ? heartbeat.recorded_tick : null,
  };
}

/**
 * Write the one tick onto a node. A missing tick removes the attribute.
 * @param {{on?: boolean, node?: any, tick?: any}} [opts]
 */
export function publishUniverseTick({on = false, node = null, tick = null} = {}) {
  if (!on || !node || typeof node.setAttribute !== 'function') return {written: false, tick: null};
  const shown = displayTick(tick);
  if (shown == null) {
    if (typeof node.removeAttribute === 'function') node.removeAttribute('data-universe-tick');
    return {written: false, tick: null};
  }
  node.setAttribute('data-universe-tick', String(shown));
  return {written: true, tick: shown};
}
