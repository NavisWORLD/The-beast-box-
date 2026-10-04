import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { exportLcx1, exportQbeast, importLcx1, importQbeast } from "../lib/companion/cage.mjs";
import { createMind, observeText } from "../lib/companion/learn.mjs";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import { renderSprite } from "../lib/companion/spark/render.mjs";
import { createHash } from "node:crypto";

const runs = JSON.parse(readFileSync(new URL("../lib/companion/spark/runs.json", import.meta.url), "utf8"));
const run = runs.find((item) => item.key === "ibm_marrakesh:d93d8pgoamcc73dc3afg");
const traits = { focus: 40, calm: 40, spark: 20 };

function genome() {
  return buildGenome(traits, run, null);
}

test("the same spark seed draws the same sprite", () => {
  const left = renderSprite(genome(), 2);
  const right = renderSprite(genome(), 2);
  const hash = createHash("sha256").update(Buffer.from(left.rgba)).digest("hex");
  assert.equal(createHash("sha256").update(Buffer.from(right.rgba)).digest("hex"), hash);
  assert.equal(left.rgba.length, 64 * 64 * 4);
  assert.ok(left.rgba.some((value) => value !== 0));
});

test("qbeast and LCX1 round-trip the beast, the xp, and the learned weights", () => {
  const beast = genome();
  const mind = createMind();
  observeText(mind, "sunflower code is marigold");
  const text = exportQbeast(beast, mind, 45);
  const imported = importQbeast(text);
  assert.equal(imported.card.run, run.key);
  assert.equal(imported.card.name, beast.names[2]);
  assert.equal(imported.card.traits.focus, 40);
  assert.equal(imported.xp, 45);
  assert.equal(imported.mind.vocab.marigold.count, 1);
  assert.equal(imported.genome.seed, beast.seed);
  assert.equal(imported.snapshot.format, "QBEAST1");
  assert.equal(imported.snapshot.public_state.mode, "unavailable");
  assert.deepEqual(imported.snapshot.progress, { trust: 0, bond: 0, evolution_stage: 0 });

  const save = exportLcx1(beast, 45);
  assert.equal(String.fromCharCode(...save.subarray(24832, 24836)), "LCX1");
  const cage = importLcx1(save);
  assert.equal(cage.focus, 40);
  assert.equal(cage.calm, 40);
  assert.equal(cage.spark, 20);
  assert.equal(cage.xp, 45);
  assert.equal(cage.stage, 2);
  assert.ok(cage.callsign.length > 0);
  const again = importLcx1(save.slice(24832, 24832 + 644));
  assert.equal(again.focus, 40);
  assert.equal(again.callsign, cage.callsign);
});

test("a published Spark Beasts qbeast still loads", () => {
  const cases = JSON.parse(readFileSync(new URL("../../../spark-beasts/golden/case.json", import.meta.url), "utf8"));
  const loaded = importQbeast(cases[0].qbeast);
  assert.equal(loaded.snapshot.format, "QBEAST1");
  assert.equal(loaded.card.run, cases[0].run);
  assert.equal(loaded.mind, null);
});
