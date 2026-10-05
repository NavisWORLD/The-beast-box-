// Seeded attack moves for the Beast Cage habitat creature.
//
// Everything here is classical and deterministic. The input is the Spark
// genome that is built from a recorded IBM quantum count table (a fixed seed
// archived on disk), not a live quantum link. The same genome always yields the
// same move set, the same attack order, the same roam path and the same roar.
// Nothing here uses unseeded randomness, so tests can replay a beast exactly.

const ELEMENT_MOVES = {
  verdant: [
    ["Bramble Lash", "slash"], ["Spore Burst", "burst"], ["Sunleaf Beam", "beam"], ["Root Quake", "quake"],
  ],
  grove: [
    ["Thornwhip", "slash"], ["Moss Nova", "burst"], ["Canopy Ray", "beam"], ["Trunk Slam", "quake"],
  ],
  radiant: [
    ["Crown Flash", "beam"], ["Halo Slash", "slash"], ["Solar Bloom", "burst"], ["Glory Drop", "quake"],
  ],
  frost: [
    ["Rime Lance", "beam"], ["Frost Fang", "slash"], ["Shard Blizzard", "burst"], ["Glacier Stomp", "quake"],
  ],
  machine: [
    ["Rail Cannon", "beam"], ["Gear Saw", "slash"], ["Overclock Burst", "burst"], ["Piston Quake", "quake"],
  ],
  ember: [
    ["Cinder Breath", "beam"], ["Flame Claw", "slash"], ["Magma Burst", "burst"], ["Eruption", "quake"],
  ],
  umbral: [
    ["Void Ray", "beam"], ["Shade Rend", "slash"], ["Eclipse Nova", "burst"], ["Gravity Well", "quake"],
  ],
  crystal: [
    ["Prism Beam", "beam"], ["Facet Slash", "slash"], ["Reef Shatter", "burst"], ["Tidal Quake", "quake"],
  ],
};
const FALLBACK = [["Spark Beam", "beam"], ["Star Claw", "slash"], ["Nebula Burst", "burst"], ["Comet Slam", "quake"]];

// Element hues (degrees) keep each family's effects in its own colour range.
const ELEMENT_HUE = { verdant: 118, grove: 92, radiant: 46, frost: 192, machine: 28, ember: 12, umbral: 272, crystal: 182 };

// Temperament biases which style a beast prefers when it picks an attack.
const TEMPER_BIAS = {
  Fierce: { slash: 3, quake: 2 }, Bold: { beam: 2, quake: 2 }, Playful: { burst: 3 }, Curious: { beam: 2, burst: 1 },
  Serene: { beam: 2 }, Dreamy: { burst: 2 }, Steadfast: { quake: 3 }, Gentle: { burst: 2, beam: 1 },
};

export const TRIGGERS = ["tap", "timer", "chat"];
export const STYLES = ["beam", "slash", "burst", "quake"];

/** FNV-1a 32-bit hash over UTF-8 text. */
export function hashText(text) {
  let out = 2166136261;
  for (const byte of new TextEncoder().encode(String(text))) {
    out ^= byte;
    out = Math.imul(out, 16777619);
  }
  return out >>> 0;
}

/** A unit float in [0,1) that depends only on the seed key and the label. */
export function unit(seedKey, label) {
  // murmur3 finalizer so labels that differ in one character still spread well.
  let h = hashText(seedKey + "|" + label);
  h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b) >>> 0;
  h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35) >>> 0;
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

