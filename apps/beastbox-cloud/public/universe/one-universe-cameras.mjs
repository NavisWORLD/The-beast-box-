// Stage 5, cameras. An empty bag is off. The Next bundle defaults the five flags on, and off clears that bag. Off does not read the clock and does not write a camera.
// On, a surface is a camera on the one world. Tiny is the expansion of that same document.
// The diary and the heartbeat stay on their own records. This file does not advance the world.
// NEXT_PUBLIC_ONE_UNIVERSE reaches only the Next client bundle, and only after a rebuild that inlines it.
// toy.js and spark/app.mjs do not read it. pageCamerasOn uses the query and localStorage only.
import {pageFlags} from './one-universe-gate.mjs';

export const CAMERA_IDS = Object.freeze(['living', 'pocket', 'beach', 'orbit', 'look', 'tiny']);
export const CAMERA_STORAGE = 'beastbox.oneUniverse.camera.v1';

const ENTRIES = Object.freeze([
  {id: 'living', label: 'Living world', camera: 'living', role: 'camera'},
  {id: 'pocket', label: 'Pocket explorer', camera: 'pocket', role: 'camera'},
  {id: 'classic', label: 'Classic pixel sprite', camera: null, role: 'overlay'},
  {id: 'beach', label: 'Beach view', camera: 'beach', role: 'camera'},
  {id: 'spawn', label: 'Spawn in', camera: 'living', role: 'pose'},
  {id: 'watch', label: 'Watch your beast', camera: 'orbit', role: 'camera'},
  {id: 'orbit-label', label: 'Orbit view', camera: 'orbit', role: 'camera'},
  {id: 'fullscreen', label: 'Full screen', camera: null, role: 'viewport'},
  {id: 'spawn-fp', label: 'Spawn in · First person', camera: 'living', role: 'pose'},
  {id: 'view-fp', label: 'View: First person', camera: 'living', role: 'pose'},
  {id: 'view-orbit', label: 'View: Orbit', camera: 'orbit', role: 'camera'},
  {id: 'weather', label: 'Weather:', camera: null, role: 'control'},
  {id: 'time', label: 'Time: live cycle', camera: null, role: 'control'},
  {id: 'treat', label: 'Drop a treat', camera: null, role: 'control'},
  {id: 'flower', label: 'Plant a flower', camera: null, role: 'control'},
  {id: 'poke', label: 'Poke your Beast', camera: null, role: 'control'},
  {id: 'residents', label: 'Who lives here', camera: null, role: 'control'},
  {id: 'reset', label: 'Reset 3D camera', camera: null, role: 'control'},
  {id: 'diary', label: 'Diary', camera: null, role: 'unchanged'},
  {id: 'look', label: 'Look Closer', camera: 'look', role: 'camera'},
  {id: 'senses', label: 'Senses (camera & mic)', camera: null, role: 'unchanged'},
  {id: 'privacy', label: 'Privacy and info', camera: null, role: 'unchanged'},
  {id: 'map', label: 'Where am I in the one world?', camera: null, role: 'unchanged'},
  {id: 'enter-tiny', label: 'Enter the tiny world', camera: 'tiny', role: 'expansion'},
  {id: 'share', label: 'Share my world', camera: null, role: 'unchanged'},
  {id: 'sound', label: 'Sound, game & help controls', camera: null, role: 'unchanged'},
  {id: 'tiny-link', label: 'Tiny World', camera: 'tiny', role: 'expansion'},
  {id: 'universe', label: 'data-universe-details', camera: 'tiny', role: 'expansion'},
  {id: 'beach-two', label: 'armStandalonePage', camera: 'beach', role: 'camera'},
  {id: 'turntable', label: 'Rotate 360°', camera: 'look', role: 'camera'},
  {id: 'pedestal', label: 'data-look-pedestal', camera: 'look', role: 'framing'},
]);

function envBits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

function cleanPath(path) {
  return String(path || '').split('?')[0].split('#')[0];
}

