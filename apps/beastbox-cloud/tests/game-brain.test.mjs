import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createTrail, followStep, goTo, reactionFor, talkAndGrow } from "../lib/companion/adventure.mjs";
import { chooseBrain, fallbackAfterFailure, interpretModelResult } from "../lib/companion/brain.mjs";
import { exportQbeast, importQbeast } from "../lib/companion/cage.mjs";
import { buildChatContext, renderContextPrompt } from "../lib/companion/context.mjs";
import { createMind, observeText } from "../lib/companion/learn.mjs";
import { readCameraFrame, readMicSample, readSignal, sensorSummary } from "../lib/companion/sensors.mjs";
import { adoptBeast, createSession } from "../lib/companion/session.mjs";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import { simulate } from "../lib/companion/spark/signal.mjs";

const runs = JSON.parse(readFileSync(new URL("../lib/companion/spark/runs.json", import.meta.url), "utf8"));
const repo = fileURLToPath(new URL("../../../", import.meta.url));

function beastSession() {
  const session = createSession();
  const genome = buildGenome({ focus: 40, calm: 80, spark: 20 }, runs[0], null);
  adoptBeast(session, genome, "Moss");
  return session;
}

test("context names the place, nearby things, mood, level, memories, and live sensors", () => {
  const session = beastSession();
  talkAndGrow(session, "sunflower code is marigold");
  const trail = goTo(createTrail(), "observatory");
  const sensors = {
    camera: readCameraFrame(null, null),
    mic: readMicSample(0.2, 0.01),
    signal: readSignal({ enabled: false }),
  };
  const context = buildChatContext({ session, trail, sensors, sensorLog: ["camera off"] });
  assert.equal(context.location, "Crown Observatory");
  assert.ok(context.nearby.includes("star chart"));
  assert.equal(context.level, session.beast.stage);
  assert.ok(context.xp >= 3);
  assert.ok(context.memories.some((line) => line.includes("sunflower")));
  const prompt = renderContextPrompt(context, "what is near us?");
  assert.match(prompt, /Crown Observatory/);
  assert.match(prompt, /star chart/);
  assert.match(prompt, /mic loudness/);
  assert.match(prompt, /camera off/);
  assert.match(prompt, /headband off/);
  assert.ok(prompt.length <= 700);
  assert.doesNotMatch(prompt, /I can see you|I am conscious/);
});

test("each sensor fails closed on its own and a simulation never pretends to be Muse", () => {
  assert.equal(readCameraFrame(null, null).reason, "camera-off");
  assert.equal(readMicSample(null, null).reason, "mic-off");
  assert.equal(readSignal({ enabled: false }).mode, "off");
  const frame = new Uint8ClampedArray(16);
  frame.fill(10);
  const next = new Uint8ClampedArray(frame);
  next[0] = 250;
  const camera = readCameraFrame(frame, next);
  assert.equal(camera.available, true);
  assert.ok(camera.motion > 0);
  const quiet = readMicSample(0.01, 0);
  const heard = readMicSample(0.2, 0.01);
  assert.equal(quiet.onset, false);
  assert.equal(heard.onset, true);
  assert.equal(readMicSample(null, 0.4).available, false);
  const simulated = readSignal({ enabled: true, simulated: simulate("focused") });
  assert.equal(simulated.mode, "simulated");
  assert.equal(simulated.available, true);
  const muse = readSignal({ museTraits: { focus: 10, calm: 20, spark: 80 } });
  assert.equal(muse.mode, "muse");
  assert.match(sensorSummary({ camera: readCameraFrame(null, null), mic: readMicSample(null, null), signal: readSignal() }), /camera off/);
  assert.match(sensorSummary({ camera, mic: heard, signal: simulated }), /simulated/);
  assert.doesNotMatch(sensorSummary({ camera, mic: heard, signal: simulated }), /mode muse|Muse/);
});

