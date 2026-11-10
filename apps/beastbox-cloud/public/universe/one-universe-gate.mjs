// Flag gate for pages that are not the Next bundle.
// NEXT_PUBLIC_ONE_UNIVERSE is inlined into the Next client bundle at build time and is empty until that app is rebuilt with the variable set.
// This file does not read that variable. toy.js and spark/app.mjs never see it. They turn on only from the query or localStorage.
export const ONE_UNIVERSE_FLAG_KEY = 'beastbox.oneUniverse.flags.v1';
export const ONE_UNIVERSE_QUERY = 'oneUniverse';

function bits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

function queryBits(search) {
  if (typeof search !== 'string' || !search) return [];
  const raw = search.charAt(0) === '?' ? search.slice(1) : search;
  try {
    const params = new URLSearchParams(raw);
    return bits(params.get(ONE_UNIVERSE_QUERY) || '');
  } catch { return []; }
}

export function pageFlags({search = '', storage = null, parentSearch = ''} = {}) {
  const out = [];
  try {
    out.push(...bits(storage && typeof storage.getItem === 'function' ? storage.getItem(ONE_UNIVERSE_FLAG_KEY) || '' : ''));
  } catch {}
  out.push(...queryBits(search));
  out.push(...queryBits(parentSearch));
  return out;
}

export function pageStateOn(sources) {
  return pageFlags(sources).includes('state');
}

export function pageLightOn(sources) {
  return pageFlags(sources).includes('light');
}

export function pagePopulationOn(sources) {
  return pageFlags(sources).includes('population');
}

/**
 * Load the Azure population reader only when the population flag is on.
 * A failed load does not throw and does not add a creature.
 * @param {{on?: boolean, load?: Function}} [opts]
 */
export async function armPopulation({on = false, load} = {}) {
  if (!on) return {armed: false, failed: false, creatures: []};
  let mod;
  try { mod = await load(); }
  catch { return {armed: false, failed: true, creatures: []}; }
  try {
    const creatures = await mod.readPopulation();
    return {armed: true, failed: false, creatures: Array.isArray(creatures) ? creatures : []};
  } catch {
    return {armed: true, failed: true, creatures: []};
  }
}

/**
 * Load the shared sun only when the light flag is on. A failed load leaves the existing lights alone.
 * @param {{on?: boolean, lights?: any, load?: Function, sec?: any, up?: any, exposure?: number, key?: any, hemi?: any, subscribe?: Function}} [opts]
 */
export async function armCameraLight({on = false, lights, load, sec, up, exposure, key, hemi, subscribe} = {}) {
  if (!on) return {armed: false, failed: false, lights};
  let mod;
  try { mod = await load(); }
  catch { return {armed: false, failed: true, lights}; }
  try {
    const paint = () => mod.paintKeyAndSky({
      on: true,
      sec: typeof sec === 'function' ? sec() : sec,
      up: typeof up === 'function' ? up() : (up || [0, 1, 0]),
      exposure, key, hemi,
    });
    paint();
    if (typeof subscribe === 'function') subscribe(paint);
    return {armed: true, failed: false, lights};
  } catch {
    return {armed: false, failed: true, lights};
  }
}

/**
 * Load the world reader only when the flag is on. A failed load does not throw and does not write.
 * @param {{on?: boolean, surface?: string, load?: Function, win?: any, storage?: any, node?: any, fetchGenesis?: Function, subscribe?: Function}} [opts]
 */
export async function armStandalonePage({on = false, surface, load, win, storage, node, fetchGenesis, subscribe} = {}) {
  if (!on) return {loaded: false, armed: false, failed: false};
  let mod;
  try { mod = await load(); }
  catch { return {loaded: false, armed: false, failed: true}; }
  try {
    await mod.publishStandalone({surface, win, storage, node, fetchGenesis, subscribe});
    return {loaded: true, armed: true, failed: false};
  } catch {
    return {loaded: true, armed: false, failed: true};
  }
}