export function oneUniverseCamerasOn({env = '', storage = null, search = '', parentSearch = ''} = {}) {
  const flags = [...envBits(env), ...pageFlags({search, storage, parentSearch})];
  if (flags.includes('off')) return false;
  return flags.includes('cameras');
}

/** Next pages call this. The env name is inlined into the Next bundle only, after a rebuild. */
export function browserCamerasOn(sources) {
  if (sources) return oneUniverseCamerasOn(sources);
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
  return oneUniverseCamerasOn({env, storage, search});
}

export function resolveMenuEntry(id) {
  return ENTRIES.find((row) => row.id === id) || null;
}

export function cameraForPath(path) {
  const clean = cleanPath(path);
  if (clean === '/universe' || clean === '/beast-cage/world') return 'tiny';
  if (clean === '/beast-cage/look' || clean === '/beast-cage/turntable') return 'look';
  if (clean === '/beach-two' || clean === '/beach-two/toy.html') return 'beach';
  return null;
}

/** A fixed route keeps its camera. A stored menu choice wins on the cage and the home page. */
export function activeCamera({path = '', stored = null} = {}) {
  const clean = cleanPath(path);
  if (clean === '/universe') return 'tiny';
  if (clean === '/beast-cage/look' || clean === '/beast-cage/turntable') return 'look';
  if (clean === '/beach-two' || clean === '/beach-two/toy.html') return 'beach';
  if (CAMERA_IDS.includes(stored)) return stored;
  return cameraForPath(clean);
}

export function rememberCamera(storage, camera) {
  if (!CAMERA_IDS.includes(camera)) return false;
  try { storage?.setItem?.(CAMERA_STORAGE, camera); return true; } catch { return false; }
}

/**
 * Framing for one camera. Off does not read the world. On does not advance it.
 * @param {{on?: boolean, camera?: string|null, world?: any}} [opts]
 */
export function cameraFrame({on = false, camera = null, world = null} = {}) {
  if (!on) return {on: false, read: false, camera: null, grew: false, tick: null};
  if (!CAMERA_IDS.includes(camera)) {
    return {on: true, read: true, camera: null, grew: false, tick: null, seed: null, sky: null, population: null, expansion: false, pedestal: null};
  }
  const tick = world && Number.isInteger(world.tick) ? world.tick : null;
  const seed = world && typeof world.seed === 'string' ? world.seed : null;
  return {
    on: true,
    read: true,
    camera,
    seed,
    tick,
    grew: false,
    sky: 'one-sun',
    population: 'one',
    expansion: camera === 'tiny',
    pedestal: camera === 'look' ? 'framing' : null,
  };
}

function writeAttr(node, name, value) {
  if (!node || typeof node.setAttribute !== 'function') return;
  if (value == null) {
    if (typeof node.removeAttribute === 'function') node.removeAttribute(name);
    return;
  }
  node.setAttribute(name, String(value));
}

/**
 * Publish the camera id. Off does not read the clock. A missing tick is not written.
 * @param {{on?: boolean, camera?: string|null, path?: string, stored?: string|null, node?: any, clock?: any}} [opts]
 */
export function publishUniverseCamera({on = false, camera = null, path = '', stored = null, node = null, clock = null} = {}) {
  if (!on) return {written: false, read: false, grew: false, camera: null, tick: null};
  const chosen = CAMERA_IDS.includes(camera) ? camera : activeCamera({path, stored});
  const world = clock && typeof clock.get === 'function' ? clock.get() : null;
  const frame = cameraFrame({on: true, camera: chosen, world});
  if (!frame.camera) {
    writeAttr(node, 'data-universe-camera', null);
    writeAttr(node, 'data-universe-expansion', null);
    writeAttr(node, 'data-universe-pedestal', null);
    writeAttr(node, 'data-universe-camera-tick', null);
    return {written: false, ...frame};
  }
  writeAttr(node, 'data-universe-camera', frame.camera);
  writeAttr(node, 'data-universe-expansion', frame.expansion ? 'tiny' : null);
  writeAttr(node, 'data-universe-pedestal', frame.pedestal);
  writeAttr(node, 'data-universe-camera-tick', frame.tick);
  return {written: true, ...frame};
}
