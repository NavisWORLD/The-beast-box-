/**
 * Creature model slot: a generic way to drop in a delivered GLB plus a rig json for any creature,
 * with the existing sprite (or sculpted body) as the fallback. Pure helpers only (no three.js import,
 * no clock, no random). The runtime is components/creature-model-slot.ts.
 *
 * Files live in public/creatures3d/custom/: manifest.json, <id>.glb, <id>.rig.json. The manifest lists
 * the ids that have a delivered model. Nothing is listed until a real file is delivered.
 */
export const MODEL_SLOT_SCHEMA = 'beastbox-creature-model-slot-v1';
export const MODEL_SLOT_BASE = '/creatures3d/custom/';
import {isNodeRig, validateNodeRig} from './node-rig.mjs';
/** Clip roles the runtime understands; a rig json maps its own clip names onto these. */
export const CLIP_ROLES = Object.freeze(['idle', 'walk', 'sleep', 'happy', 'startle']);
const ROLE_RX = {idle: /idle|stand|breath/i, walk: /walk|run|trot|move/i, sleep: /sleep|nap|rest/i, happy: /happy|play|joy|greet/i, startle: /startle|scare|jump|hop/i};

export function validateRig(rig, id) {
  const errors = [];
  if (!rig || typeof rig !== 'object') return {ok: false, errors: ['rig json is not an object']};
  if (rig.schema !== MODEL_SLOT_SCHEMA) errors.push('schema must be ' + MODEL_SLOT_SCHEMA);
  if (rig.id !== id) errors.push('rig id "' + rig.id + '" does not match "' + id + '"');
  if (!(Number.isFinite(rig.height_m) && rig.height_m > 0 && rig.height_m < 100)) errors.push('height_m must be a number above 0');
  if (rig.forward !== undefined && !/^[+-][XYZ]$/.test(rig.forward)) errors.push('forward must look like +Z');
  if (rig.clips !== undefined) {
    if (typeof rig.clips !== 'object' || Array.isArray(rig.clips)) errors.push('clips must map a role to a clip name');
    else for (const [role, name] of Object.entries(rig.clips)) {
      if (!CLIP_ROLES.includes(role)) errors.push('unknown clip role "' + role + '"');
      if (typeof name !== 'string' || !name) errors.push('clip "' + role + '" needs a name');
    }
  }
  if (isNodeRig(rig)) errors.push(...validateNodeRig(rig));
  if (rig.sprite_fallback !== undefined && typeof rig.sprite_fallback !== 'string') errors.push('sprite_fallback must be a url string');
  if (typeof rig.honesty !== 'string' || rig.honesty.length < 8) errors.push('honesty: say what the model is and is not (artist-made, not measured, and so on)');
  return {ok: errors.length === 0, errors};
}

/** Manifest entry for an id, or null. A manifest is {schema, models:{id:{glb, rig, glb_low?}}}. */
export function resolveModelEntry(manifest, id, base = MODEL_SLOT_BASE) {
  const m = manifest && manifest.models && manifest.models[id];
  if (!m || typeof m !== 'object') return null;
  const file = (f, fb) => (typeof f === 'string' && /^[A-Za-z0-9_.\-]+$/.test(f) ? base + f : fb);
  const glb = file(m.glb, base + id + '.glb'), rig = file(m.rig, base + id + '.rig.json');
  return {id, glb, rig, glbLow: m.glb_low ? file(m.glb_low, null) : null, bytes: Number.isFinite(m.bytes) ? m.bytes : null, tris: Number.isFinite(m.tris) ? m.tris : null, tier: m.tier === 'heavy' ? 'heavy' : 'light', variants: m.variants && typeof m.variants === 'object' ? m.variants : null};
}

/** Which clip name plays a role: the rig's own mapping first, then a name match. */
export function pickClipName(names, role, rigClips = {}) {
  if (rigClips[role] && names.includes(rigClips[role])) return rigClips[role];
  const rx = ROLE_RX[role];
  return rx ? (names.find(n => rx.test(n)) || null) : null;
}

/** Uniform scale that makes a model of measured height `h` (m) stand `target` tall. */
export function fitScale(h, target) {
  return Number.isFinite(h) && h > 1e-6 && Number.isFinite(target) && target > 0 ? target / h : 1;
}

/** Which role a creature should be playing: speed and mood in, role out. Deterministic. */
export function roleFor({speed = 0, sleep = 0, startle = 0, joy = 0} = {}) {
  if (sleep > 0.5) return 'sleep';
  if (startle > 0.5) return 'startle';
  if (speed > 0.12) return 'walk';
  if (joy > 0.75) return 'happy';
  return 'idle';
}

/**
 * Size budget so phones never load a heavy model. A manifest entry declares bytes and tris; the runtime also
 * checks the real downloaded size. Phone limits fit the light chars3d models (all under 140 KB and 4k tris);
 * the sculpted res_* beasts (0.47-3 MB, 33k-49k tris) are over them by design.
 */
export const MODEL_BUDGET = Object.freeze({phone: Object.freeze({bytes: 300000, tris: 8000}), desktop: Object.freeze({bytes: 8000000, tris: 120000})});
export function budgetFor(phone) { return phone ? MODEL_BUDGET.phone : MODEL_BUDGET.desktop; }
/** True when a declared or measured size fits. A missing number does not pass on a phone (unknown size is not light). */
export function withinBudget({bytes, tris} = {}, phone = false) {
  const b = budgetFor(phone);
  const ok = (v, max) => (Number.isFinite(v) ? v <= max : !phone);
  return ok(bytes, b.bytes) && ok(tris, b.tris);
}
/** Which tier a device gets: phones always the light models; a stronger device may take the heavy one when it declares enough memory and cores. */
export function deviceTier({phone = false, deviceMemory, cores} = {}) {
  if (phone) return 'light';
  return (deviceMemory === undefined || deviceMemory >= 4) && (cores === undefined || cores >= 4) ? 'heavy' : 'light';
}
/** Heavy sculpted GLBs (res_*) are only for the heavy tier; a phone keeps the light model or the sprite. */
export function heavyAllowed(device) { return deviceTier(device) === 'heavy'; }
