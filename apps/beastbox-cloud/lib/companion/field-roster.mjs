/**
 * Full Spark Beast roster built from recorded runs.
 * Names come from the public genome, including stages I–III, Charlet, and 12 rares.
 */

import { buildGenome } from "../../public/spark/genome.mjs";

export const STAGE_MARK = { 1: "I", 2: "II", 3: "III" };

export const BODY_RECIPES = [
  { body: "pup", traits: { focus: 0, calm: 0, spark: 100 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "fox", traits: { focus: 0, calm: 100, spark: 0 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "sprout", traits: { focus: 0, calm: 40, spark: 80 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "moth", traits: { focus: 0, calm: 0, spark: 40 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "axolotl", traits: { focus: 0, calm: 40, spark: 60 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "golem", traits: { focus: 0, calm: 0, spark: 60 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "dragonling", traits: { focus: 0, calm: 0, spark: 0 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "bird", traits: { focus: 0, calm: 20, spark: 20 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "fish", traits: { focus: 0, calm: 40, spark: 0 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "serpent", traits: { focus: 0, calm: 0, spark: 80 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
  { body: "biped", traits: { focus: 0, calm: 40, spark: 100 }, runKey: "ibm_marrakesh:d93d8pgoamcc73dc3afg" },
];

export const CHARLET_RECIPE = {
  name: "Charlet",
  stage: 1,
  body: "dragonling",
  island: "Cinder Drift",
  traits: { focus: 40, calm: 0, spark: 40 },
  runKey: "ibm_fez:d6lmid0bfi7c73a2lae0",
};

/** Twelve distinct 12-bit recorded runs: two publications from each rare job. */
export const RARE_KEYS = [
  "ibm_kingston:da5qu843jnrc73ahka2g#pub0",
  "ibm_kingston:da5qu843jnrc73ahka2g#pub1",
  "ibm_kingston:da5quo6aa69c739l6jl0#pub0",
  "ibm_kingston:da5quo6aa69c739l6jl0#pub1",
  "ibm_kingston:da5qv8maa69c739l6k3g#pub0",
  "ibm_kingston:da5qv8maa69c739l6k3g#pub1",
  "ibm_marrakesh:da5qvqs3jnrc73ahkbj0#pub0",
  "ibm_marrakesh:da5qvqs3jnrc73ahkbj0#pub1",
  "ibm_marrakesh:da5r0c3otlns739c8h10#pub0",
  "ibm_marrakesh:da5r0c3otlns739c8h10#pub1",
  "ibm_marrakesh:da5r0ts3jnrc73ahkck0#pub0",
  "ibm_marrakesh:da5r0ts3jnrc73ahkck0#pub1",
];

function stagesOf(genome) {
  return [1, 2, 3].map((stage) => ({
    stage,
    mark: STAGE_MARK[stage],
    name: genome.names[stage],
  }));
}

function requireRun(byKey, key) {
  const run = byKey.get(key);
  if (!run) throw new Error("Recorded roster run is missing: " + key);
  return run;
}

export function catalogRoster(runs) {
  const byKey = new Map((runs || []).map((run) => [run.key, run]));
  const creatures = BODY_RECIPES.map((recipe) => {
    const genome = buildGenome(recipe.traits, requireRun(byKey, recipe.runKey), null, 10);
    return {
      kind: "creature",
      body: genome.body,
      island: genome.island,
      stages: stagesOf(genome),
      genome,
    };
  });
  const charletGenome = buildGenome(CHARLET_RECIPE.traits, requireRun(byKey, CHARLET_RECIPE.runKey), null, 10);
  const rares = RARE_KEYS.map((key) => {
    const run = requireRun(byKey, key);
    const genome = buildGenome({ focus: 40, calm: 40, spark: 40 }, run, null, 10);
    return {
      kind: "rare",
      key,
      num_bits: run.num_bits,
      name: genome.names[1],
      body: genome.body,
      genome,
    };
  });
  return {
    creatures,
    charlet: {
      kind: "charlet",
      name: charletGenome.names[1],
      body: charletGenome.body,
      island: charletGenome.island,
      stages: stagesOf(charletGenome),
      genome: charletGenome,
    },
    rares,
  };
}
