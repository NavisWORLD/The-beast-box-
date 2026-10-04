/**
 * Deterministic spark genome.
 * seed = SHA-256(canonical JSON of schema, stabilized cosmic-muse-traits-v1,
 * the recorded run's identity and full counts, and an optional player name).
 */
import { canon, pyRound, sha256Bytes, sha256Hex, u64Unit } from './hash.mjs';
import { bucketTraits } from './signal.mjs';
import { fuse, gaussianAffinity, quantumFeatures } from './engine.mjs';
import { deriveVoice } from './voice.mjs';

export const SEED_SCHEMA = 'lost-cosmos-beast-seed-v2';
export const GENOME_SCHEMA = 'lost-cosmos-beast-genome-v2';

export class Stream {
  constructor(seedHex, label) {
    this.seed = seedHex;
    this.label = label;
    this.n = 0;
  }

  u() {
    const digest = sha256Bytes(`${this.seed}:${this.label}:${this.n}`);
    this.n += 1;
    return u64Unit(digest);
  }

  pick(items, weights = null) {
    const list = [...items];
    const w = weights ? [...weights] : list.map(() => 1);
    let sum = 0;
    for (const weight of w) sum += weight;
    let x = this.u() * sum;
    let acc = 0;
    for (let i = 0; i < list.length; i++) {
      acc += w[i];
      if (x < acc) return list[i];
    }
    return list[list.length - 1];
  }

  rng(lo, hi) {
    return lo + (hi - lo) * this.u();
  }
}

export const ISLANDS = {
  'Eridoria Prime': { arch: [0.33, 0.33, 0.30], element: 'verdant', bodies: { sprout: 3, pup: 2, fox: 2, biped: 2, bird: 1, golem: 1 }, ears: ['leaf', 'pointy', 'round'], tails: ['leaf', 'fluffy'], wings: ['none', 'none', 'leaf'], patterns: ['spots', 'moss', 'belly', 'stripes'] },
  'Hollow Verdance': { arch: [0.15, 0.60, 0.05], element: 'grove', bodies: { sprout: 2, golem: 2, pup: 1, fox: 1, biped: 2, serpent: 1 }, ears: ['antlers', 'leaf', 'round'], tails: ['leaf', 'fluffy'], wings: ['none', 'none', 'leaf'], patterns: ['moss', 'spots', 'stripes'] },
  'The Crown': { arch: [0.50, 0.45, 0.05], element: 'radiant', bodies: { pup: 2, bird: 3, fox: 2, dragonling: 1, moth: 1, biped: 1 }, ears: ['pointy', 'crown', 'horns'], tails: ['fluffy', 'plume'], wings: ['feather', 'feather', 'none'], patterns: ['belly', 'stars', 'stripes'] },
  'The Pale Expanse': { arch: [0.05, 0.90, 0.02], element: 'frost', bodies: { pup: 2, axolotl: 1, fish: 2, bird: 1, fox: 2, serpent: 1 }, ears: ['round', 'pointy', 'crystal'], tails: ['fluffy', 'crystal'], wings: ['none', 'none', 'crystal'], patterns: ['facets', 'spots', 'belly'] },
  'Rust Meridian': { arch: [0.85, 0.10, 0.05], element: 'machine', bodies: { golem: 3, biped: 2, pup: 1, dragonling: 1, fish: 1 }, ears: ['antenna', 'bolts', 'pointy'], tails: ['cable', 'gear'], wings: ['none', 'none', 'vanes'], patterns: ['circuits', 'plates', 'stripes'] },
  'Cinder Drift': { arch: [0.40, 0.03, 0.50], element: 'ember', bodies: { dragonling: 3, pup: 2, fox: 2, serpent: 1, biped: 1 }, ears: ['flame', 'pointy', 'horns'], tails: ['flame'], wings: ['none', 'bat', 'flame'], patterns: ['cracks', 'stripes'] },
  'Umbral Deep': { arch: [0.05, 0.15, 0.05], element: 'umbral', bodies: { moth: 3, dragonling: 2, serpent: 1, fish: 1, sprout: 1 }, ears: ['feelers', 'round', 'horns'], tails: ['fluffy', 'none'], wings: ['moth', 'bat'], patterns: ['stars', 'spots'] },
  'The Shattered Reef': { arch: [0.10, 0.40, 0.45], element: 'crystal', bodies: { axolotl: 3, fish: 3, serpent: 2, moth: 1 }, ears: ['gills', 'crystal'], tails: ['fin', 'crystal'], wings: ['none', 'crystal'], patterns: ['facets', 'spots', 'stars'] },
};

