/**
 * Seeded voice parameters. The browser synth in voice-synth.mjs speaks them.
 * Port of beastgen/voice.py.
 */
import { pyRound, sha256Bytes, u64Unit } from './hash.mjs';

const STYLES = ['chirp', 'purr', 'growl', 'trill', 'coo', 'beep'];
const SIZE = {
  pup: 0.50, fox: 0.52, sprout: 0.45, moth: 0.34, axolotl: 0.46, golem: 0.82, dragonling: 0.64,
  bird: 0.30, fish: 0.40, serpent: 0.58, biped: 0.50,
};
const STYLE_W = {
  pup: { purr: 3, chirp: 2, coo: 1, growl: 1 },
  fox: { chirp: 3, purr: 2, trill: 1 },
  sprout: { coo: 3, chirp: 2, trill: 1 },
  moth: { coo: 3, trill: 2, chirp: 2 },
  axolotl: { trill: 3, coo: 2, chirp: 1 },
  golem: { growl: 3, beep: 2, purr: 1 },
  dragonling: { growl: 3, chirp: 2, purr: 1 },
  bird: { chirp: 4, trill: 3 },
  fish: { trill: 3, coo: 2, chirp: 1 },
  serpent: { trill: 2, purr: 2, growl: 1, coo: 1 },
  biped: { chirp: 2, coo: 2, purr: 1, beep: 1 },
};
const ELEMENT_W = {
  machine: { beep: 6 }, ember: { growl: 2, chirp: 1 }, umbral: { coo: 2, purr: 1 }, crystal: { trill: 2, chirp: 1 },
  frost: { coo: 2, trill: 1 }, radiant: { chirp: 2, trill: 1 }, verdant: { chirp: 1, coo: 1 }, grove: { purr: 1, coo: 1 },
};
const TEMPER_W = {
  Serene: { coo: 1.5, purr: 1 }, Gentle: { purr: 1.5, coo: 1 }, Fierce: { growl: 2 }, Bold: { growl: 1, chirp: 1 },
  Playful: { chirp: 1.5, trill: 1 }, Curious: { chirp: 1.5, trill: 0.5 }, Dreamy: { coo: 2 }, Steadfast: { purr: 1, beep: 0.5 },
};
const STYLE_P = {
  chirp: [{ sine: 2, triangle: 3 }, [6.0, 9.0], [6, 9], [20, 60], 0, [0.02, 0.10]],
  purr: [{ triangle: 2, sawtooth: 1 }, [3.0, 4.6], [4, 6], [10, 30], [22, 30], [0.10, 0.25]],
  growl: [{ sawtooth: 3, square: 1 }, [2.8, 4.2], [4, 6], [20, 50], [30, 46], [0.12, 0.30]],
  trill: [{ sine: 2, triangle: 2 }, [4.5, 7.0], [14, 22], [90, 180], 0, [0.02, 0.10]],
  coo: [{ sine: 4, triangle: 1 }, [2.6, 4.0], [4, 6], [15, 40], 0, [0.06, 0.18]],
  beep: [{ square: 3, triangle: 1 }, [5.0, 8.0], [0, 0.01], [0, 1], 0, [0.0, 0.02]],
};
const CONSONANTS = {
  chirp: ['p', 't', 'ch', 'k', 'pi'], purr: ['mr', 'r', 'm', 'pr'], growl: ['gr', 'r', 'g', 'hr'],
  trill: ['tr', 'l', 'r', 'tl'], coo: ['w', 'm', 'h', 'n'], beep: ['b', 'd', 'bz', 't'],
};
const VOWELS = [['a', 800, 1200], ['e', 500, 1900], ['i', 320, 2500], ['o', 500, 900], ['u', 340, 800],
  ['ee', 300, 2700], ['aw', 650, 1000], ['ü', 300, 1700]];

class VoiceStream {
  constructor(seed, label) {
    this.seed = seed;
    this.label = label;
    this.n = 0;
  }

  u() {
    const digest = sha256Bytes(`${this.seed}:${this.label}:${this.n}`);
    this.n += 1;
    return u64Unit(digest);
  }

  rng(lo, hi) {
    return lo + (hi - lo) * this.u();
  }

