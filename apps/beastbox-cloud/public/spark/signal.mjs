/** cosmic-muse-traits-v1. Simulated windows match beastgen/signal.py. Raw samples are discarded. */

import { pyRound } from "./engine.mjs";
import { shaFrac } from "./sha.mjs";

export const SCHEMA = "cosmic-muse-traits-v1";
export const EEG_RATE = 256;
export const WINDOW = 256;
export const DEFAULT_BUCKET = 10;
export const DEFAULT_WINDOWS = 8;

export const PROFILES = {
  mock: { 10: 30, 20: 8, 40: 4 },
  serene: { 10: 34, 6: 10, 20: 5, 38: 3 },
  focused: { 20: 30, 10: 10, 24: 12, 40: 5 },
  sparky: { 40: 26, 35: 14, 20: 10, 10: 8 },
  dreamy: { 6: 30, 2: 16, 10: 14, 40: 3 },
  balanced: { 10: 18, 20: 18, 40: 18, 6: 8 },
  restless: { 20: 22, 40: 20, 3: 12, 10: 6 },
  steady: { 10: 22, 18: 22, 6: 6, 42: 4 },
};

export function validate(traits) {
  const out = {};
  for (const k of ["focus", "calm", "spark"]) {
    const v = traits[k];
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0 || v > 100) throw new Error(`trait ${k} must be a number in 0..100`);
    out[k] = Math.round(v);
  }
  return out;
}

export function bandPowers(samples, rate = EEG_RATE) {
  const n = samples.length;
  const bands = { delta: 0, theta: 0, alpha: 0, beta: 0, gamma: 0 };
  for (let k = 1; k < (n >> 1); k++) {
    const freq = k * rate / n;
    if (freq >= 45) break;
    let re = 0, im = 0;
    for (let i = 0; i < n; i++) {
      const ang = -2 * Math.PI * k * i / n;
      re += samples[i] * Math.cos(ang);
      im += samples[i] * Math.sin(ang);
    }
    const p = re * re + im * im;
    if (freq < 4) bands.delta += p;
    else if (freq < 8) bands.theta += p;
    else if (freq < 13) bands.alpha += p;
    else if (freq < 30) bands.beta += p;
    else bands.gamma += p;
  }
  return bands;
}

export function deriveTraits(b) {
  const s = b.delta + b.theta + b.alpha + b.beta + b.gamma;
  const r = (x) => (s > 0 ? Math.max(0, Math.min(100, Math.floor(100 * x / s + 0.5))) : 0);
  return { focus: r(b.beta), calm: r(b.alpha), spark: r(b.gamma) };
}

function samplesFor(amps) {
  const samples = [];
  const entries = Object.entries(amps).map(([f, a]) => [Number(f), a]);
  for (let i = 0; i < WINDOW; i++) {
    let s = 0;
    for (const [f, a] of entries) s += a * Math.sin(2 * Math.PI * f * (i / EEG_RATE));
    samples.push(s);
  }
  return samples;
}

export function simulate(profile = "mock") {
  const samples = samplesFor(PROFILES[profile]);
  const traits = deriveTraits(bandPowers(samples));
  samples.length = 0;
  return { schema: SCHEMA, mode: "simulated", profile, ...traits };
}

export function simulateWindows(profile = "mock", n = DEFAULT_WINDOWS, jitter = 0.18, salt = "") {
  const out = [];
  for (let w = 0; w < n; w++) {
    const amps = {};
    for (const [f, a] of Object.entries(PROFILES[profile])) {
      const u = shaFrac(`${profile}:${salt}:${w}:${f}`);
      amps[f] = w ? a * (1 + jitter * (2 * u - 1)) : a;
    }
    const samples = samplesFor(amps);
    out.push(deriveTraits(bandPowers(samples)));
    samples.length = 0;
  }
  return out;
}

function median(values) {
  const s = values.slice().sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export function stabilize(windows, bucket = DEFAULT_BUCKET) {
  if (!windows.length) throw new Error("need at least one window");
  const med = {};
  for (const k of ["focus", "calm", "spark"]) med[k] = median(windows.map((w) => validate(w)[k]));
  const b = Math.max(1, bucket | 0);
  const out = {};
  for (const k of ["focus", "calm", "spark"]) out[k] = Math.min(100, Math.max(0, pyRound(med[k] / b) * b));
  return out;
}

export function simulateStable(profile = "mock", n = DEFAULT_WINDOWS, bucket = DEFAULT_BUCKET) {
  const t = stabilize(simulateWindows(profile, n), bucket);
  return { schema: SCHEMA, mode: "simulated", profile, stabilization: { method: "median", windows: n, bucket }, ...t };
}
