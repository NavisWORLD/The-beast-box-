/**
 * Node-transform rig driver for the light chars3d models (no skins, no baked clips). Pure maths: a rig json plus
 * a time in seconds in, a list of node transform deltas out. No three.js import, no clock, no random: the caller
 * passes its own time. The formulas are Cosmo's (chars3d README / render.html): idle breathes and sways, blink
 * closes the eye nodes at SEEDED event times, walk bobs, hop is a parabola, wave raises the creature-right limb,
 * sleep squashes, tilts and nods with the eyes shut. Amplitudes are SIMULATED, timings SEEDED; nothing is measured.
 */
export const NODE_RIG_FORMAT = 'chars3d-node-rig-v1';
export const NODE_ACTIONS = Object.freeze(['idle', 'walk', 'hop', 'wave', 'sleep']);
const TAU = Math.PI * 2;
const clamp01 = x => (x < 0 ? 0 : x > 1 ? 1 : x);

/** Slot role (creature-model-slot roleFor) to rig action. */
export const ROLE_TO_ACTION = Object.freeze({idle: 'idle', walk: 'walk', happy: 'wave', startle: 'hop', sleep: 'sleep'});

export function isNodeRig(rig) { return !!rig && rig.rig_format === NODE_RIG_FORMAT; }

export function validateNodeRig(rig) {
  const errors = [];
  if (!rig || typeof rig !== 'object') return ['rig json is not an object'];
  if (typeof rig.root !== 'string' || !rig.root) errors.push('root node name missing');
  if (!rig.actions || typeof rig.actions !== 'object') errors.push('actions missing');
  else for (const a of ['idle']) if (!rig.actions[a]) errors.push('action "' + a + '" missing');
  if (rig.eyes && (!Array.isArray(rig.eyes.nodes) || !(rig.eyes.closed_scale_y >= 0 && rig.eyes.closed_scale_y <= 1))) errors.push('eyes needs nodes and closed_scale_y in 0..1');
  const lists = [];
  for (const a of Object.values(rig.actions || {})) for (const k of ['head_sway', 'extra', 'gait', 'limbs', 'curl']) if (Array.isArray(a && a[k])) lists.push(...a[k]);
  for (const m of lists) if (!m || typeof m.node !== 'string' || !Array.isArray(m.axis) || m.axis.length !== 3 || !m.axis.every(Number.isFinite)) { errors.push('a limb entry has no node or axis'); break; }
  return errors;
}

/** A species variant (wisp_species.json) bends the family rig: amp multiplies idle amplitude, tempo divides periods, blink_hold scales blink timing. */
export function applyActionMultipliers(rig, mult = {}) {
  const amp = Number.isFinite(mult.amp) ? mult.amp : 1, tempo = Number.isFinite(mult.tempo) && mult.tempo > 0 ? mult.tempo : 1, bh = Number.isFinite(mult.blink_hold) && mult.blink_hold > 0 ? mult.blink_hold : 1;
  const A = JSON.parse(JSON.stringify(rig.actions));
  if (A.idle) { A.idle.amp_y *= amp; A.idle.amp_x *= amp; A.idle.period_s /= tempo; }
  for (const k of ['walk', 'hop', 'wave']) if (A[k] && A[k].period_s) A[k].period_s /= tempo;
  if (A.blink) { A.blink.events = A.blink.events.map(e => e * bh); A.blink.hold_s *= bh; A.blink.loop_s *= bh; }
  return {...rig, actions: A};
}

/** Eye closure 0..1 at time t: each SEEDED event closes, holds, then opens; the loop repeats. */
export function blinkClosure(blink, t) {
  if (!blink || !Array.isArray(blink.events) || !(blink.loop_s > 0)) return 0;
  const lt = ((t % blink.loop_s) + blink.loop_s) % blink.loop_s;
  let k = 0;
  for (const e of blink.events) {
    const d = lt - e;
    if (d < 0) continue;
    const v = d < blink.close_s ? d / blink.close_s : d < blink.close_s + blink.hold_s ? 1 : d < blink.close_s + blink.hold_s + blink.open_s ? 1 - (d - blink.close_s - blink.hold_s) / blink.open_s : 0;
    if (v > k) k = v;
  }
  return k;
}