test("model routing uses Brain Bay, then the guest host, then the local mind, and never invents a model reply", () => {
  const owner = chooseBrain({ ownerReady: true, providerKind: "ollama_cloud", guestReady: true });
  assert.equal(owner.route, "owner-bridge");
  assert.match(owner.label, /ollama_cloud/);
  const guest = chooseBrain({ ownerReady: false, guestReady: true });
  assert.equal(guest.route, "guest-rawrphos");
  assert.equal(chooseBrain({ ownerReady: true, providerKind: "reference", guestReady: false }).route, "local-mind");
  assert.equal(chooseBrain({}).route, "local-mind");
  assert.match(chooseBrain({}).label, /No language model is connected/);
  const verified = interpretModelResult("guest-rawrphos", {
    provider: "rawrphos-local", model: "rawrphos-native", step: 14000, guest_stateless: true, reply: "Hello from the checkpoint.",
  });
  assert.equal(verified.ok, true);
  assert.equal(verified.reply, "Hello from the checkpoint.");
  const missing = interpretModelResult("guest-rawrphos", { error: "Guest model host is not configured" });
  assert.equal(missing.ok, false);
  assert.equal(interpretModelResult("owner-bridge", { result: { result: { response: "From Brain Bay." } } }).reply, "From Brain Bay.");
  assert.equal(interpretModelResult("owner-bridge", {}).ok, false);
  assert.equal(interpretModelResult("local-mind", { reply: "should not be trusted" }).ok, false);
  const fallback = fallbackAfterFailure(missing.reason);
  assert.equal(fallback.route, "local-mind");
  assert.match(fallback.failure, /not configured/);
});

test("talking grows xp through the care rules and the qbeast file keeps the conversation", () => {
  const session = beastSession();
  const before = session.beast.xp;
  const grown = talkAndGrow(session, "sunflower code is marigold");
  assert.equal(grown.safe, true);
  assert.ok(session.beast.xp > before);
  assert.ok(session.mind.vocab.marigold.count >= 1);
  const trail = createTrail("shore");
  let stepped = goTo(trail, "nest");
  assert.equal(stepped.moving, true);
  for (let i = 0; i < 30 && stepped.moving; i++) stepped = followStep(stepped);
  assert.equal(stepped.moving, false);
  const reaction = reactionFor({
    genome: session.beast.genome,
    beast: { ...session.beast, energy: 10, mood: "idle" },
    trail: stepped,
    sensors: { camera: readCameraFrame(null, null), mic: readMicSample(null, null), signal: readSignal() },
  });
  assert.equal(reaction.emote, "sleep");
  const text = exportQbeast(session.beast.genome, session.mind, session.beast.xp, session.chat.map((turn) => `${turn.role}: ${turn.text}`));
  const imported = importQbeast(text);
  assert.equal(imported.xp, session.beast.xp);
  assert.ok(imported.mind.vocab.sunflower.count >= 1);
  assert.ok(imported.notes.some((line) => line.includes("sunflower")));
  const parsed = spawnSync(process.execPath, ["--experimental-strip-types", "--import", "./apps/beastbox-cloud/tests/register-ts.mjs", "--input-type=module", "-e", `
    import { parseSnapshot } from './packages/quantum-beast/src/verifier.ts';
    const text = ${JSON.stringify(text)};
    const snap = await parseSnapshot(text);
    if (snap.format !== 'QBEAST1' || snap.events.length < 2) process.exit(2);
  `], { cwd: repo, encoding: "utf8" });
  assert.equal(parsed.status, 0, parsed.stderr || parsed.stdout);
});

test("blocked talk does not grow xp or pattern weights", () => {
  const session = beastSession();
  const mind = createMind();
  session.mind = mind;
  observeText(mind, "sunflower");
  const xp = session.beast.xp;
  const result = talkAndGrow(session, "this is porn");
  assert.equal(result.safe, false);
  assert.equal(session.beast.xp, xp);
  assert.equal(session.mind.steps, 1);
});
