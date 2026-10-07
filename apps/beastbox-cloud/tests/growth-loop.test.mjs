import test from "node:test";
import assert from "node:assert/strict";
import { adoptBeast, applyGameReturn, createSession, exportSession, grantXp, importSession, progressFromLocalGrowth, swapBrain } from "../lib/companion/session.mjs";
import { care, rememberExchange, talkAndGrow, train } from "../lib/companion/adventure.mjs";

function hatch() {
  const session = createSession();
  adoptBeast(session, { seed: "spine-seed", names: { 1: "Miraby" }, island: "grove", body: "pup" }, "Miraby");
  session.beast.qbeast = { profile: { id: "bb-spine01", seed: "spine-seed" } };
  session.beast.nativeStage = 1;
  grantXp(session, 0, "attach");
  return session;
}

test("care, train, talk, and memory advance one unsigned QBEAST and survive reload", () => {
  const session = hatch();
  const id = session.beast.localGrowth.qbeast_id;
  const cared = care(session, "pet");
  const trained = train(session, 2, 6);
  const talked = talkAndGrow(session, "hello beast");
  const remembered = rememberExchange(session, "we went to the reef", "I kept the echo");
  const xp = session.beast.xp;
  const bond = session.beast.bond;
  assert.equal(cared.qbeast_id, "bb-spine01");
  assert.equal(talked.qbeast_id, "bb-spine01");
  assert.equal(session.beast.localGrowth.status, "unsigned-local");
  assert.equal(session.beast.localGrowth.signature, "none");
  assert.equal(session.beast.qbeast.progress, undefined);
  assert.equal(session.beast.qbeastProgress, "pending-unsigned");
  assert.equal(session.beast.xp, 4 + 8 + 3 + 3);
  assert.equal(session.beast.bond, 1 + 2 + 1 + 1);
  assert.equal(session.beast.stage, 1);
  assert.ok(session.mind.steps > 0);

  const reloaded = importSession(exportSession(session));
  assert.equal(reloaded.beast.localGrowth.qbeast_id, id);
  assert.equal(reloaded.beast.xp, xp);
  assert.equal(reloaded.beast.bond, bond);
  assert.equal(reloaded.mind.steps, session.mind.steps);
  grantXp(reloaded, 0, "reload");
  assert.equal(reloaded.beast.xp, xp);
});

test("brain swap keeps identity, xp, bond, and memory, then growth continues", () => {
  const session = hatch();
  care(session, "feed");
  const before = { id: session.beast.localGrowth.qbeast_id, xp: session.beast.xp, bond: session.beast.bond, steps: session.mind.steps };
  const swapped = swapBrain(session, "rawrphos-native");
  assert.equal(swapped.qbeast_id, before.id);
  assert.equal(swapped.xp, before.xp);
  assert.equal(swapped.bond, before.bond);
  assert.equal(swapped.memory_steps, before.steps);
  care(session, "pet");
  assert.equal(session.beast.localGrowth.qbeast_id, before.id);
  assert.equal(session.beast.xp, before.xp + 4);
  assert.equal(session.beast.localGrowth.model.provider, "rawrphos-native");
});

test("Lost COSMOS return updates allowlisted game fields once and cannot rewrite identity", () => {
  const session = hatch();
  const seed = session.beast.seed;
  const first = applyGameReturn(session, {
    schema: "lost-cosmos-return-v1",
    qbeast_id: "bb-spine01",
    event_id: "save-1",
    game_xp: 12,
    beacons: 2,
    echoes: 1,
    seed: "forged",
    owner_memory: "nope",
  });
  assert.equal(first.ok, true);
  assert.equal(first.duplicate, false);
  assert.equal(session.beast.seed, seed);
  assert.equal(session.beast.game.game_xp, 12);
  assert.equal(session.beast.game.beacons, 2);
  assert.equal(session.beast.game.owner_memory, undefined);
  const again = applyGameReturn(session, { schema: "lost-cosmos-return-v1", qbeast_id: "bb-spine01", event_id: "save-1", game_xp: 99 });
  assert.equal(again.duplicate, true);
  assert.equal(session.beast.game.game_xp, 12);
  const wrong = applyGameReturn(session, { schema: "lost-cosmos-return-v1", qbeast_id: "bb-other", event_id: "save-2", game_xp: 50 });
  assert.equal(wrong.ok, false);
  assert.equal(session.beast.localGrowth.qbeast_id, "bb-spine01");
});

test("local growth maps into existing QBEAST progress fields and stays unsigned", () => {
  const session = hatch();
  care(session, "pet");
  const progress = progressFromLocalGrowth(session.beast);
  assert.equal(progress.trust, 0);
  assert.equal(progress.bond, session.beast.bond);
  assert.equal(progress.evolution_stage, 0);
  assert.equal(session.beast.seed, "spine-seed");
  assert.equal(session.beast.localGrowth.qbeast_id, "bb-spine01");
  assert.equal(session.beast.localGrowth.signature, "none");
  assert.equal(session.beast.qbeast.progress, undefined);
});


test("old session without local growth still loads", () => {
  const legacy = { schema: "beastbox-companion-session-v1", beast: { seed: "old", xp: 9, bond: 3, energy: 80, stage: 1, mood: "idle" }, train: { score: 1, rounds: 1 } };
  const session = importSession(legacy);
  assert.equal(session.beast.xp, 9);
  assert.equal(session.beast.localGrowth.qbeast_id, "seed:old");
  assert.equal(session.beast.localGrowth.status, "unsigned-local");
});
