/**
 * Beast Box bridge: three 4-outcome packets -> dyn12 -> mirror_step -> dyn54.
 * Port of beastbox.quantum_lifesource + state_family + dyn12, used the same
 * way the Python prototype fuses a signal with recorded counts.
 */
import { py15g } from './hash.mjs';

const PAIRS = [[0, 1], [2, 3], [4, 0]];

export function pairsFor(nb) {
  if (nb >= 6) return [[0, 1], [2, 3], [4, 5]];
  if (nb === 5) return PAIRS.map((pair) => pair.slice());
  return PAIRS.map(([a, b]) => [a % nb, b % nb]);
}

export function bit(bitstring, i) {
  return Number(bitstring[bitstring.length - 1 - i]);
}

function unit(values) {
  let norm = 0;
  for (const value of values) norm += value * value;
  norm = Math.sqrt(norm);
  if (norm <= 1e-15) return values.map(() => 0);
  return values.map((value) => py15g(value / norm));
}

export function quantumFeatures(counts) {
  const keys = Object.keys(counts);
  let shots = 0;
  for (const key of keys) shots += counts[key];
  const nb = keys[0].length;
  const packets = [];
  for (const [a, b] of pairsFor(nb)) {
    const c = { '00': 0, '01': 0, '10': 0, '11': 0 };
    for (const key of keys) c[`${bit(key, b)}${bit(key, a)}`] += counts[key];
    const probs = ['00', '01', '10', '11'].map((outcome) => py15g(c[outcome] / shots));
    packets.push(probs);
  }
  const q12 = packets.flat();
  const margNb = [];
  for (let i = 0; i < nb; i++) {
    let ones = 0;
    for (const key of keys) if (bit(key, i)) ones += counts[key];
    margNb.push(ones / shots);
  }
  const marg = [];
  for (let i = 0; i < Math.max(5, nb); i++) marg.push(margNb[i % nb]);
  let entropy = 0;
  for (const key of keys) {
    const p = counts[key] / shots;
    if (p > 0) entropy -= p * Math.log2(p);
  }
  entropy /= nb;
  const ranked = keys.slice().sort((a, b) => (counts[b] - counts[a]) || (a < b ? -1 : a > b ? 1 : 0));
  const top = ranked[0];
  return {
    q12,
    marginals: marg,
    marginalsMeasured: margNb,
    numBits: nb,
    entropyNorm: entropy,
    topState: top,
    countsTop: ranked.slice(0, 4),
    topFrac: counts[top] / shots,
  };
}

export function signalVector(traits) {
  const f = traits.focus / 100;
  const c = traits.calm / 100;
  const s = traits.spark / 100;
  const r = Math.max(0, 1 - f - c - s);
  const values = [
    f, c, s, r, f - c, s - c, f - s, 4 * f * c, 4 * c * s, 4 * s * f,
    Math.sin(2 * Math.PI * f + c), Math.cos(2 * Math.PI * s + c),
  ];
  return values.map((value) => Math.max(-1, Math.min(1, value)));
}

function updateDyn12(state, drive, step) {
  const out = [];
  for (let i = 0; i < 12; i++) {
    const u = drive[i % drive.length];
    const forcing = 0.015 * Math.sin((step + 1) * (i + 1) * 0.17320508075688773);
    out.push(Math.tanh(0.86 * state[i] + 0.14 * u + forcing));
  }
  return out;
}

function coupledStep(state, drive, coupling = 0.06) {
  const n = state.length;
  const d = [];
  for (let i = 0; i < n; i++) d.push(drive[i % drive.length]);
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push(Math.tanh(0.90 * state[i] + 0.08 * d[i] + coupling * (state[(i - 1 + n) % n] - state[(i + 1) % n])));
  }
  return out;
}

export function mirrorStep(state1, sourceDrive) {
  const observer = unit(state1.map((left, i) => (left + sourceDrive[i]) / 2));
  const feedback = unit(observer.map((obs, i) => obs - state1[i]));
  const coupled = sourceDrive.map((left, i) => py15g(Math.tanh(0.70 * left + 0.20 * observer[i] + 0.10 * feedback[i])));
  return { observer, feedback, coupledDrive: coupled };
}

export function gaussianAffinity(a, b, sigma = 0.75) {
  let d2 = 0;
  for (let i = 0; i < a.length; i++) d2 += (a[i] - b[i]) ** 2;
  return Math.exp(-d2 / (2 * sigma * sigma));
}

export function fuse(traits, qf, steps = 9) {
  const s12 = signalVector(traits);
  const qdrive = qf.q12.map((p) => Math.max(-1, Math.min(1, (p - 0.25) * 6)));
  const mir = mirrorStep(s12, qdrive);
  let dyn12 = Array(12).fill(0);
  let dyn42 = Array(42).fill(0);
  for (let i = 0; i < steps; i++) {
    const drive = (i % 3 === 0) ? s12 : mir.coupledDrive;
    dyn12 = updateDyn12(dyn12, drive, i + 1);
    dyn42 = coupledStep(dyn42, drive);
  }
  return { signal12: s12, quantumDrive12: qdrive, coupled12: mir.coupledDrive, dyn12, dyn54: dyn12.concat(dyn42) };
}
