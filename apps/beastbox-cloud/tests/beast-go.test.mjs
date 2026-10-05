import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { askBeast, guestSafeContext } from "../lib/companion/ask-beast.mjs";
import { BODY_RECIPES, catalogRoster, CHARLET_RECIPE, RARE_KEYS } from "../lib/companion/field-roster.mjs";
import { expandCompactRun, loadRecordedRuns, portraitRun, revealRecordedBeast, sealedMachine } from "../lib/companion/spark-machine.mjs";
import { wanderFrame } from "../lib/companion/wander.mjs";
import { noteModelActivity, petClaim, petPose } from "../lib/companion/pet-dragon.mjs";
import { adoptBeast, createSession } from "../lib/companion/session.mjs";
import { FULL_PATH, modeFor } from "../lib/companion/gba-dock.mjs";
import { focusBeast, hudCard, keyboardLegend, pressCartridge, QUICK, sheetGesture, sparkVisualState } from "../lib/companion/go-hud.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");

test("the field route is full screen and every other page keeps the cartridge parked or mini", () => {
  assert.equal(modeFor("/beast-cage/go"), "full");
  assert.equal(modeFor("/beast-cage/go/"), "full");
  assert.equal(FULL_PATH, "/beast-cage/go");
  for (const path of ["/beast-cage", "/beast-cage/talk", "/beast-cage/guest", "/beast-cage/play"]) {
    assert.equal(modeFor(path), "mini");
  }
  assert.equal(modeFor("/"), "mini");
  assert.equal(modeFor("/try"), "mini");
  assert.equal(modeFor("/workspace"), "parked");
  assert.equal(modeFor("/workspace#brain-bay"), "parked");
  const dock = read("components/lost-cosmos-dock.tsx");
  assert.match(dock, /modeFor/);
  assert.match(dock, /css\.full/);
  assert.match(dock, /data-cosmos-mode=\{mode\}/);
  assert.match(dock, /EJS_gameUrl = '\/api\/gba-rom'/);
  assert.match(dock, /data-rom-source="\/api\/gba-rom"/);
  assert.match(dock, /V11\.2 Spark/);
  assert.doesNotMatch(dock, /1\.11|11\.1/);
  assert.match(dock, /id="lost-cosmos-screen"/);
  assert.match(read("components/lost-cosmos-dock.module.css"), /left:-240vw/);
});

test("Brain Bay, Model Bay, cosmos world, and owner settings are not edited for the field screen", () => {
  for (const path of [
    "components/model-switcher.tsx",
    "components/cosmos-world.tsx",
    "components/device-panel.tsx",
    "components/live-senses.tsx",
    "components/beast-adventure.tsx",
    "app/api/status/route.ts",
    "app/api/guest/route.ts",
    "app/api/bridge/[endpoint]/route.ts",
  ]) {
    assert.doesNotMatch(read(path), /BeastGo|beast-cage\/go/);
  }
  const studio = read("components/studio.tsx");
  assert.match(studio, /href="\/beast-cage\/go"/);
  assert.match(studio, /LOST COSMOS/);
  for (const name of ["COSMOS WORLD", "BRAIN", "ORBIT", "BRAIN BAY", "MEMORY VAULT", "SYNAPSE TRACE", "ACTIVATION", "FILES", "AUTHORITY", "SETTINGS"]) {
    assert.match(studio, new RegExp(name));
  }
  assert.match(studio, /'BRAIN BAY'/);
  assert.match(studio, /'SETTINGS'/);
  assert.match(studio, /<ModelSwitcher /);
  assert.match(studio, /<CosmosWorld /);
  assert.match(read("components/beast-adventure.tsx"), /\/api\/bridge\/chat-start/);
});

