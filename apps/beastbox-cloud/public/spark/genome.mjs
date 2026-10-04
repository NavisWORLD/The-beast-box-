/** Seed -> genome. Discrete choices use labelled SHA-256 streams, matching beastgen/genome.py. */

import { sha256Hex } from "./sha.mjs";
import { fuse, gaussianAffinity, pyRound, quantumFeatures, Stream } from "./engine.mjs";
import { validate } from "./signal.mjs";

export const SEED_SCHEMA = "lost-cosmos-beast-seed-v2";
export const GENOME_SCHEMA = "lost-cosmos-beast-genome-v2";

export function canon(value) {
  return JSON.stringify(value);
}

function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = sortObject(value[key]);
    return out;
  }
  return value;
}

export function canonicalJson(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Invalid number");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

const ISLANDS = {
  "Eridoria Prime": { arch: [0.33, 0.33, 0.30], element: "verdant", bodies: { sprout: 3, pup: 2, fox: 2, biped: 2, bird: 1, golem: 1 }, ears: ["leaf", "pointy", "round"], tails: ["leaf", "fluffy"], wings: ["none", "none", "leaf"], patterns: ["spots", "moss", "belly", "stripes"] },
  "Hollow Verdance": { arch: [0.15, 0.60, 0.05], element: "grove", bodies: { sprout: 2, golem: 2, pup: 1, fox: 1, biped: 2, serpent: 1 }, ears: ["antlers", "leaf", "round"], tails: ["leaf", "fluffy"], wings: ["none", "none", "leaf"], patterns: ["moss", "spots", "stripes"] },
  "The Crown": { arch: [0.50, 0.45, 0.05], element: "radiant", bodies: { pup: 2, bird: 3, fox: 2, dragonling: 1, moth: 1, biped: 1 }, ears: ["pointy", "crown", "horns"], tails: ["fluffy", "plume"], wings: ["feather", "feather", "none"], patterns: ["belly", "stars", "stripes"] },
  "The Pale Expanse": { arch: [0.05, 0.90, 0.02], element: "frost", bodies: { pup: 2, axolotl: 1, fish: 2, bird: 1, fox: 2, serpent: 1 }, ears: ["round", "pointy", "crystal"], tails: ["fluffy", "crystal"], wings: ["none", "none", "crystal"], patterns: ["facets", "spots", "belly"] },
  "Rust Meridian": { arch: [0.85, 0.10, 0.05], element: "machine", bodies: { golem: 3, biped: 2, pup: 1, dragonling: 1, fish: 1 }, ears: ["antenna", "bolts", "pointy"], tails: ["cable", "gear"], wings: ["none", "none", "vanes"], patterns: ["circuits", "plates", "stripes"] },
  "Cinder Drift": { arch: [0.40, 0.03, 0.50], element: "ember", bodies: { dragonling: 3, pup: 2, fox: 2, serpent: 1, biped: 1 }, ears: ["flame", "pointy", "horns"], tails: ["flame"], wings: ["none", "bat", "flame"], patterns: ["cracks", "stripes"] },
  "Umbral Deep": { arch: [0.05, 0.15, 0.05], element: "umbral", bodies: { moth: 3, dragonling: 2, serpent: 1, fish: 1, sprout: 1 }, ears: ["feelers", "round", "horns"], tails: ["fluffy", "none"], wings: ["moth", "bat"], patterns: ["stars", "spots"] },
  "The Shattered Reef": { arch: [0.10, 0.40, 0.45], element: "crystal", bodies: { axolotl: 3, fish: 3, serpent: 2, moth: 1 }, ears: ["gills", "crystal"], tails: ["fin", "crystal"], wings: ["none", "crystal"], patterns: ["facets", "spots", "stars"] },
};

export const BODIES = ["pup", "fox", "sprout", "moth", "axolotl", "golem", "dragonling", "bird", "fish", "serpent", "biped"];
export const POSES = {
  pup: ["front"], sprout: ["front"], moth: ["front"], golem: ["front"], biped: ["front", "three_quarter"],
  axolotl: ["front"], fox: ["three_quarter", "side"], dragonling: ["three_quarter", "side"],
  bird: ["three_quarter", "front"], fish: ["side"], serpent: ["side"],
};

export const PALETTES = {
  "Eridoria Prime": { base: [92, .55, .70], alt: [70, .55, .55], belly: [55, .30, .93], accent: [110, .60, .55], glow: [46, .85, 1.0] },
  "Hollow Verdance": { base: [135, .50, .50], alt: [28, .50, .45], belly: [95, .35, .78], accent: [150, .55, .38], glow: [165, .70, .95] },
  "The Crown": { base: [48, .18, .97], alt: [44, .70, .92], belly: [50, .08, 1.0], accent: [42, .75, .90], glow: [48, .80, 1.0] },
  "The Pale Expanse": { base: [200, .22, .97], alt: [205, .40, .85], belly: [195, .06, 1.0], accent: [190, .45, .95], glow: [185, .75, 1.0] },
  "Rust Meridian": { base: [24, .62, .78], alt: [215, .12, .62], belly: [30, .25, .88], accent: [210, .10, .48], glow: [184, .80, 1.0] },
  "Cinder Drift": { base: [10, .38, .42], alt: [355, .70, .55], belly: [20, .55, .55], accent: [15, .85, .85], glow: [36, .95, 1.0] },
  "Umbral Deep": { base: [272, .42, .72], alt: [285, .35, .55], belly: [270, .18, .92], accent: [265, .45, .82], glow: [48, .85, 1.0] },
  "The Shattered Reef": { base: [176, .48, .78], alt: [188, .55, .60], belly: [170, .20, .95], accent: [345, .40, .92], glow: [182, .85, 1.0] },
};

const NAMES = {
  "Eridoria Prime": ["Sprig", "Fern", "Clover", "Gild", "Thistle", "Bud", "Meadow", "Grove"],
  "Hollow Verdance": ["Bark", "Root", "Glen", "Hollow", "Mire", "Yew", "Moss", "Bramble"],
  "The Crown": ["Aur", "Sol", "Halo", "Regal", "Lumi", "Bright", "Gloria", "Crest"],
  "The Pale Expanse": ["Frost", "Rime", "Glace", "Snow", "Hail", "Pale", "Shiver", "Floe"],
  "Rust Meridian": ["Cog", "Rivet", "Ferro", "Bolt", "Gear", "Rust", "Volt", "Piston"],
  "Cinder Drift": ["Ember", "Ash", "Cinder", "Scorch", "Pyre", "Char", "Magma", "Calder"],
  "Umbral Deep": ["Moth", "Nyx", "Umbra", "Dusk", "Lun", "Shade", "Vesper", "Noct"],
  "The Shattered Reef": ["Glimmer", "Reef", "Prism", "Coral", "Shard", "Tide", "Lagoon", "Brine"],
};
const SUFFIX = {
  1: { default: ["ling", "pup", "kin", "let", "bun", "bit"], moth: ["mite", "let", "fluff"], axolotl: ["fin", "ling", "lotl"], golem: ["bot", "nub", "ling"], sprout: ["ling", "bud", "sprout"], fox: ["kit", "ling", "pip"], dragonling: ["wyrm", "let", "scale"], bird: ["chick", "pip", "fledge"], fish: ["fry", "fin", "bub"], serpent: ["noodle", "ling", "coil"], biped: ["kin", "tot", "bit"] },
  2: { default: ["paw", "fang", "hound", "strider", "tail"], moth: ["moth", "flutter", "wisp"], axolotl: ["shard", "fin", "newt"], golem: ["guard", "frame", "fist"], sprout: ["paw", "bloom", "puff"], fox: ["fox", "tail", "vix"], dragonling: ["drake", "wing", "claw"], bird: ["wing", "plume", "crest"], fish: ["fin", "gill", "ray"], serpent: ["coil", "naga", "slither"], biped: ["walker", "scout", "kin"] },
  3: { default: ["rex", "warden", "titan", "heart", "lord"], moth: ["wing", "seraph", "veil"], axolotl: ["leviath", "serpent", "drake"], golem: ["colossus", "warden", "titan"], sprout: ["warden", "heart", "elder"], fox: ["kitsune", "warden", "regent"], dragonling: ["dragon", "wyvern", "tyrant"], bird: ["phoenix", "roc", "seraph"], fish: ["leviath", "monarch", "tide"], serpent: ["wyrm", "leviath", "naga"], biped: ["knight", "sage", "warden"] },
};
const TEMPERAMENTS = ["Serene", "Curious", "Fierce", "Dreamy", "Steadfast", "Playful", "Bold", "Gentle"];
const GAITS = ["bob", "hop", "sway", "float", "wobble", "scuttle", "pulse"];
const HABITS = ["look_around", "stretch", "turn_around", "double_hop", "doze_off", "shake", "sparkle_burst", "tail_flick", "peek", "spin_hop", "yawn", "sniff"];
const QUIRKS = ["hiccups", "wanders", "shivers", "echo_bounce", "freezes_mid_beat", "counts_beats", "moonwalk", "startles"];
const FLAVORS = { calm: ["dozes", "melts", "purrs", "hums"], focus: ["freezes", "tracks", "paces", "stares"], spark: ["bounces", "zooms", "glitters", "spins"] };
const CHANNELS = ["focus", "calm", "spark"];

const STYLES = ["chirp", "purr", "growl", "trill", "coo", "beep"];
const SIZE = { pup: 0.50, fox: 0.52, sprout: 0.45, moth: 0.34, axolotl: 0.46, golem: 0.82, dragonling: 0.64, bird: 0.30, fish: 0.40, serpent: 0.58, biped: 0.50 };
const STYLE_W = {
  pup: { purr: 3, chirp: 2, coo: 1, growl: 1 }, fox: { chirp: 3, purr: 2, trill: 1 }, sprout: { coo: 3, chirp: 2, trill: 1 },
  moth: { coo: 3, trill: 2, chirp: 2 }, axolotl: { trill: 3, coo: 2, chirp: 1 }, golem: { growl: 3, beep: 2, purr: 1 },
  dragonling: { growl: 3, chirp: 2, purr: 1 }, bird: { chirp: 4, trill: 3 }, fish: { trill: 3, coo: 2, chirp: 1 },
  serpent: { trill: 2, purr: 2, growl: 1, coo: 1 }, biped: { chirp: 2, coo: 2, purr: 1, beep: 1 },
};
const ELEMENT_W = { machine: { beep: 6 }, ember: { growl: 2, chirp: 1 }, umbral: { coo: 2, purr: 1 }, crystal: { trill: 2, chirp: 1 }, frost: { coo: 2, trill: 1 }, radiant: { chirp: 2, trill: 1 }, verdant: { chirp: 1, coo: 1 }, grove: { purr: 1, coo: 1 } };
const TEMPER_W = { Serene: { coo: 1.5, purr: 1 }, Gentle: { purr: 1.5, coo: 1 }, Fierce: { growl: 2 }, Bold: { growl: 1, chirp: 1 }, Playful: { chirp: 1.5, trill: 1 }, Curious: { chirp: 1.5, trill: 0.5 }, Dreamy: { coo: 2 }, Steadfast: { purr: 1, beep: 0.5 } };
const STYLE_P = {
  chirp: [{ sine: 2, triangle: 3 }, [6.0, 9.0], [6, 9], [20, 60], 0, [0.02, 0.10]],
  purr: [{ triangle: 2, sawtooth: 1 }, [3.0, 4.6], [4, 6], [10, 30], [22, 30], [0.10, 0.25]],
  growl: [{ sawtooth: 3, square: 1 }, [2.8, 4.2], [4, 6], [20, 50], [30, 46], [0.12, 0.30]],
  trill: [{ sine: 2, triangle: 2 }, [4.5, 7.0], [14, 22], [90, 180], 0, [0.02, 0.10]],
  coo: [{ sine: 4, triangle: 1 }, [2.6, 4.0], [4, 6], [15, 40], 0, [0.06, 0.18]],
  beep: [{ square: 3, triangle: 1 }, [5.0, 8.0], [0, 0.01], [0, 1], 0, [0.0, 0.02]],
};
const CONSONANTS = { chirp: ["p", "t", "ch", "k", "pi"], purr: ["mr", "r", "m", "pr"], growl: ["gr", "r", "g", "hr"], trill: ["tr", "l", "r", "tl"], coo: ["w", "m", "h", "n"], beep: ["b", "d", "bz", "t"] };
const VOWELS = [["a", 800, 1200], ["e", 500, 1900], ["i", 320, 2500], ["o", 500, 900], ["u", 340, 800], ["ee", 300, 2700], ["aw", 650, 1000], ["ü", 300, 1700]];

function gclamp(x) { return 0.5 + 0.5 * Math.tanh(2.5 * x); }

function pickDict(stream, weights) {
  const items = Object.entries(weights);
  const tot = items.reduce((s, [, v]) => s + v, 0);
  let x = stream.u() * tot, acc = 0;
  for (const [k, v] of items) {
    acc += v;
    if (x < acc) return k;
  }
  return items[items.length - 1][0];
}

function deriveVoice(seed, body, element, temperament, genes, qf, beh) {
  const V = new Stream(seed, "voice");
  const w = Object.fromEntries(STYLES.map((s) => [s, 0.2]));
  for (const src of [STYLE_W[body] || {}, ELEMENT_W[element] || {}, TEMPER_W[temperament] || {}]) {
    for (const [k, v] of Object.entries(src)) w[k] += v;
  }
  const style = pickDict(V, w);
  const [waves, sps, vib, cents, am, breath] = STYLE_P[style];
  const size = (SIZE[body] ?? 0.5) + 0.18 * (genes.chub - 0.5);
  let base = 980 * 2 ** (-1.7 * size) * 2 ** (0.6 * (V.u() - 0.5));
  if (style === "growl") base *= 0.72;
  const m = qf.marginals_measured;
  const m0 = m[0], m1 = m[1 % m.length];
  const f1 = 300 + 550 * m0 + 80 * (V.u() - 0.5);
  const f2 = 950 + 1500 * m1 + 200 * (V.u() - 0.5);
  let vowelSeq = (qf.counts_top.length ? qf.counts_top : [qf.top_state]).map((b) => parseInt(b, 2) % VOWELS.length).slice(0, 4);
  let vowelSrc;
  if (new Set(vowelSeq).size < 2) {
    vowelSeq = vowelSeq.concat([0, 1, 2].map((i) => parseInt(seed.slice(20 + 2 * i, 22 + 2 * i), 16) % VOWELS.length));
    vowelSrc = "top outcomes + seed-hash (run has few distinct outcomes)";
  } else vowelSrc = "top outcomes of the run";
  let rhythm = [...qf.top_state].reverse().map((b) => Number(b)).slice(0, 8);
  let rsrc = "top_state bits";
  if (rhythm.length < 5) {
    const sb = parseInt(seed.slice(24, 32), 16).toString(2).padStart(32, "0");
    rhythm = rhythm.concat([...sb.slice(0, 5 - rhythm.length)].map((c) => Number(c)));
    rsrc = "top_state bit + seed-hash padding (1-bit run)";
  }
  const cons0 = CONSONANTS[style].slice();
  const k0 = Math.floor(V.u() * cons0.length);
  const cons = cons0.slice(k0).concat(cons0.slice(0, k0));
  return {
    style,
    base_pitch_hz: pyRound(base, 1),
    formants_hz: [pyRound(f1), pyRound(f2)],
    formant_q: pyRound(V.rng(4.0, 9.0), 2),
    wave: pickDict(V, waves),
    brightness: pyRound(V.rng(0.2, 0.9), 3),
    breath: pyRound(V.rng(breath[0], breath[1]), 3),
    speed_sps: pyRound(V.rng(sps[0], sps[1]), 2),
    vibrato_hz: pyRound(V.rng(vib[0], vib[1]), 2),
    vibrato_cents: pyRound(V.rng(cents[0], cents[1]), 1),
    am_hz: am ? pyRound(V.rng(am[0], am[1]), 1) : 0,
    contour: pickDict(V, { rise: 1, fall: 1, arch: 1.3, bounce: 1 }),
    jump_semitones: pyRound(V.rng(2.0, 7.0), 2),
    rhythm, rhythm_source: rsrc,
    vowels: vowelSeq.map((i) => VOWELS[i][0]),
    vowel_formants: vowelSeq.map((i) => [VOWELS[i][1], VOWELS[i][2]]),
    vowel_source: vowelSrc,
    consonants: cons,
    phrase_syllables: [2 + Math.floor(V.u() * 2), 3 + Math.floor(V.u() * 3)],
    gain: pyRound(V.rng(0.55, 0.85), 3),
    prng_seed: parseInt(seed.slice(32, 40), 16),
    chattiness: beh.chattiness,
  };
}

function behavior(seed, genes, eng, qf, traits, body, wings, tail) {
  const B = new Stream(seed, "behavior");
  const d54 = eng.dyn54, c12 = eng.coupled12;
  const gw = {
    bob: 1.0,
    hop: 0.4 + 1.6 * genes.legs,
    sway: 0.4 + 1.2 * genes.tail_size * (tail !== "none"),
    float: 0.15 + 2.2 * genes.wing_size * (wings !== "none"),
    wobble: 0.3 + 1.6 * genes.chub,
    scuttle: 0.3 + 1.2 * (1 - genes.legs),
    pulse: 0.3 + 1.2 * genes.glow_amount,
  };
  const gait = B.pick(Object.keys(gw), Object.values(gw));
  const tempo = pyRound(0.35 + 1.25 * (0.5 * gclamp(d54[31]) + 0.5 * B.u()) + 0.4 * traits.spark / 100, 3);
  let accents = [...qf.top_state].reverse().map((b) => Number(b));
  let accentsSource = `top_state bits q0..q${accents.length - 1}`;
  if (accents.length < 5) {
    const sb = parseInt(seed.slice(8, 16), 16).toString(2).padStart(32, "0");
    accents = accents.concat([...sb.slice(0, 5 - accents.length)].map((c) => Number(c)));
    accentsSource += " + seed-hash padding";
  }
  accents = accents.slice(0, 8);
  if (!accents.some(Boolean)) accents = [1, ...accents.slice(1)];
  let pool = HABITS.map((name) => [name, 0.4 + B.u()]);
  const habits = [];
  for (let n = 0; n < 3; n++) {
    const h = B.pick(pool.map((p) => p[0]), pool.map((p) => p[1]));
    pool = pool.filter((p) => p[0] !== h);
    habits.push({ name: h, every_s: pyRound(B.rng(4.0, 13.0), 2) });
  }
  const quirks = [];
  const qpool = QUIRKS.slice();
  const nq = 1 + (B.u() < 0.55 ? 1 : 0);
  for (let n = 0; n < nq; n++) {
    const q = qpool.splice(Math.floor(B.u() * qpool.length), 1)[0];
    quirks.push({ name: q, every_s: pyRound(B.rng(3.0, 11.0), 2), strength: pyRound(B.rng(0.4, 1.0), 3) });
  }
  const raw = [0, 1, 2].map((i) => 0.3 + 0.7 * gclamp(d54[40 + 3 * i] + c12[4 * i]) + 0.9 * B.u() + 0.5 * qf.marginals[i]);
  const tot = raw.reduce((a, b) => a + b, 0);
  const sens = {};
  CHANNELS.forEach((ch, i) => { sens[ch] = pyRound(3 * raw[i] / tot, 3); });
  const dominant = CHANNELS.reduce((best, ch) => (sens[ch] > sens[best] ? ch : best));
  return {
    gait, tempo_hz: tempo, amplitude_px: 1 + Math.floor(B.u() * 3), swing: pyRound(B.rng(0, 0.35), 3),
    accents, accents_source: accentsSource, breath_hz: pyRound(B.rng(0.12, 0.45), 3), breath_px: 1 + (B.u() < 0.35 ? 1 : 0),
    appendage_mul: pyRound(B.rng(0.5, 3.0), 2), appendage_px: 1 + (B.u() < 0.4 ? 1 : 0),
    blink_mean_s: pyRound(B.rng(1.6, 6.0), 2), double_blink_p: pyRound(B.rng(0, 0.5), 2),
    habits, quirks, sensitivity: sens, reacts_most_to: dominant,
    thresholds: Object.fromEntries(CHANNELS.map((ch) => [ch, Math.floor(B.rng(25, 60))])),
    latency_s: pyRound(B.rng(0.2, 1.2), 2),
    flavors: Object.fromEntries(CHANNELS.map((ch) => [ch, B.pick(FLAVORS[ch])])),
    chattiness: pyRound(B.rng(0.25, 1.0), 2),
    tic: null,
    prng_seed: parseInt(seed.slice(0, 8), 16),
  };
}

export function bucketTraits(traits, bucket = 10) {
  const t = validate(traits);
  if (bucket <= 1) return t;
  const out = {};
  for (const [k, v] of Object.entries(t)) out[k] = Math.min(100, pyRound(v / bucket) * bucket);
  return out;
}

export function makeSeed(traits, run, userId = null, bucket = 10) {
  const t = validate(traits);
  const material = {
    schema: SEED_SCHEMA,
    traits: { schema: "cosmic-muse-traits-v1", ...t },
    stabilization: { bucket: bucket | 0 },
    quantum: { backend: run.backend, job_id: run.job_id, pub_index: run.pub_index, shots: run.shots, counts: run.counts },
    user_id: userId,
  };
  const orderedTraits = { calm: t.calm, focus: t.focus, spark: t.spark };
  const canonMaterial = {
    quantum: { backend: run.backend, counts: sortObject(run.counts), job_id: run.job_id, pub_index: run.pub_index, shots: run.shots },
    schema: SEED_SCHEMA,
    stabilization: { bucket: bucket | 0 },
    traits: { calm: orderedTraits.calm, focus: orderedTraits.focus, schema: "cosmic-muse-traits-v1", spark: orderedTraits.spark },
    user_id: userId,
  };
  void material;
  return [sha256Hex(canonicalJson(canonMaterial)), canonMaterial];
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
  for (const [k, v] of Object.entries(ISLANDS)) aff[k] = gaussianAffinity(tp, v.arch, 0.28);
  const island = S("island").pick(Object.keys(aff), Object.values(aff).map((a) => a ** 2 + 0.02));
  const I = ISLANDS[island];
  let body = S("body").pick(Object.keys(I.bodies), Object.values(I.bodies));
  let ears = S("ears").pick(I.ears);
  let tail = S("tail").pick(I.tails);
  let wings = body === "moth" ? "moth" : S("wings").pick(I.wings);
  if (body === "axolotl") {
    ears = ["gills", "crystal"].includes(ears) ? ears : "gills";
    tail = ["fin", "crystal"].includes(tail) ? tail : "fin";
  }
  if (body === "dragonling") {
    wings = ["none", "moth", "leaf", "feather"].includes(wings) ? "bat" : wings;
    ears = ["horns", "crown", "crystal", "flame", "antenna", "bolts"].includes(ears) ? ears : "horns";
    tail = ["fluffy", "plume", "leaf", "none"].includes(tail) ? "spade" : tail;
  }
  if (body === "bird") {
    wings = ["crystal", "flame", "vanes"].includes(wings) ? wings : "feather";
    tail = ["fluffy", "leaf", "none", "cable", "gear"].includes(tail) ? "plume" : tail;
  }
  if (body === "fish") {
    wings = "none";
    tail = tail === "crystal" ? "crystal" : "fishtail";
  }
  if (body === "serpent") {
    wings = ["feather", "leaf", "moth", "vanes"].includes(wings) ? "none" : wings;
    tail = ["crystal", "flame", "fin", "leaf"].includes(tail) ? tail : "tip";
  }
  const pose = S("pose").pick(POSES[body]);
  const pattern = S("pattern").pick(I.patterns);
  const top = qf.top_state;
  const topInt = parseInt(top, 2);
  let patternVariant, pvSource;
  if (top.length >= 5) {
    patternVariant = topInt & 31;
    pvSource = "top_state (low 5 bits)";
  } else {
    patternVariant = (topInt + 2 * parseInt(seed.slice(16, 18), 16)) & 31;
    pvSource = "top_state bit + seed-hash bits";
  }
  const genes = {};
  const names = ["chub", "head", "legs", "ear_size", "tail_size", "wing_size", "eye_size", "eye_gap", "hue", "sat", "val", "pattern_density", "pattern_scale", "glow_amount"];
  const gs = S("genes");
  names.forEach((n, i) => { genes[n] = pyRound(0.55 * gclamp(d54[(i * 5) % 54]) + 0.45 * gs.u(), 4); });
  const [f, c, s] = tp;
  let glowHue = (s >= f && !["The Pale Expanse", "The Shattered Reef"].includes(island)) ? "gold" : "cyan";
  if (["Cinder Drift", "The Crown", "Eridoria Prime"].includes(island)) glowHue = "native";
  const eyeStyle = S("eye").pick(["round", "sparkle", "sleepy", "round"], [3, 1 + 3 * s, 3 * c, 1]);
  const mouth = S("mouth").pick(["smile", "w", "fang", "open"], [3, 2, 1 + 3 * f, 1 + 2 * s]);
  const ts = S("temper");
  const scores = {
    Serene: c * 1.2, Curious: (s + f) * 0.6, Fierce: (f + s) * 0.7 - c, Dreamy: 1 - (f + c + s),
    Steadfast: (f + c) * 0.6, Playful: (s + c) * 0.6, Bold: f, Gentle: c * 0.7 + 0.1,
  };
  let temperament = TEMPERAMENTS[0];
  let bestScore = -Infinity;
  for (const k of TEMPERAMENTS) {
    const score = scores[k] + 0.25 * ts.u();
    if (score > bestScore) { bestScore = score; temperament = k; }
  }
  return finishGenome({ t, seed, run, userId, qf, eng, d54, island, I, body, ears, tail, wings, pose, pattern, top, topInt, patternVariant, pvSource, genes, glowHue, eyeStyle, mouth, temperament, aff, f, c, s });
}

function finishGenome(ctx) {
  const { t, seed, run, userId, qf, eng, d54, island, I, body, ears, tail, wings, pose, pattern, top, topInt, patternVariant, pvSource, genes, glowHue, eyeStyle, mouth, temperament, aff } = ctx;
  const m = qf.marginals;
  const w = [
    1 + t.calm / 100 + 0.6 * gclamp(d54[3]) + m[0],
    1 + t.focus / 100 + 0.6 * gclamp(d54[7]) + m[1],
    1 + (t.calm / 100) * 0.8 + 0.6 * gclamp(d54[11]) + m[2],
    1 + ((t.focus + t.spark) / 100) * 0.6 + 0.6 * gclamp(d54[17]) + m[3],
    1 + (t.spark / 100) * 1.2 + 0.6 * gclamp(d54[23]) + m[4],
  ];
  const sumW = w.reduce((a, b) => a + b, 0);
  const stats = {};
  for (const [stage, total] of [[1, 180], [2, 300], [3, 440]]) {
    const v = w.map((wi) => pyRound(total * wi / sumW));
    stats[stage] = { hp: v[0], atk: v[1], def: v[2], spd: v[3], spark: v[4] };
  }
  const ns = new Stream(seed, "names");
  const pool = NAMES[island].slice();
  const stageNames = {};
  for (const stage of [1, 2, 3]) {
    const pre = pool.splice(Math.floor(ns.u() * pool.length), 1)[0];
    const sufPool = SUFFIX[stage][body] || SUFFIX[stage].default;
    const suf = sufPool[Math.floor(ns.u() * sufPool.length)];
    let nm = (pre + suf).replace("lll", "ll");
    stageNames[stage] = nm[0].toUpperCase() + nm.slice(1);
  }
  const beh = behavior(seed, genes, eng, qf, t, body, wings, tail);
  const voice = deriveVoice(seed, body, I.element, temperament, genes, qf, beh);
  const nm1 = stageNames[1];
  const ticStem = (nm1.slice(0, 2) + nm1.slice(2, 5).toLowerCase().replace(/[aeiou]/g, "").slice(0, 1) || nm1.slice(0, 3)).toLowerCase();
  beh.tic = ticStem + new Stream(seed, "tic").pick(["!", "~", "?", "..."]);
  return {
    schema: GENOME_SCHEMA,
    seed,
    inputs: { traits: t, quantum_run: run.key, user_id: userId },
    quantum: {
      backend: run.backend, job_id: run.job_id, pub_index: run.pub_index, counts_sha256: run.counts_sha256,
      top_state: top, top_state_int: topInt, num_bits: qf.num_bits, entropy_norm: pyRound(qf.entropy_norm, 4),
      marginals: qf.marginals_measured.map((x) => pyRound(x, 4)),
    },
    engine: {
      dyn12: eng.dyn12.map((x) => pyRound(x, 5)),
      island_affinity: Object.fromEntries(Object.entries(aff).map(([k, v]) => [k, pyRound(v, 4)])),
    },
    island, element: I.element, body, ears, tail, wings, pattern, pattern_variant: patternVariant,
    pattern_variant_source: pvSource, pose, eye_style: eyeStyle, mouth, glow: glowHue,
    facing: new Stream(seed, "facing").pick(["right", "left"]),
    temperament, behavior: beh, voice, genes, stats, names: stageNames,
  };
}
