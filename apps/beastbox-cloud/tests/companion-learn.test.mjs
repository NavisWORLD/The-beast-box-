import assert from "node:assert/strict";
import test from "node:test";
import { createMind, loadMind, memoryDb, observeText, saveMind, weightSum } from "../lib/companion/learn.mjs";

test("hebbian weights change after training and survive a reload", async () => {
  const mind = createMind();
  const before = weightSum(mind);
  const first = observeText(mind, "sunflower code is marigold");
  assert.equal(first.learned, true);
  assert.ok(weightSum(mind) > before);
  assert.ok(mind.vocab.sunflower.count >= 1);
  assert.equal(mind.steps, 1);
  observeText(mind, "sunflower code is marigold");
  assert.equal(mind.vocab.marigold.count, 2);
  const db = memoryDb();
  await saveMind(db, mind);
  const loaded = await loadMind(db);
  assert.deepEqual(loaded.weights, mind.weights);
  assert.equal(loaded.steps, mind.steps);
  assert.equal(loaded.vocab.sunflower.count, 2);
  assert.equal(loaded.next.sunflower.code, 2);
});

test("blocked phrases do not move weights", () => {
  const mind = createMind();
  const before = JSON.stringify(mind.weights);
  const result = observeText(mind, "this is porn");
  assert.equal(result.learned, false);
  assert.equal(JSON.stringify(mind.weights), before);
  assert.equal(mind.steps, 0);
});