export const BODIES = ['pup', 'fox', 'sprout', 'moth', 'axolotl', 'golem', 'dragonling', 'bird', 'fish', 'serpent', 'biped'];
export const POSES = {
  pup: ['front'], sprout: ['front'], moth: ['front'], golem: ['front'], biped: ['front', 'three_quarter'],
  axolotl: ['front'], fox: ['three_quarter', 'side'], dragonling: ['three_quarter', 'side'],
  bird: ['three_quarter', 'front'], fish: ['side'], serpent: ['side'],
};

export const PALETTES = {
  'Eridoria Prime': { base: [92, .55, .70], alt: [70, .55, .55], belly: [55, .30, .93], accent: [110, .60, .55], glow: [46, .85, 1.0] },
  'Hollow Verdance': { base: [135, .50, .50], alt: [28, .50, .45], belly: [95, .35, .78], accent: [150, .55, .38], glow: [165, .70, .95] },
  'The Crown': { base: [48, .18, .97], alt: [44, .70, .92], belly: [50, .08, 1.0], accent: [42, .75, .90], glow: [48, .80, 1.0] },
  'The Pale Expanse': { base: [200, .22, .97], alt: [205, .40, .85], belly: [195, .06, 1.0], accent: [190, .45, .95], glow: [185, .75, 1.0] },
  'Rust Meridian': { base: [24, .62, .78], alt: [215, .12, .62], belly: [30, .25, .88], accent: [210, .10, .48], glow: [184, .80, 1.0] },
  'Cinder Drift': { base: [10, .38, .42], alt: [355, .70, .55], belly: [20, .55, .55], accent: [15, .85, .85], glow: [36, .95, 1.0] },
  'Umbral Deep': { base: [272, .42, .72], alt: [285, .35, .55], belly: [270, .18, .92], accent: [265, .45, .82], glow: [48, .85, 1.0] },
  'The Shattered Reef': { base: [176, .48, .78], alt: [188, .55, .60], belly: [170, .20, .95], accent: [345, .40, .92], glow: [182, .85, 1.0] },
};