test("cage nav links the field beside Adventure and the deploy guard stays off", () => {
  const portal = read("components/beast-cage-portal.tsx");
  assert.match(portal, /href="\/beast-cage\/play">Adventure<\/Link><Link href="\/beast-cage\/go">Go<\/Link>/);
  assert.match(read("components/beast-care-deck.tsx"), /href="\/beast-cage\/go"/);
  assert.match(read("app/beast-cage/go/page.tsx"), /BeastGo/);
  assert.match(read("app/layout.tsx"), /<CompanionProvider>\{children\}<\/CompanionProvider>/);
  assert.match(read("components/studio.tsx"), /<CosmosWorld /);
  const guard = JSON.parse(read("vercel.json"));
  assert.equal(guard.git.deploymentEnabled.main, false);
});

test("the field HUD is a portrait, quick buttons, a round menu, and swipe sheets over the same talk path", () => {
  const ui = read("components/beast-go.tsx");
  for (const label of ["Bag", "Beasts", "Talk", "Map", "Settings"]) assert.match(ui, new RegExp(label));
  assert.match(ui, /aria-label="Main menu"/);
  assert.match(ui, /sheetGesture/);
  assert.match(ui, /askBeast/);
  assert.match(ui, /SparkBeastCompanion/);
  assert.match(ui, /useCompanion\(\)/);
  assert.doesNotMatch(ui, /PixelBeast/);
  assert.equal(sparkVisualState("sleep"), "sleeping");
  assert.equal(sparkVisualState("happy"), "celebrating");
  assert.equal(sparkVisualState("idle"), "idle");
  assert.match(ui, /Swipe up for the menu/);
  assert.match(ui, /Touch controls/);
  assert.doesNotMatch(ui, /mockReply|fakeAnswer|Math\.random/);
  assert.deepEqual(QUICK.map((item) => item.label), ["Bag", "Beasts", "Talk", "Map", "Settings"]);
  assert.equal(sheetGesture(200, 140, false), "open");
  assert.equal(sheetGesture(100, 160, true), "close");
  assert.equal(sheetGesture(100, 120, true), "stay");
  const card = hudCard({ xp: 20, stage: 1, mood: "happy", displayName: "Moss", genome: { names: { 1: "Moss" } } });
  assert.equal(card.stage, 1);
  assert.equal(card.mood, "happy");
  assert.ok(card.ratio > 0 && card.ratio < 1);
  assert.equal(hudCard({ xp: 120, mood: "evolve" }).ratio, 1);
  assert.ok(keyboardLegend().some((row) => row[0] === "Z" && row[1] === "A"));
});

test("touch controls press the GBA keys the cartridge already listens for", () => {
  const events = [];
  const presses = [];
  const host = {
    EJS_emulator: { gameManager: { simulateInput: (player, index, value) => presses.push([player, index, value]) } },
    dispatchEvent: (event) => events.push(event),
  };
  assert.equal(pressCartridge("a", true, host), true);
  assert.equal(pressCartridge("a", false, host), true);
  assert.deepEqual(presses, [[0, 8, 1], [0, 8, 0]]);
  assert.equal(events[0].type, "keydown");
  assert.equal(events[0].key, "z");
  assert.equal(events[1].type, "keyup");
  assert.equal(pressCartridge("nope", true, host), false);
});

test("focusing another beast keeps the care stats on the party row", () => {
  const session = createSession();
  adoptBeast(session, { seed: "one", names: { 1: "Moss" } }, "Moss");
  session.beast.xp = 12;
  session.beast.bond = 4;
  session.bestiary.push({ seed: "two", name: "Lumen", genome: { seed: "two", names: { 1: "Lumen" } }, xp: 3, bond: 2 });
  const focused = focusBeast(session, "two");
  assert.equal(focused.ok, true);
  assert.equal(session.beast.seed, "two");
  assert.equal(session.beast.xp, 3);
  assert.equal(session.bestiary.find((item) => item.seed === "one").xp, 12);
  assert.equal(session.bestiary.find((item) => item.seed === "one").bond, 4);
});

function jsonResponse(body, ok = true) {
  return { ok, json: async () => body };
}

