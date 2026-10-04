/** Beast Box 12D -> 54D port. Float rounding follows quantum_lifesource `.15g`. */

import { shaFrac } from "./sha.mjs";

export function pyRound(value, digits = 0) {
  const sign = value < 0 ? -1 : 1;
  const p = 10 ** digits;
  const y = Math.abs(value) * p;
  const fl = Math.floor(y);
  const frac = y - fl;
  let n;
  if (Math.abs(frac - 0.5) < 1e-8) n = (fl % 2 === 0) ? fl : fl + 1;
  else n = frac > 0.5 ? fl + 1 : fl;
  const rounded = sign * n / p;
  return digits === 0 ? rounded : Number(rounded.toFixed(digits));
}

export function py15g(x) {
  if (Object.is(x, -0) || x === 0) return 0;
  if (!Number.isFinite(x)) throw new Error("non-finite");
  const neg = x < 0;
  const ax = Math.abs(x);
  const exp = ax.toExponential(14);
  const v = Number(exp);
  return neg ? -v : v;
}

function finite12(values, name) {
  if (values.length !== 12) throw new Error(`${name} must contain exactly 12 values`);
  return values.map((value) => {
    const n = Number(value);
    if (!Number.isFinite(n)) throw new Error(`${name} must contain only finite values`);
    return n;
  });
}

function unit(values) {
  const vec = values.map(Number);
  const norm = Math.sqrt(vec.reduce((s, v) => s + v * v, 0));
  if (norm <= 1e-15) return vec.map(() => 0);
  return vec.map((value) => py15g(value / norm));
}

const OUTCOMES = ["00", "01", "10", "11"];

function probabilities(packet) {
  const counts = OUTCOMES.map((outcome) => Number(packet.counts[outcome] || 0));
  if (counts.some((value) => value < 0)) throw new Error("measurement counts cannot be negative");
  const declared = packet.shots === undefined ? counts.reduce((a, b) => a + b, 0) : Number(packet.shots);
  if (declared !== counts.reduce((a, b) => a + b, 0) || declared <= 0) throw new Error("measurement packet shot count is invalid");
  return counts.map((value) => py15g(value / declared));
}

export function packetsToDyn12(packets) {
  if (packets.length !== 3) throw new Error("dyn12 source adapter requires exactly three measurement packets");
  const out = [];
  for (const packet of packets) out.push(...probabilities(packet));
  return finite12(out, "quantum/control dyn12 drive");
}

export function mirrorStep(state1, sourceDrive) {
  const s1 = finite12(state1, "state1");
  const drive = finite12(sourceDrive, "source_drive");
  const observer = unit(s1.map((left, i) => (left + drive[i]) / 2));
  const feedback = unit(observer.map((obs, i) => obs - s1[i]));
  const coupled = drive.map((left, i) => py15g(Math.tanh(0.70 * left + 0.20 * observer[i] + 0.10 * feedback[i])));
  return { observer, feedback, coupled_drive: coupled };
}

export function gaussianAffinity(a, b, sigma = 0.75) {
  if (sigma <= 0) throw new Error("sigma must be positive");
  if (a.length !== b.length) throw new Error("state vectors must be same length");
  let d2 = 0;
  for (let i = 0; i < a.length; i++) d2 += (Number(a[i]) - Number(b[i])) ** 2;
  return Math.exp(-d2 / (2 * sigma * sigma));
}

function updateDyn12(state, drive, step) {
  const d = drive.length ? drive : [0];
  const out = [];
  for (let i = 0; i < 12; i++) {
    const u = Number(d[i % d.length]);
    const forcing = 0.015 * Math.sin((step + 1) * (i + 1) * 0.17320508075688773);
    out.push(Math.tanh(0.86 * Number(state[i]) + 0.14 * u + forcing));
  }
  return out;
}

function fit(values, n) {
  const src = values.length ? values.map(Number) : [0];
  const out = [];
  for (let i = 0; i < n; i++) out.push(src[i % src.length]);
  return out;
}

function coupledStep(state, drive, coupling = 0.06) {
  const s = state.map(Number);
  const d = fit(drive, s.length);
  const n = s.length;
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push(Math.tanh(0.90 * s[i] + 0.08 * d[i] + coupling * (s[(i - 1 + n) % n] - s[(i + 1) % n])));
  }
  return out;
}