  pick(weights) {
    const items = Object.entries(weights);
    const tot = items.reduce((sum, [, value]) => sum + value, 0);
    let x = this.u() * tot;
    let acc = 0;
    for (const [key, value] of items) {
      acc += value;
      if (x < acc) return key;
    }
    return items[items.length - 1][0];
  }
}

export function deriveVoice(seed, body, element, temperament, genes, qf, beh) {
  const V = new VoiceStream(seed, 'voice');
  const w = Object.fromEntries(STYLES.map((style) => [style, 0.2]));
  for (const src of [STYLE_W[body] || {}, ELEMENT_W[element] || {}, TEMPER_W[temperament] || {}]) {
    for (const [key, value] of Object.entries(src)) w[key] += value;
  }
  const style = V.pick(w);
  const [waves, sps, vib, cents, am, breath] = STYLE_P[style];
  const size = (SIZE[body] ?? 0.5) + 0.18 * (genes.chub - 0.5);
  let base = 980 * 2 ** (-1.7 * size) * 2 ** (0.6 * (V.u() - 0.5));
  if (style === 'growl') base *= 0.72;
  const measured = qf.marginalsMeasured;
  const m0 = measured[0];
  const m1 = measured[1 % measured.length];
  const f1 = 300 + 550 * m0 + 80 * (V.u() - 0.5);
  const f2 = 950 + 1500 * m1 + 200 * (V.u() - 0.5);
  const tops = qf.countsTop?.length ? qf.countsTop : [qf.topState];
  let vowelSeq = tops.slice(0, 4).map((bits) => Number.parseInt(bits, 2) % VOWELS.length);
  let vowelSrc = 'top outcomes of the run';
  if (new Set(vowelSeq).size < 2) {
    vowelSeq = vowelSeq.concat([0, 1, 2].map((i) => Number.parseInt(seed.slice(20 + 2 * i, 22 + 2 * i), 16) % VOWELS.length));
    vowelSrc = 'top outcomes + seed-hash (run has few distinct outcomes)';
  }
  let rhythm = qf.topState.split('').reverse().map((ch) => Number(ch)).slice(0, 8);
  let rhythmSource = 'top_state bits';
  if (rhythm.length < 5) {
    const sb = BigInt(`0x${seed.slice(24, 32)}`).toString(2).padStart(32, '0');
    rhythm = rhythm.concat([...sb.slice(0, 5 - rhythm.length)].map((ch) => Number(ch)));
    rhythmSource = 'top_state bit + seed-hash padding (1-bit run)';
  }
  const cons = CONSONANTS[style].slice();
  const k0 = Math.trunc(V.u() * cons.length);
  const consonants = cons.slice(k0).concat(cons.slice(0, k0));
  return {
    style,
    base_pitch_hz: pyRound(base, 1),
    formants_hz: [pyRound(f1), pyRound(f2)],
    formant_q: pyRound(V.rng(4.0, 9.0), 2),
    wave: V.pick(waves),
    brightness: pyRound(V.rng(0.2, 0.9), 3),
    breath: pyRound(V.rng(breath[0], breath[1]), 3),
    speed_sps: pyRound(V.rng(sps[0], sps[1]), 2),
    vibrato_hz: pyRound(V.rng(vib[0], vib[1]), 2),
    vibrato_cents: pyRound(V.rng(cents[0], cents[1]), 1),
    am_hz: am ? pyRound(V.rng(am[0], am[1]), 1) : 0,
    contour: V.pick({ rise: 1, fall: 1, arch: 1.3, bounce: 1 }),
    jump_semitones: pyRound(V.rng(2.0, 7.0), 2),
    rhythm,
    rhythm_source: rhythmSource,
    vowels: vowelSeq.map((i) => VOWELS[i][0]),
    vowel_formants: vowelSeq.map((i) => [VOWELS[i][1], VOWELS[i][2]]),
    vowel_source: vowelSrc,
    consonants,
    phrase_syllables: [2 + Math.trunc(V.u() * 2), 3 + Math.trunc(V.u() * 3)],
    gain: pyRound(V.rng(0.55, 0.85), 3),
    prng_seed: Number.parseInt(seed.slice(32, 40), 16),
    chattiness: beh.chattiness,
  };
}
