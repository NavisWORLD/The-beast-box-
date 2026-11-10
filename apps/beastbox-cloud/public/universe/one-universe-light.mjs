// Stage 2, light. An empty bag is off. The Next bundle defaults the five flags on, and off clears that bag. Off does not read the day clock and does not change a camera's lights.
// On, the key direction and the sky stops come from oneSunAt + skyAtElevation + lightRigFor for that camera's up.
// NEXT_PUBLIC_ONE_UNIVERSE reaches only the Next client bundle, and only after a rebuild that inlines it.
// toy.js does not read it. pageLightOn uses the query and localStorage only.
// Fill and rim stay. The old light constructors stay. The day clock is the caller's seconds.
import {pageFlags, pageLightOn, armCameraLight} from './one-universe-gate.mjs';
import {ONE_SUN, oneSunAt, skyAtElevation} from './one-sun.mjs';
import {lightRigFor} from './light-rig.mjs';

export {pageLightOn, armCameraLight};

function envBits(value) {
  if (typeof value !== 'string' || !value) return [];
  const out = [];
  for (const part of value.split(',')) {
    const t = part.trim();
    if (t) out.push(t);
  }
  return out;
}

export function oneUniverseLightOn({env = '', storage = null, search = '', parentSearch = ''} = {}) {
  const flags = [...envBits(env), ...pageFlags({search, storage, parentSearch})];
  if (flags.includes('off')) return false;
  return flags.includes('light');
}

/** Next pages call this. The env name is inlined into the Next bundle only, after a rebuild. */
export function browserLightOn() {
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
  return oneUniverseLightOn({env, storage, search});
}

export function cameraLight({sec, up = [0, 1, 0], exposure = 0.85} = {}) {
  const os = oneSunAt(sec, up);
  const sky = skyAtElevation(os.elevationDeg);
  const rig = lightRigFor(os, exposure);
  return {os, sky, rig, dir: os.dir.map((n) => n)};
}

/**
 * @param {{on?: boolean, lights?: any, sec?: number, up?: number[], exposure?: number, readSec?: Function}} [opts]
 */
export function applyCameraLight({on = false, lights, sec, up = [0, 1, 0], exposure = 0.85, readSec} = {}) {
  if (!on) return lights;
  const time = typeof readSec === 'function' ? readSec() : sec;
  const cam = cameraLight({sec: time, up, exposure});
  return {
    ...lights,
    key: {...(lights && lights.key), dir: cam.dir, intensity: cam.rig.sunIntensity},
    hemi: {...(lights && lights.hemi), color: cam.rig.hemiColor.slice(), intensity: cam.rig.hemiIntensity},
    sky: {zenith: cam.sky.zenith.slice(), horizon: cam.sky.horizon.slice(), stop: cam.sky.stop, starAlpha: cam.sky.starAlpha},
  };
}

export function beachSunDir({on = false, noon, sec, up = [0, 1, 0], readSec} = {}) {
  if (!on) return noon;
  const time = typeof readSec === 'function' ? readSec() : sec;
  return oneSunAt(time, up).dir.map((n) => n);
}

/** Which sun branch a camera takes. `noon` is the living-world __lwNoon value, not a direction.
 * @param {{lightOn?: boolean, beach?: boolean, noon?: any, hold?: boolean}} [opts]
 */
export function sunBranch({lightOn = false, beach = false, noon, hold = false} = {}) {
  if (!lightOn && beach && noon !== 'night') return 'noon';
  if (!lightOn && noon) return 'override';
  if (hold) return 'hold';
  return 'one-sun';
}

export function cssColor(rgb) {
  const h = (v) => Math.max(0, Math.min(255, Math.round(Number(v) * 255))).toString(16).padStart(2, '0');
  return '#' + h(rgb[0]) + h(rgb[1]) + h(rgb[2]);
}

/** Move an existing key and hemisphere onto the shared sun. No new light is created here.
 * @param {{on?: boolean, sec?: number, up?: number[], exposure?: number, key?: any, hemi?: any, readSec?: Function}} [opts]
 */
export function paintKeyAndSky({on = false, sec, up = [0, 1, 0], exposure, key, hemi, readSec} = {}) {
  if (!on) return false;
  const cam = cameraLight({sec: typeof readSec === 'function' ? readSec() : sec, up, exposure});
  if (key) {
    if (key.position && typeof key.position.set === 'function') {
      const x = +key.position.x || 0, y = +key.position.y || 0, z = +key.position.z || 0;
      const len = Math.hypot(x, y, z) || 1;
      key.position.set(cam.dir[0] * len, cam.dir[1] * len, cam.dir[2] * len);
    }
    if (key.intensity != null) key.intensity = cam.rig.sunIntensity;
    if (key.color && typeof key.color.setRGB === 'function') key.color.setRGB(ONE_SUN.linear[0], ONE_SUN.linear[1], ONE_SUN.linear[2]);
  }
  if (hemi) {
    const zenith = cam.sky.zenith, horizon = cam.sky.horizon;
    if (hemi.color && typeof hemi.color.setRGB === 'function') hemi.color.setRGB(zenith[0], zenith[1], zenith[2]);
    if (hemi.groundColor && typeof hemi.groundColor.setRGB === 'function') hemi.groundColor.setRGB(horizon[0], horizon[1], horizon[2]);
    if (hemi.intensity != null) hemi.intensity = cam.rig.hemiIntensity;
  }
  return cam;
}