const NAMES = {
  'Eridoria Prime': ['Sprig', 'Fern', 'Clover', 'Gild', 'Thistle', 'Bud', 'Meadow', 'Grove'],
  'Hollow Verdance': ['Bark', 'Root', 'Glen', 'Hollow', 'Mire', 'Yew', 'Moss', 'Bramble'],
  'The Crown': ['Aur', 'Sol', 'Halo', 'Regal', 'Lumi', 'Bright', 'Gloria', 'Crest'],
  'The Pale Expanse': ['Frost', 'Rime', 'Glace', 'Snow', 'Hail', 'Pale', 'Shiver', 'Floe'],
  'Rust Meridian': ['Cog', 'Rivet', 'Ferro', 'Bolt', 'Gear', 'Rust', 'Volt', 'Piston'],
  'Cinder Drift': ['Ember', 'Ash', 'Cinder', 'Scorch', 'Pyre', 'Char', 'Magma', 'Calder'],
  'Umbral Deep': ['Moth', 'Nyx', 'Umbra', 'Dusk', 'Lun', 'Shade', 'Vesper', 'Noct'],
  'The Shattered Reef': ['Glimmer', 'Reef', 'Prism', 'Coral', 'Shard', 'Tide', 'Lagoon', 'Brine'],
};
const SUFFIX = {
  1: { default: ['ling', 'pup', 'kin', 'let', 'bun', 'bit'], moth: ['mite', 'let', 'fluff'], axolotl: ['fin', 'ling', 'lotl'], golem: ['bot', 'nub', 'ling'], sprout: ['ling', 'bud', 'sprout'], fox: ['kit', 'ling', 'pip'], dragonling: ['wyrm', 'let', 'scale'], bird: ['chick', 'pip', 'fledge'], fish: ['fry', 'fin', 'bub'], serpent: ['noodle', 'ling', 'coil'], biped: ['kin', 'tot', 'bit'] },
  2: { default: ['paw', 'fang', 'hound', 'strider', 'tail'], moth: ['moth', 'flutter', 'wisp'], axolotl: ['shard', 'fin', 'newt'], golem: ['guard', 'frame', 'fist'], sprout: ['paw', 'bloom', 'puff'], fox: ['fox', 'tail', 'vix'], dragonling: ['drake', 'wing', 'claw'], bird: ['wing', 'plume', 'crest'], fish: ['fin', 'gill', 'ray'], serpent: ['coil', 'naga', 'slither'], biped: ['walker', 'scout', 'kin'] },
  3: { default: ['rex', 'warden', 'titan', 'heart', 'lord'], moth: ['wing', 'seraph', 'veil'], axolotl: ['leviath', 'serpent', 'drake'], golem: ['colossus', 'warden', 'titan'], sprout: ['warden', 'heart', 'elder'], fox: ['kitsune', 'warden', 'regent'], dragonling: ['dragon', 'wyvern', 'tyrant'], bird: ['phoenix', 'roc', 'seraph'], fish: ['leviath', 'monarch', 'tide'], serpent: ['wyrm', 'leviath', 'naga'], biped: ['knight', 'sage', 'warden'] },
};
const TEMPERAMENTS = ['Serene', 'Curious', 'Fierce', 'Dreamy', 'Steadfast', 'Playful', 'Bold', 'Gentle'];
const GAITS = ['bob', 'hop', 'sway', 'float', 'wobble', 'scuttle', 'pulse'];
const HABITS = ['look_around', 'stretch', 'turn_around', 'double_hop', 'doze_off', 'shake', 'sparkle_burst', 'tail_flick', 'peek', 'spin_hop', 'yawn', 'sniff'];
const QUIRKS = ['hiccups', 'wanders', 'shivers', 'echo_bounce', 'freezes_mid_beat', 'counts_beats', 'moonwalk', 'startles'];
const FLAVORS = { calm: ['dozes', 'melts', 'purrs', 'hums'], focus: ['freezes', 'tracks', 'paces', 'stares'], spark: ['bounces', 'zooms', 'glitters', 'spins'] };
const CHANNELS = ['focus', 'calm', 'spark'];

function squash(x) {
  return 0.5 + 0.5 * Math.tanh(2.5 * x);
}

export function makeSeed(traits, run, userId = null, bucket = 10) {
  const material = {
    schema: SEED_SCHEMA,
    traits: { schema: 'cosmic-muse-traits-v1', focus: traits.focus, calm: traits.calm, spark: traits.spark },
    stabilization: { bucket: bucket | 0 },
    quantum: {
      backend: run.backend,
      job_id: run.job_id,
      pub_index: run.pub_index,
      shots: run.shots,
      counts: run.counts,
    },
    user_id: userId ?? null,
  };
  return [sha256Hex(canon(material)), material];
}