export function stateFamily(steps, drives) {
  let dyn12 = Array(12).fill(0);
  let dyn42 = Array(42).fill(0);
  let step = 0;
  let dyn54 = Array(54).fill(0);
  for (const drive of drives) {
    step += 1;
    dyn12 = updateDyn12(dyn12, drive, step);
    dyn42 = coupledStep(dyn42, drive);
    dyn54 = dyn12.concat(dyn42);
    if (step === steps) break;
  }
  return { dyn12, dyn54 };
}

export function pairsFor(nb) {
  if (nb >= 6) return [[0, 1], [2, 3], [4, 5]];
  if (nb === 5) return [[0, 1], [2, 3], [4, 0]];
  return [[0, 1], [2, 3], [4, 0]].map(([a, b]) => [a % nb, b % nb]);
}

export function bitOf(bitstring, i) {
  return Number(bitstring[bitstring.length - 1 - i]);
}

export function quantumFeatures(counts) {
  const keys = Object.keys(counts);
  const shots = keys.reduce((s, k) => s + counts[k], 0);
  const nb = keys[0].length;
  const packets = pairsFor(nb).map(([a, b]) => {
    const c = { "00": 0, "01": 0, "10": 0, "11": 0 };
    for (const k of keys) c[`${bitOf(k, b)}${bitOf(k, a)}`] += counts[k];
    return { counts: c, shots };
  });
  const q12 = packetsToDyn12(packets);
  const margNb = [];
  for (let i = 0; i < nb; i++) {
    let n = 0;
    for (const k of keys) if (bitOf(k, i)) n += counts[k];
    margNb.push(n / shots);
  }
  const marg = [];
  for (let i = 0; i < Math.max(5, nb); i++) marg.push(margNb[i % nb]);
  let entropy = 0;
  for (const k of keys) {
    const p = counts[k] / shots;
    if (p > 0) entropy -= p * Math.log2(p);
  }
  entropy /= nb;
  const top = keys.slice().sort().reduce((best, k) => (counts[k] > counts[best] ? k : best));
  const countsTop = keys.slice().sort((a, b) => counts[b] - counts[a] || (a < b ? -1 : a > b ? 1 : 0)).slice(0, 4);
  return {
    q12, marginals: marg, marginals_measured: margNb, num_bits: nb, entropy_norm: entropy,
    top_state: top, counts_top: countsTop, top_frac: counts[top] / shots, packets,
  };
}

export function signalVector(traits) {
  const f = traits.focus / 100, c = traits.calm / 100, s = traits.spark / 100;
  const r = Math.max(0, 1 - f - c - s);
  const v = [f, c, s, r, f - c, s - c, f - s, 4 * f * c, 4 * c * s, 4 * s * f, Math.sin(2 * Math.PI * f + c), Math.cos(2 * Math.PI * s + c)];
  return v.map((x) => Math.max(-1, Math.min(1, x)));
}

export function fuse(traits, qf, steps = 9) {
  const s12 = signalVector(traits);
  const qdrive = qf.q12.map((p) => Math.max(-1, Math.min(1, (p - 0.25) * 6)));
  const mir = mirrorStep(s12, qdrive);
  const drives = [];
  for (let i = 0; i < steps; i++) drives.push(i % 3 ? mir.coupled_drive : s12);
  const st = stateFamily(steps, drives);
  return { signal12: s12, quantum_drive12: qdrive, coupled12: mir.coupled_drive, dyn12: st.dyn12, dyn54: st.dyn54 };
}

export class Stream {
  constructor(seed, label) {
    this.seed = seed;
    this.label = label;
    this.n = 0;
  }
  u() {
    const value = shaFrac(`${this.seed}:${this.label}:${this.n}`);
    this.n += 1;
    return value;
  }
  pick(items, weights = null) {
    const list = Array.from(items);
    const w = weights ? Array.from(weights) : list.map(() => 1);
    let x = this.u() * w.reduce((a, b) => a + b, 0);
    let acc = 0;
    for (let i = 0; i < list.length; i++) {
      acc += w[i];
      if (x < acc) return list[i];
    }
    return list[list.length - 1];
  }
  rng(lo, hi) { return lo + (hi - lo) * this.u(); }
}