function num(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/** The stable identity of a genome for move picking. */
export function seedKeyFor(genome) {
  if (!genome || typeof genome !== "object") return "spark-fallback";
  const q = genome.quantum || {};
  return [genome.seed || "", q.top_state || "", q.counts_sha256 || "", genome.element || "", genome.temperament || ""].join(":");
}

/**
 * Build the per-beast move set from the recorded seed and the genome traits.
 * Each move carries its look (hue, particle count, beam width), its timing,
 * and how hard it shakes the habitat.
 */
export function buildMoveset(genome) {
  const key = seedKeyFor(genome);
  const element = genome && genome.element;
  const temperament = (genome && genome.temperament) || "Curious";
  const stats = (genome && genome.stats && (genome.stats[2] || genome.stats[1])) || {};
  const atk = num(stats.atk, 60), spd = num(stats.spd, 60), spark = num(stats.spark, 60);
  const baseHue = num(genome && genome.glow, NaN);
  const elementHue = ELEMENT_HUE[element] ?? (Number.isFinite(baseHue) ? baseHue : 200);
  const table = ELEMENT_MOVES[element] || FALLBACK;
  const bias = TEMPER_BIAS[temperament] || {};
  const moves = table.map(([name, style], index) => {
    const u = unit(key, "move:" + index);
    const v = unit(key, "look:" + index);
    return {
      id: `${style}-${index}`,
      name,
      style,
      hue: Math.round((elementHue + (u - 0.5) * 40 + 360) % 360),
      accentHue: Math.round((elementHue + 150 + v * 60) % 360),
      particles: 18 + Math.round(v * 22 + spark / 12),
      width: 6 + Math.round(u * 10),
      chargeMs: Math.round(420 + (1 - Math.min(1, spd / 140)) * 380 + u * 120),
      strikeMs: style === "beam" ? 520 : style === "slash" ? 320 : style === "burst" ? 460 : 560,
      shake: Math.min(14, Math.round(3 + atk / 18 + (style === "quake" ? 4 : 0))),
      power: Math.min(1, 0.45 + atk / 220 + u * 0.15),
      weight: 1 + (bias[style] || 0),
    };
  });
  const tempo = Math.max(0.2, num(genome && genome.behavior && genome.behavior.tempo_hz, 0.7));
  return {
    key,
    element: element || "spark",
    temperament,
    tempo,
    moves,
    // Roam path frequencies are fixed per beast so each one wanders its own figure.
    roam: {
      fx: 0.05 + unit(key, "roam:fx") * 0.07,
      fy: 0.07 + unit(key, "roam:fy") * 0.08,
      phase: unit(key, "roam:phase") * Math.PI * 2,
      reach: 0.55 + unit(key, "roam:reach") * 0.4,
    },
  };
}

/**
 * Pick the n-th attack for a trigger. Pure: the same moveset, counter and
 * trigger always give the same move, so a beast "fights" the same way on every
 * device that holds the same recorded seed.
 */
export function pickAttack(moveset, counter, trigger = "timer") {
  const moves = (moveset && moveset.moves) || [];
  if (!moves.length) return null;
  const n = Math.max(0, Math.floor(num(counter, 0)));
  const t = TRIGGERS.includes(trigger) ? trigger : "timer";
  const total = moves.reduce((sum, move) => sum + move.weight, 0);
  let roll = unit(moveset.key, `pick:${t}:${n}`) * total;
  let chosen = moves[moves.length - 1];
  for (const move of moves) {
    roll -= move.weight;
    if (roll < 0) { chosen = move; break; }
  }
  const crit = unit(moveset.key, `crit:${n}`) < 0.18;
  return { ...chosen, counter: n, trigger: t, crit, shake: crit ? Math.min(16, chosen.shake + 4) : chosen.shake };
}

/** Delay in ms before the n-th self-started attack (between 5.5 s and 12.5 s). */
export function nextAttackDelay(moveset, counter) {
  const key = (moveset && moveset.key) || "spark-fallback";
  return Math.round(5500 + unit(key, "delay:" + Math.max(0, Math.floor(num(counter, 0)))) * 7000);
}

/** Position on the seeded roam figure at time t (seconds), in [-1,1] for both axes. */
export function roamAt(moveset, t) {
  const r = (moveset && moveset.roam) || { fx: 0.08, fy: 0.1, phase: 0, reach: 0.7 };
  const time = num(t, 0);
  const x = Math.sin(time * r.fx * Math.PI * 2 + r.phase) * r.reach;
  const y = Math.sin(time * r.fy * Math.PI * 2 + r.phase * 0.5) * Math.cos(time * r.fx * Math.PI) * r.reach * 0.8;
  return { x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)), facing: Math.cos(time * r.fx * Math.PI * 2 + r.phase) >= 0 ? 1 : -1 };
}

/** Roar synthesis parameters from the genome voice and the move. */
export function roarFor(genome, move) {
  const voice = (genome && genome.voice) || {};
  const base = Math.max(70, Math.min(900, num(voice.base_pitch_hz, 220)));
  const formants = Array.isArray(voice.formants_hz) ? voice.formants_hz.map((f) => num(f, 900)) : [700, 1400];
  const style = (move && move.style) || "burst";
  const power = num(move && move.power, 0.7);
  return {
    startHz: Math.round(base * (style === "quake" ? 0.55 : style === "slash" ? 1.3 : 0.85)),
    peakHz: Math.round(base * (style === "beam" ? 2.2 : style === "slash" ? 2.6 : 1.6)),
    endHz: Math.round(base * 0.45),
    formantHz: Math.round(Math.max(300, Math.min(4000, formants[0] || 800))),
    noise: style === "quake" ? 0.85 : style === "burst" ? 0.6 : 0.4,
    seconds: Math.round((0.55 + power * 0.5 + (style === "beam" ? 0.25 : 0)) * 100) / 100,
    gain: Math.round((0.28 + power * 0.22) * 100) / 100,
  };
}