function behavior(seed, genes, eng, qf, traits, wings, tail) {
  const B = new Stream(seed, 'behavior');
  const d54 = eng.dyn54;
  const c12 = eng.coupled12;
  const gw = {
    bob: 1.0,
    hop: 0.4 + 1.6 * genes.legs,
    sway: 0.4 + 1.2 * genes.tail_size * (tail !== 'none' ? 1 : 0),
    float: 0.15 + 2.2 * genes.wing_size * (wings !== 'none' ? 1 : 0),
    wobble: 0.3 + 1.6 * genes.chub,
    scuttle: 0.3 + 1.2 * (1 - genes.legs),
    pulse: 0.3 + 1.2 * genes.glow_amount,
  };
  const gait = B.pick(Object.keys(gw), Object.values(gw));
  const tempo = pyRound(0.35 + 1.25 * (0.5 * squash(d54[31]) + 0.5 * B.u()) + 0.4 * traits.spark / 100, 3);
  let accents = qf.topState.split('').reverse().map((ch) => Number(ch));
  let accentsSource = `top_state bits q0..q${accents.length - 1}`;
  if (accents.length < 5) {
    const sb = BigInt(`0x${seed.slice(8, 16)}`).toString(2).padStart(32, '0');
    accents = accents.concat([...sb.slice(0, 5 - accents.length)].map((ch) => Number(ch)));
    accentsSource += ' + seed-hash padding';
  }
  accents = accents.slice(0, 8);
  if (!accents.some(Boolean)) accents = [1, ...accents.slice(1)];
  const habitW = HABITS.map(() => 0.4 + B.u());
  let pool = HABITS.map((name, i) => [name, habitW[i]]);
  const habits = [];
  for (let n = 0; n < 3; n++) {
    const name = B.pick(pool.map((row) => row[0]), pool.map((row) => row[1]));
    pool = pool.filter((row) => row[0] !== name);
    habits.push({ name, every_s: pyRound(B.rng(4.0, 13.0), 2) });
  }
  const quirkCount = 1 + (B.u() < 0.55 ? 1 : 0);
  const qpool = QUIRKS.slice();
  const quirks = [];
  for (let n = 0; n < quirkCount; n++) {
    const index = Math.trunc(B.u() * qpool.length);
    const name = qpool.splice(index, 1)[0];
    quirks.push({ name, every_s: pyRound(B.rng(3.0, 11.0), 2), strength: pyRound(B.rng(0.4, 1.0), 3) });
  }
  const raw = [0, 1, 2].map((i) => 0.3 + 0.7 * squash(d54[40 + 3 * i] + c12[4 * i]) + 0.9 * B.u() + 0.5 * qf.marginals[i]);
  const tot = raw.reduce((a, b) => a + b, 0);
  const sens = {};
  CHANNELS.forEach((ch, i) => { sens[ch] = pyRound(3 * raw[i] / tot, 3); });
  let dominant = CHANNELS[0];
  for (const ch of CHANNELS) if (sens[ch] > sens[dominant]) dominant = ch;
  const thresholds = {};
  const flavors = {};
  const amplitude = 1 + Math.trunc(B.u() * 3);
  const swing = pyRound(B.rng(0, 0.35), 3);
  const breathHz = pyRound(B.rng(0.12, 0.45), 3);
  const breathPx = 1 + (B.u() < 0.35 ? 1 : 0);
  const appendageMul = pyRound(B.rng(0.5, 3.0), 2);
  const appendagePx = 1 + (B.u() < 0.4 ? 1 : 0);
  const blinkMean = pyRound(B.rng(1.6, 6.0), 2);
  const doubleBlink = pyRound(B.rng(0, 0.5), 2);
  for (const ch of CHANNELS) thresholds[ch] = Math.trunc(B.rng(25, 60));
  const latency = pyRound(B.rng(0.2, 1.2), 2);
  for (const ch of CHANNELS) flavors[ch] = B.pick(FLAVORS[ch]);
  const chattiness = pyRound(B.rng(0.25, 1.0), 2);
  return {
    gait, tempo_hz: tempo, amplitude_px: amplitude, swing,
    accents, accents_source: accentsSource, breath_hz: breathHz, breath_px: breathPx,
    appendage_mul: appendageMul, appendage_px: appendagePx,
    blink_mean_s: blinkMean, double_blink_p: doubleBlink,
    habits, quirks, sensitivity: sens, reacts_most_to: dominant, thresholds,
    latency_s: latency, flavors, chattiness, tic: null,
    prng_seed: Number.parseInt(seed.slice(0, 8), 16),
  };
}