test("field talk uses Brain Bay, then the guest host, and leaves an empty reply when neither answers", async () => {
  const calls = [];
  const owner = await askBeast({
    context: { name: "Moss", location: "Eridoria Grove", nearby: [], mood: "idle", level: 1, xp: 0, bond: 1, energy: 100, memories: [], sensors: [] },
    saying: "hello",
    fetchImpl: async (url) => {
      calls.push(String(url));
      if (url === "/api/status") return jsonResponse({ owner: true, backendReachable: true, providerKind: "ollama_cloud" });
      if (url === "/api/bridge/chat-start") return jsonResponse({ job_id: "job-1", state: "done", result: { result: { response: "From Brain Bay." } } });
      throw new Error("guest should stay quiet when Brain Bay answered");
    },
    uuid: () => "11111111-1111-4111-8111-111111111111",
  });
  assert.equal(owner.reply, "From Brain Bay.");
  assert.match(owner.label, /ollama_cloud/);
  assert.equal(owner.pending, false);
  assert.ok(calls.includes("/api/bridge/chat-start"));
  assert.equal(calls.includes("/api/guest"), false);

  const pendingCalls = [];
  const pending = await askBeast({
    context: { name: "Moss", location: "Eridoria Grove", nearby: [], mood: "idle", level: 1, xp: 0, bond: 1, energy: 100, memories: [], sensors: [] },
    saying: "still there?",
    now: () => 10_000,
    deadlineMs: 0,
    fetchImpl: async (url) => {
      pendingCalls.push(String(url));
      if (url === "/api/status") return jsonResponse({ owner: true, backendReachable: true, providerKind: "ollama_cloud" });
      return jsonResponse({ job_id: "job-2", state: "running" });
    },
  });
  assert.equal(pending.reply, "");
  assert.equal(pending.pending, true);
  assert.match(pending.label, /No substitute reply was invented/);
  assert.equal(pendingCalls.includes("/api/guest"), false);

  const quiet = await askBeast({
    context: { name: "Moss", location: "Eridoria Grove", nearby: [], mood: "idle", level: 1, xp: 0, bond: 1, energy: 100, memories: [], sensors: [] },
    saying: "anyone?",
    fetchImpl: async (url) => {
      if (url === "/api/status") return jsonResponse({ owner: false, backendReachable: false, providerKind: "" });
      return jsonResponse({ error: "Guest model host is not configured" });
    },
  });
  assert.equal(quiet.reply, "");
  assert.equal(quiet.pending, false);
  assert.match(quiet.label, /not configured/);
});