class Acc {
  constructor() { this.nodes = {}; }
  n(name) { return this.nodes[name] || (this.nodes[name] = {p: [0, 0, 0], r: [], s: [1, 1, 1]}); }
  pos(name, x, y, z) { const n = this.n(name); n.p[0] += x; n.p[1] += y; n.p[2] += z; }
  rot(name, axis, deg) { if (deg) this.n(name).r.push([axis, deg * Math.PI / 180]); }
  scale(name, sx, sy, sz) { const n = this.n(name); n.s[0] *= sx; n.s[1] *= sy; n.s[2] *= sz; }
}

/**
 * Pose at time t. `action` is the layer on top of idle (walk, hop, wave, sleep, or idle), `w` its weight 0..1 (a
 * blend-in), `sleepK` how far into sleep 0..1. Returns {nodes:{name:{p:[dx,dy,dz], r:[[axis,rad]...], s:[sx,sy,sz]}}, eye:closure}.
 * p is added to the rest position, r is multiplied onto the rest rotation in order, s multiplies the rest scale.
 */
export function nodeRigPose(rig, t, {action = 'idle', w = 1, sleepK = 1} = {}) {
  const acc = new Acc(), H = rig.height_m || 1, A = rig.actions || {}, root = rig.root;
  const sq = (sx, sy) => acc.scale(root, sx, sy, sx);
  const I = A.idle;
  if (I) {
    const f = TAU * t / I.period_s + (I.phase || 0) * TAU;
    sq(1 - I.amp_x * Math.sin(f), 1 + I.amp_y * Math.sin(f));
    for (const m of I.head_sway || []) acc.rot(m.node, m.axis, m.deg * Math.sin(f - Math.PI / 2));
    for (const m of I.extra || []) acc.rot(m.node, m.axis, m.deg * Math.sin(f + (m.ph || 0) * TAU));
  }
  let eye = blinkClosure(A.blink, t);
  const a = A[action];
  if (a && action !== 'idle' && w > 0) {
    if (action === 'walk') {
      const f = TAU * t / a.period_s, sn = Math.sin(f), ab = Math.abs(sn);
      acc.pos(root, a.sway_frac * H * sn * w, a.bob_frac * H * ab * w, 0);
      acc.rot(root, [0, 0, 1], a.tilt_deg * sn * w);
      sq(1, 1 - a.squash * (1 - ab) * w);
      for (const m of a.gait || []) acc.rot(m.node, m.axis, m.deg * Math.sin(f + (m.ph || 0) * Math.PI) * w);
    } else if (action === 'hop') {
      const u = ((t / a.period_s) % 1 + 1) % 1;
      acc.pos(root, 0, a.height_frac * H * 4 * u * (1 - u) * w, 0);
      const st = a.stretch * Math.sin(Math.PI * u) * w;
      sq(1 - st * 0.5, 1 + st);
    } else if (action === 'wave') {
      const u = ((t / a.period_s) % 1 + 1) % 1, env = Math.pow(Math.sin(Math.PI * u), 0.6) * w, s = Math.sin(TAU * a.cycles * u);
      for (const m of a.limbs || []) acc.rot(m.node, m.axis, ((m.raise_deg || 0) * env) + m.deg * env * s);
      if (a.head_node) acc.rot(a.head_node, [0, 0, 1], a.head_deg * env * s);
      acc.rot(root, [0, 0, 1], a.lean_deg * env);
    } else if (action === 'sleep') {
      const k = clamp01(sleepK) * w;
      sq(1 + (a.sx - 1) * k, 1 + (a.sy - 1) * k);
      const br = Math.sin(TAU * t / (a.breath_period_s || 4.2)) * (a.breath_amp || 0) * k;
      acc.scale(root, 1, 1 + br, 1);
      acc.rot(root, [0, 0, 1], a.tilt_deg * k);
      if (a.head_node) acc.rot(a.head_node, a.nod_axis, a.nod_deg * k);
      for (const m of a.curl || []) acc.rot(m.node, m.axis, m.deg * k);
      eye = Math.max(eye, k);
    }
  }
  const closed = rig.eyes ? rig.eyes.closed_scale_y : 1;
  if (rig.eyes && eye > 0) for (const e of rig.eyes.nodes) acc.scale(e, 1, 1 - eye * (1 - closed), 1);
  return {nodes: acc.nodes, eye};
}