export function buildGenome(traits, run, userId = null, bucket = 10) {
  const t = bucketTraits(traits, bucket);
  const [seed] = makeSeed(t, run, userId, bucket);
  const qf = quantumFeatures(run.counts);
  const eng = fuse(t, qf);
  const d54 = eng.dyn54;
  const S = (label) => new Stream(seed, label);
  const tp = [t.focus / 100, t.calm / 100, t.spark / 100];
  const aff = {};
  for (const [name, island] of Object.entries(ISLANDS)) aff[name] = gaussianAffinity(tp, island.arch, 0.28);
  const island = S('island').pick(Object.keys(aff), Object.values(aff).map((a) => a ** 2 + 0.02));
  const I = ISLANDS[island];
  let body = S('body').pick(Object.keys(I.bodies), Object.values(I.bodies));
  let ears = S('ears').pick(I.ears);
  let tail = S('tail').pick(I.tails);
  let wings = body === 'moth' ? 'moth' : S('wings').pick(I.wings);
  if (body === 'axolotl') {
    ears = (ears === 'gills' || ears === 'crystal') ? ears : 'gills';
    tail = (tail === 'fin' || tail === 'crystal') ? tail : 'fin';
  }
  if (body === 'dragonling') {
    wings = (wings === 'none' || wings === 'moth' || wings === 'leaf' || wings === 'feather') ? 'bat' : wings;
    ears = ['horns', 'crown', 'crystal', 'flame', 'antenna', 'bolts'].includes(ears) ? ears : 'horns';
    tail = ['fluffy', 'plume', 'leaf', 'none'].includes(tail) ? 'spade' : tail;
  }
  if (body === 'bird') {
    wings = ['crystal', 'flame', 'vanes'].includes(wings) ? wings : 'feather';
    tail = ['fluffy', 'leaf', 'none', 'cable', 'gear'].includes(tail) ? 'plume' : tail;
  }
  if (body === 'fish') {
    wings = 'none';
    tail = tail === 'crystal' ? 'crystal' : 'fishtail';
  }
  if (body === 'serpent') {
    wings = ['feather', 'leaf', 'moth', 'vanes'].includes(wings) ? 'none' : wings;
    tail = ['crystal', 'flame', 'fin', 'leaf'].includes(tail) ? tail : 'tip';
  }
  const pose = S('pose').pick(POSES[body]);
  const pattern = S('pattern').pick(I.patterns);
  const top = qf.topState;
  const topInt = Number.parseInt(top, 2);
  let patternVariant;
  let pvSource;
  if (top.length >= 5) {
    patternVariant = topInt & 31;
    pvSource = 'top_state (low 5 bits)';
  } else {
    patternVariant = (topInt + 2 * Number.parseInt(seed.slice(16, 18), 16)) & 31;
    pvSource = 'top_state bit + seed-hash bits';
  }
  const geneNames = ['chub', 'head', 'legs', 'ear_size', 'tail_size', 'wing_size', 'eye_size', 'eye_gap', 'hue', 'sat', 'val', 'pattern_density', 'pattern_scale', 'glow_amount'];
  const gs = S('genes');
  const genes = {};
  geneNames.forEach((name, i) => {
    genes[name] = pyRound(0.55 * squash(d54[(i * 5) % 54]) + 0.45 * gs.u(), 4);
  });
  const [f, c, s] = tp;
  let glow = (s >= f && island !== 'The Pale Expanse' && island !== 'The Shattered Reef') ? 'gold' : 'cyan';
  if (island === 'Cinder Drift' || island === 'The Crown' || island === 'Eridoria Prime') glow = 'native';
  const eyeStyle = S('eye').pick(['round', 'sparkle', 'sleepy', 'round'], [3, 1 + 3 * s, 3 * c, 1]);
  const mouth = S('mouth').pick(['smile', 'w', 'fang', 'open'], [3, 2, 1 + 3 * f, 1 + 2 * s]);
  const ts = S('temper');
  const scores = {
    Serene: c * 1.2, Curious: (s + f) * 0.6, Fierce: (f + s) * 0.7 - c, Dreamy: 1 - (f + c + s),
    Steadfast: (f + c) * 0.6, Playful: (s + c) * 0.6, Bold: f, Gentle: c * 0.7 + 0.1,
  };
  let temperament = TEMPERAMENTS[0];
  let best = -Infinity;
  for (const name of TEMPERAMENTS) {
    const score = scores[name] + 0.25 * ts.u();
    if (score > best) { best = score; temperament = name; }
  }
  const m = qf.marginals;
  const w = [
    1 + c + 0.6 * squash(d54[3]) + m[0],
    1 + f + 0.6 * squash(d54[7]) + m[1],
    1 + c * 0.8 + 0.6 * squash(d54[11]) + m[2],
    1 + (f + s) * 0.6 + 0.6 * squash(d54[17]) + m[3],
    1 + s * 1.2 + 0.6 * squash(d54[23]) + m[4],
  ];
  const wsum = w.reduce((a, b) => a + b, 0);
  const stats = {};
  for (const [stage, total] of [[1, 180], [2, 300], [3, 440]]) {
    const values = w.map((wi) => pyRound(total * wi / wsum));
    stats[String(stage)] = { hp: values[0], atk: values[1], def: values[2], spd: values[3], spark: values[4] };
  }
  const ns = S('names');
  const pool = NAMES[island].slice();
  const stageNames = {};
  for (const stage of [1, 2, 3]) {
    const pre = pool.splice(Math.trunc(ns.u() * pool.length), 1)[0];
    const sufPool = SUFFIX[stage][body] || SUFFIX[stage].default;
    const suf = sufPool[Math.trunc(ns.u() * sufPool.length)];
    let nm = `${pre}${suf}`.replaceAll('lll', 'll');
    nm = nm[0].toUpperCase() + nm.slice(1);
    stageNames[String(stage)] = nm;
  }
  const beh = behavior(seed, genes, eng, qf, t, wings, tail);
  const voice = deriveVoice(seed, body, I.element, temperament, genes, qf, beh);
  const nm1 = stageNames['1'];
  const mid = nm1.slice(2, 5).toLowerCase().replace(/^[aeiou]+|[aeiou]+$/g, '').slice(0, 1);
  const ticBase = (nm1.slice(0, 2) + mid) || nm1.slice(0, 3);
  beh.tic = `${ticBase.toLowerCase()}${S('tic').pick(['!', '~', '?', '...'])}`;
  return {
    schema: GENOME_SCHEMA,
    seed,
    inputs: { traits: t, quantum_run: run.key, user_id: userId ?? null },
    quantum: {
      backend: run.backend,
      job_id: run.job_id,
      pub_index: run.pub_index,
      counts_sha256: run.counts_sha256,
      top_state: top,
      top_state_int: topInt,
      num_bits: qf.numBits,
      entropy_norm: pyRound(qf.entropyNorm, 4),
      marginals: qf.marginalsMeasured.map((x) => pyRound(x, 4)),
    },
    engine: {
      dyn12: eng.dyn12.map((x) => pyRound(x, 5)),
      island_affinity: Object.fromEntries(Object.entries(aff).map(([k, v]) => [k, pyRound(v, 4)])),
    },
    island,
    element: I.element,
    body,
    ears,
    tail,
    wings,
    pattern,
    pattern_variant: patternVariant,
    pattern_variant_source: pvSource,
    pose,
    eye_style: eyeStyle,
    mouth,
    glow,
    facing: S('facing').pick(['right', 'left']),
    temperament,
    behavior: beh,
    voice,
    genes,
    stats,
    names: stageNames,
  };
}

export { GAITS, HABITS, QUIRKS };
