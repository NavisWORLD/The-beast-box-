import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { askBeast } from "../lib/companion/ask-beast.mjs";
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
  assert.equal(modeFor("/workspace"), "parked");
  assert.equal(modeFor("/workspace#brain-bay"), "parked");
  assert.equal(modeFor("/"), "parked");
  const dock = read("components/lost-cosmos-dock.tsx");
  assert.match(dock, /modeFor/);
  assert.match(dock, /css\.full/);
  assert.match(dock, /data-cosmos-mode=\{mode\}/);
  assert.match(dock, /EJS_gameUrl = '\/api\/gba-rom'/);
  assert.match(dock, /id="lost-cosmos-screen"/);
  assert.match(read("components/lost-cosmos-dock.module.css"), /left:-240vw/);
});

test("Brain Bay, Model Bay, cosmos world, and owner settings are not edited for the field screen", () => {
  for (const path of [
    "components/studio.tsx",
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
