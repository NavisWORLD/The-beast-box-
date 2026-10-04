/** QBEAST1 writer. Same bytes as spark-beasts/qbeast_file.py and Living Universe qbeast.mjs. */

import { pyRound } from "./engine.mjs";
import { canonicalJson } from "./genome.mjs";
import { sha256Hex } from "./sha.mjs";

const FAMILIES = ["nebula", "aurora", "void", "plasma", "memory", "signal", "starlight"];
const FAMILY_LOOK = { nebula: "nebula", aurora: "aurora", void: "nebula", plasma: "starlight", memory: "starlight", signal: "aurora", starlight: "starlight" };
const HUES = { nebula: 0, aurora: 0, void: 83, plasma: -92, memory: 29, signal: 45, starlight: 0 };
const STAT_NAMES = ["hp", "energy", "signal", "memory", "resonance", "agility", "chaos", "stability", "curiosity", "evolution"];
const TRAIT_NAMES = ["curiosity", "energy", "playfulness", "caution", "independence"];
const STEMS = ["Neb", "Lum", "Ori", "Vexa", "Astr", "Phera", "Glima", "Zori", "Mira", "Cosmi"];
const ENDS = ["by", "io", "ix", "a", "on", "ora", "u", "ra", "yx", "iri"];
const PRIVATE = /(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})/i;
const CARD_RE = /^Spark Beasts v1\. Recorded quantum seed, game companion\. traits=(\d+),(\d+),(\d+) bucket=(\d+) run=([A-Za-z0-9:_#-]+) name=([A-Za-z0-9]+)(?: keeper=([A-Za-z0-9 ._-]{1,24}))?$/;

function fnv1a(text) {
  let h = 2166136261;
  for (const byte of new TextEncoder().encode(text)) {
    h ^= byte;
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

function generator(seed, domain) {
  let state = fnv1a(`1|${domain}|${seed}`) || 0x6d2b79f5;
  return () => {
    state = (state ^ (state << 13)) >>> 0;
    state = (state ^ (state >>> 17)) >>> 0;
    state = (state ^ (state << 5)) >>> 0;
    return (state >>> 0) / 4294967296;
  };
}

export function stableCreatureId(seed) {
  return `bb-${fnv1a(`identity|1|${seed}`).toString(16).padStart(8, "0")}`;
}

export function generateCreature(seed, chosenFamily = null) {
  if (typeof seed !== "string" || seed.length < 1 || seed.length > 64) throw new Error("Seed must have 1 to 64 characters");
  const art = generator(seed, "appearance");
  const statsRandom = generator(seed, "stats");
  const traitsRandom = generator(seed, "temperament");
  const family = chosenFamily || FAMILIES[Math.floor(art() * FAMILIES.length)];
  const hueShift = Math.max(-180, Math.min(180, HUES[family] + Math.floor(art() * 21) - 10));
  const stats = Object.fromEntries(STAT_NAMES.map((key) => [key, 50]));
  for (let n = 0; n < 270; n++) {
    const source = Math.floor(statsRandom() * STAT_NAMES.length);
    const target = Math.floor(statsRandom() * STAT_NAMES.length);
    if (source !== target && stats[STAT_NAMES[source]] > 20 && stats[STAT_NAMES[target]] < 80) {
      stats[STAT_NAMES[source]] -= 1;
      stats[STAT_NAMES[target]] += 1;
    }
  }
  const temperament = Object.fromEntries(TRAIT_NAMES.map((key) => [key, Math.floor(20 + traitsRandom() * 61)]));
  const naming = generator(seed, "name");
  const name = STEMS[Math.floor(naming() * STEMS.length)] + ENDS[Math.floor(naming() * ENDS.length)];
  if (Math.abs(hueShift) > 127) throw new Error("hue out of the portable range");
  return {
    schema: "beast-cage-creature-v1",
    version: 1,
    id: stableCreatureId(seed),
    seed,
    name,
    family,
    baseLook: FAMILY_LOOK[family],
    appearance: {
      hueShift,
      glow: pyRound(40 + art() * 60),
      finPattern: Math.floor(art() * 4),
      haloPattern: Math.floor(art() * 3),
      constellation: Math.floor(art() * 65536),
    },
    temperament,
    game: { stats, level: 1, experience: 0 },
    provenance: "classical-seeded-game-generation",
  };
}

export function sparkSummary(genome) {
  const traits = genome.inputs.traits;
  const keeper = genome.inputs.user_id || "";
  let text = `Spark Beasts v1. Recorded quantum seed, game companion. traits=${traits.focus},${traits.calm},${traits.spark} bucket=10 run=${genome.inputs.quantum_run} name=${genome.names[2]}`;
  if (keeper) {
    if (!/^[A-Za-z0-9 ._-]{1,24}$/.test(keeper) || PRIVATE.test(keeper)) throw new Error("keeper name must be a short public label");
    text += ` keeper=${keeper}`;
  }
  if (text.length > 256 || PRIVATE.test(text)) throw new Error("spark card is not public text");
  return text;
}

export function parseSparkCard(summary) {
  const match = CARD_RE.exec(summary);
  if (!match) throw new Error("spark card was not recognized");
  const bucket = Number(match[4]);
  if (bucket !== 10) throw new Error("unsupported bucket");
  return {
    traits: { focus: Number(match[1]), calm: Number(match[2]), spark: Number(match[3]) },
    bucket,
    run: match[5],
    name: match[6],
    user_id: match[7] || null,
  };
}

function hashObject(value) {
  return sha256Hex(`QBEAST1\0${canonicalJson(value)}`);
}

export function buildQbeast(genome) {
  const seed = genome.seed;
  const family = FAMILIES[fnv1a(`spark-family|${seed}`) % FAMILIES.length];
  const profile = generateCreature(seed, family);
  const publicState = { schema: "dyn12-public-v1", mode: "unavailable", values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], source_sha256: null };
  const progress = { trust: 0, bond: 0, evolution_stage: 0 };
  const summary = sparkSummary(genome);
  const head = hashObject({ domain: "genesis", profile, public_state: publicState, progress });
  const event = {
    generation: 1,
    parent: head,
    proposal_id: sha256Hex(`spark-proposal:${seed}`),
    kind: "memory",
    payload: { summary, source_ref: "public:spark-beasts" },
  };
  event.hash = hashObject({ domain: "event", generation: event.generation, parent: event.parent, proposal_id: event.proposal_id, kind: event.kind, payload: event.payload });
  const snapshot = {
    format: "QBEAST1",
    version: 1,
    profile,
    public_state: publicState,
    progress,
    events: [event],
    generation: 1,
    lineage_head: event.hash,
    digest: "0".repeat(64),
  };
  const { digest, ...body } = snapshot;
  void digest;
  snapshot.digest = hashObject(body);
  return snapshot;
}

export function serializeQbeast(snapshot) {
  return `${canonicalJson(snapshot)}\n`;
}

export function loadQbeast(text) {
  if (new TextEncoder().encode(text).length > 524288) throw new Error("Beast file is too large");
  const snapshot = JSON.parse(text);
  if (snapshot.format !== "QBEAST1" || snapshot.version !== 1) throw new Error("Unsupported QBEAST format");
  const { digest, ...body } = snapshot;
  if (hashObject(body) !== digest) throw new Error("QBEAST digest mismatch");
  if (snapshot.generation !== snapshot.events.length) throw new Error("Lineage was rejected");
  if (snapshot.public_state.mode !== "unavailable") throw new Error("Measured projection is not accepted from Spark Beasts");
  if (snapshot.progress.trust || snapshot.progress.bond || snapshot.progress.evolution_stage) throw new Error("Host progress is not accepted without a pinned signing key");
  const card = parseSparkCard(snapshot.events[0].payload.summary);
  const expected = generateCreature(snapshot.profile.seed, snapshot.profile.family);
  if (canonicalJson(snapshot.profile) !== canonicalJson(expected)) throw new Error("Game profile does not match the seed");
  return { snapshot, card };
}
