/**
 * cosmic-muse-traits-v1 plus the prototype's median-of-8, bucket-10 stabilizer.
 * Band powers come from the shared Muse client so a simulated headband matches
 * the handheld and the Synapse cage.
 */
import { bandPowers, deriveTraits, EEG_RATE, WINDOW, mockTraits } from './muse.mjs';
import { pyRound, sha256Bytes, u64Unit } from './hash.mjs';

export const SCHEMA = 'cosmic-muse-traits-v1';
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
  for (const key of ['focus', 'calm', 'spark']) {
    const value = traits?.[key];
    if (typeof value === 'boolean' || typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100) {
      throw new Error(`trait ${key} must be a number in 0..100`);
    }
    out[key] = pyRound(value);
  }
  return out;
}

export function samplesFor(amps) {
  const samples = new Float64Array(WINDOW);
  const freqs = Object.keys(amps);
  for (let i = 0; i < WINDOW; i++) {
    const t = i / EEG_RATE;
    let sum = 0;
    for (const freq of freqs) sum += amps[freq] * Math.sin(2 * Math.PI * Number(freq) * t);
    samples[i] = sum;
  }
  return samples;
}

export function simulate(profile = 'mock') {
  if (profile === 'mock') {
    const traits = mockTraits();
    return { schema: SCHEMA, mode: 'simulated', profile, ...traits };
  }
  const samples = samplesFor(PROFILES[profile]);
  const traits = deriveTraits(bandPowers(samples));
  samples.fill(0);
  return { schema: SCHEMA, mode: 'simulated', profile, ...traits };
}

export function simulateWindows(profile = 'mock', n = DEFAULT_WINDOWS, jitter = 0.18, salt = '') {
  const base = PROFILES[profile];
  const out = [];
  for (let w = 0; w < n; w++) {
    const amps = {};
    for (const freq of Object.keys(base)) {
      if (!w) amps[freq] = base[freq];
      else {
        const digest = sha256Bytes(`${profile}:${salt}:${w}:${freq}`);
        const unit = u64Unit(digest);
        amps[freq] = base[freq] * (1 + jitter * (2 * unit - 1));
      }
    }
    const samples = samplesFor(amps);
    out.push(deriveTraits(bandPowers(samples)));
    samples.fill(0);
  }
  return out;
}

export function stabilize(windows, bucket = DEFAULT_BUCKET) {
  if (!windows?.length) throw new Error('need at least one window');
  const b = Math.max(1, bucket | 0);
  const out = {};
  for (const key of ['focus', 'calm', 'spark']) {
    const values = windows.map((window) => validate(window)[key]).sort((a, c) => a - c);
    const mid = values.length % 2
      ? values[(values.length - 1) / 2]
      : (values[values.length / 2 - 1] + values[values.length / 2]) / 2;
    out[key] = Math.min(100, Math.max(0, pyRound(mid / b) * b)) | 0;
  }
  return out;
}

export function simulateStable(profile = 'mock', n = DEFAULT_WINDOWS, bucket = DEFAULT_BUCKET) {
  const traits = stabilize(simulateWindows(profile, n), bucket);
  return {
    schema: SCHEMA,
    mode: 'simulated',
    profile,
    stabilization: { method: 'median', windows: n, bucket },
    ...traits,
  };
}

export function bucketTraits(traits, bucket = DEFAULT_BUCKET) {
  const clean = validate(traits);
  if (bucket <= 1) return clean;
  const out = {};
  for (const key of ['focus', 'calm', 'spark']) {
    out[key] = Math.min(100, pyRound(clean[key] / bucket) * bucket) | 0;
  }
  return out;
}
