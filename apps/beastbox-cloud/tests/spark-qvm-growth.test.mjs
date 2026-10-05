import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { expandQvmReceipt, growthFromQvmBatch, QVM_SOURCE_CLASS, QVM_SOURCE_SHA, scenarioRuns } from "../public/spark/qvm-growth.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");

test("the pinned Azure Rigetti QVM simulator receipt expands to 24 deterministic browser runs", () => {
  const receipt = JSON.parse(read("public/spark/rigetti-qvm-sim.json"));
  assert.equal(receipt.source_class, QVM_SOURCE_CLASS);
  assert.equal(receipt.public_rows_sha256, QVM_SOURCE_SHA);
  const runs = expandQvmReceipt(receipt);
  assert.equal(runs.length, 24);
  assert.equal(new Set(runs.map((row) => row.job_id)).size, 24);
  assert.equal(runs.every((row) => row.backend === "rigetti.sim.qvm" && row.num_bits === 2), true);
  assert.equal(scenarioRuns(runs, 1).length, 3);
  const growth = growthFromQvmBatch(runs[0]);
  assert.ok(growth.delta >= 0.05 && growth.delta <= 0.18);
  assert.ok(growth.entropy >= 0 && growth.entropy <= 1);
});

test("public simulator growth is visible, browser-local, and never claims QPU or native evolution", () => {
  const app = read("public/spark/app.mjs");
  const page = read("public/spark/index.html");
  assert.match(app, /expandQvmReceipt/);
  assert.match(app, /qvmPulseUntil/);
  assert.match(app, /browserReact/);
  assert.match(app, /BODIES\.length/);
  assert.match(page, /archived Azure-hosted Rigetti QVM scenario/);
  assert.match(page, /not a QPU run/);
  assert.match(page, /does not crawl arbitrary sites/);
  assert.match(page, /native stage unchanged/);
  assert.doesNotMatch(page, /live Rigetti|Rigetti QPU/);
});

// PR runs against guarded main; simulator tests do not enable production deploys.