test("guests on the field use the guest-safe brain and a local beast, with no owner route", async () => {
  const secret = "owner private cosmos memory";
  const calls = [];
  let sent = "";
  const guest = await askBeast({
    audience: "guest",
    context: guestSafeContext({
      name: "Moss",
      location: "Lost Cosmos",
      nearby: ["grove"],
      mood: "idle",
      level: 1,
      xp: 0,
      bond: 1,
      energy: 100,
      memories: [secret],
      sensors: ["camera on"],
    }),
    saying: "hello",
    fetchImpl: async (url, init) => {
      calls.push(String(url));
      sent = String(init?.body || "");
      if (String(url).includes("bridge") || String(url).includes("status")) throw new Error("guest called an owner route");
      return jsonResponse({
        provider: "rawrphos-local",
        model: "rawrphos-native",
        step: 14000,
        guest_stateless: true,
        reply: "Hello from the guest host.",
      });
    },
  });
  assert.equal(guest.reply, "Hello from the guest host.");
  assert.equal(guest.audience, "guest");
  assert.deepEqual(calls, ["/api/guest"]);
  assert.equal(sent.includes(secret), false);
  assert.equal(sent.includes("camera on"), false);
  assert.deepEqual(guestSafeContext({ memories: [secret], sensors: ["camera on"] }).memories, []);
  const ui = read("components/beast-go.tsx");
  assert.match(ui, /audience: guestMode \? 'guest'/);
  assert.match(ui, /No owner authority and no private memory/);
  assert.match(ui, /guest-safe brain/);
  assert.doesNotMatch(ui, /mockReply|fakeAnswer|Math\.random/);
  for (const path of ["app/page.tsx", "app/try/page.tsx", "components/gba-guest-lab.tsx", "components/beast-cage-talk.tsx"]) {
    assert.match(read(path), /href="\/beast-cage\/go"/);
  }
  const talk = read("components/beast-cage-talk.tsx");
  assert.match(talk, /CosmicCompanion3D/);
  assert.match(talk, /SparkWanderer/);
  assert.match(talk, /fetch\('\/api\/guest'/);
  assert.doesNotMatch(talk, /\/api\/bridge|localStorage|ownerToken|mockReply|fakeAnswer|Math\.random/);
  assert.match(read("components/gba-guest-lab.tsx"), /No camera, microphone or memory access/);
  assert.doesNotMatch(read("components/gba-guest-lab.tsx"), /\/api\/bridge|ownerToken|navigator\.mediaDevices/);
});

test("the roster covers every body, stages I through III, Charlet, and twelve rares", () => {
  const table = JSON.parse(read("public/spark/runs.json"));
  const catalog = catalogRoster(table.runs.map(expandCompactRun));
  assert.equal(catalog.creatures.length, BODY_RECIPES.length);
  assert.equal(new Set(catalog.creatures.map((item) => item.body)).size, 11);
  for (const creature of catalog.creatures) {
    assert.deepEqual(creature.stages.map((stage) => stage.mark), ["I", "II", "III"]);
    assert.equal(creature.stages.every((stage) => stage.name.length > 1), true);
  }
  assert.equal(catalog.charlet.name, "Charlet");
  assert.equal(catalog.charlet.body, CHARLET_RECIPE.body);
  assert.equal(catalog.charlet.island, "Cinder Drift");
  assert.equal(catalog.rares.length, 12);
  assert.deepEqual(catalog.rares.map((item) => item.key), RARE_KEYS);
  assert.equal(catalog.rares.every((item) => item.num_bits === 12), true);
  const roster = read("components/spark-field-roster.tsx");
  assert.match(roster, /Charlet/);
  assert.match(roster, /Stage \{STAGE_MARK/);
  assert.match(roster, /renderBeast/);
  assert.match(read("app/api/companion-release/route.ts"), /sim_earth_embedded:false/);
});

test("the spark machine stays sealed and reveals one recorded beast, including public shards", async () => {
  assert.deepEqual(sealedMachine(), { sealed: true, names: [], keys: [] });
  const calls = [];
  const runs = await loadRecordedRuns(async (url) => {
    calls.push(String(url));
    if (String(url).endsWith("user-seeds-20261004.json")) {
      return { json: async () => ({ shards: ["/spark/user-seeds-20261004-1.json"] }) };
    }
    if (String(url).endsWith("/spark/runs.json")) {
      return { json: async () => ({ runs: [
        { b: "ibm_fez", j: "basejob", p: 0, n: 1, s: 4, h: "aa", k: "ibm_fez:basejob", c: "0:3,1:1" },
        { b: "ibm_fez", j: "wide", p: 0, n: 5, s: 8, h: "bb", k: "ibm_fez:wide", c: "00000:4,00001:4" },
      ] }) };
    }
    return { json: async () => ({ runs: [
      { b: "ibm_torino", j: "newjob", p: 0, n: 5, s: 8, h: "cc", k: "ibm_torino:newjob", c: "00000:2,00001:6" },
    ] }) };
  });
  assert.ok(calls.includes("/spark/user-seeds-20261004-1.json"));
  assert.equal(portraitRun({ id: "one", seed: "one" }, runs).num_bits >= 2, true);
  assert.equal(runs.some((run) => run.job_id === "newjob"), true);
  assert.equal(portraitRun({ id: "one", seed: "one" }, runs.filter((run) => run.num_bits < 2)), null);
  const profile = {
    id: "bb-field",
    seed: "sparkfield01",
    game: { stats: { signal: 30, memory: 30, stability: 30, energy: 40, resonance: 20 } },
    temperament: { caution: 20, playfulness: 40 },
  };
  const first = revealRecordedBeast(profile, runs);
  const second = revealRecordedBeast(profile, runs);
  assert.equal(first.ok, true);
  assert.equal(first.name, second.name);
  assert.equal(first.runKey, second.runKey);
  assert.equal(typeof first.name, "string");
  const machine = read("components/spark-machine.tsx");
  assert.match(machine, /crypto\.getRandomValues/);
  assert.match(machine, /does not show what will come out/);
  assert.match(machine, /loadRecordedRuns/);
  assert.doesNotMatch(machine, /<select|Math\.random|\/api\/bridge|ownerToken/);
  assert.match(read("lib/companion/spark-machine.mjs"), /user-seeds-20261004\.json/);
});

test("the chat beast idles, walks, emotes, and reacts", () => {
  assert.equal(wanderFrame(10, 0, false, false).mode, "idle");
  assert.equal(wanderFrame(80, 0, false, false).mode, "walk");
  assert.equal(wanderFrame(4, 30, false, false).mode, "emote");
  assert.equal(wanderFrame(4, 8, false, false).mode, "react");
  assert.equal(wanderFrame(4, 0, true, false).visual, "thinking");
  assert.equal(wanderFrame(80, 0, false, true).x, 0);
  const wander = read("components/spark-wanderer.tsx");
  assert.match(wander, /SparkBeastCompanion/);
  assert.match(wander, /data-spark-wander="true"/);
  assert.match(read("components/beast-go.tsx"), /SparkWanderer/);
  assert.doesNotMatch(wander, /Math\.random/);
});

test("the pet dragon loops from a recorded seed and only grows on-device weights", () => {
  const seeded = petPose(3, { seed: 9 }, false);
  const again = petPose(3, { seed: 9 }, false);
  assert.equal(seeded.looping, true);
  assert.equal(seeded.claim, "quantum-seed");
  assert.deepEqual(seeded, again);
  assert.equal(petPose(4, { seed: 9, chat: true }, false).visual, "thinking");
  assert.equal(petPose(4, { seed: 9, sensor: 0.4 }, false).visual, "listening");
  assert.equal(petPose(80, { seed: 9 }, true).x, 0);
  assert.match(petClaim(seeded), /recorded quantum seed/);
  const session = createSession();
  const before = session.mind.steps;
  const pet = noteModelActivity(session, "hello beast", "ollama_cloud");
  assert.equal(pet.learned, true);
  assert.equal(pet.modelWeightsTrained, false);
  assert.ok(session.mind.steps > before);
  assert.match(petClaim({ claim: "on-device-weights" }), /were not trained/);
  const dock = read("components/cosmic-companion-dock.tsx");
  assert.match(dock, /data-pet-dragon="true"/);
  assert.match(dock, /seedRunKey=\{DRAGON_RUN_KEY\}/);
  assert.match(dock, /selectSafeRoamSpot/);
  assert.match(read("components/companion-provider.tsx"), /data-pet-dragon="true"/);
  assert.match(read("components/studio.tsx"), /beastbox:pet-growth/);
  assert.match(read("components/beast-care-deck.tsx"), /not trained by the pet dragon/);
  assert.doesNotMatch(dock, /Math\.random/);
});

test("field touch UI is one Game Boy-style deck with a closable sheet instead of stacked floating controls", () => {
  const ui = read("components/beast-go.tsx");
  const css = read("components/beast-go.module.css");
  assert.match(ui, /data-handheld-controls="game-boy"/);
  assert.match(ui, /aria-label="Select"/);
  assert.match(ui, /aria-label="Close field menu"/);
  assert.match(css, /\.handheld\{/);
  assert.match(css, /\.sheetClose\{/);
  assert.doesNotMatch(css, /\.orb\{/);
});
