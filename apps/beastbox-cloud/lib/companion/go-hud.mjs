/**
 * Field HUD rules. The cartridge is the world; these only describe the overlay.
 */

import { shownName, STAGE_XP, nextGoal, stageFromXp } from "./session.mjs";

export const QUICK = [
  { id: "bag", label: "Bag" },
  { id: "beasts", label: "Beasts" },
  { id: "talk", label: "Talk" },
  { id: "map", label: "Map" },
  { id: "settings", label: "Settings" },
];

/** @type {{ id: string, label: string, kind: "feed" | "pet" | "rest" | "spark" }[]} */
export const BAG = [
  { id: "feed", label: "Feed", kind: "feed" },
  { id: "pet", label: "Pet", kind: "pet" },
  { id: "rest", label: "Rest", kind: "rest" },
  { id: "spark", label: "Spark", kind: "spark" },
];

/** EmulatorJS GBA defaults: Z is A, X is B, arrows, Enter start, V select, Q/E shoulders. */
export const GBA_KEYS = {
  up: { key: "ArrowUp", code: "ArrowUp", index: 4, label: "Up" },
  down: { key: "ArrowDown", code: "ArrowDown", index: 5, label: "Down" },
  left: { key: "ArrowLeft", code: "ArrowLeft", index: 6, label: "Left" },
  right: { key: "ArrowRight", code: "ArrowRight", index: 7, label: "Right" },
  a: { key: "z", code: "KeyZ", index: 8, label: "A" },
  b: { key: "x", code: "KeyX", index: 0, label: "B" },
  start: { key: "Enter", code: "Enter", index: 3, label: "Start" },
  select: { key: "v", code: "KeyV", index: 2, label: "Select" },
  l: { key: "q", code: "KeyQ", index: 10, label: "L" },
  r: { key: "e", code: "KeyE", index: 11, label: "R" },
};

export const STANDARD_GAMEPAD_BUTTONS = {
  0: "a", 1: "b",
  4: "l", 5: "r", 6: "l", 7: "r",
  8: "select", 9: "start",
  12: "up", 13: "down", 14: "left", 15: "right",
};

export function gamepadButtons(gamepad, deadzone = 0.55) {
  const active = new Set();
  const buttons = gamepad?.buttons || [];
  for (const [index, logical] of Object.entries(STANDARD_GAMEPAD_BUTTONS)) {
    const button = buttons[Number(index)];
    if (button && (button.pressed === true || Number(button.value) > 0.5)) active.add(logical);
  }
  const x = Number(gamepad?.axes?.[0]);
  const y = Number(gamepad?.axes?.[1]);
  if (Number.isFinite(x)) {
    if (x <= -deadzone) active.add("left");
    if (x >= deadzone) active.add("right");
  }
  if (Number.isFinite(y)) {
    if (y <= -deadzone) active.add("up");
    if (y >= deadzone) active.add("down");
  }
  return [...active];
}

export function keyboardLegend() {
  return [
    ["Arrows", "Move"],
    ["Z", "A"],
    ["X", "B"],
    ["Enter", "Start"],
    ["V", "Select"],
    ["Q / E", "L / R"],
    ["Gamepad", "D-pad / sticks · A / B · Start / Select · L / R"],
    ["Escape", "Close a sheet"],
  ];
}

export function sparkVisualState(mood) {
  if (mood === "sleep") return "sleeping";
  if (mood === "evolve" || mood === "happy") return "celebrating";
  return "idle";
}

export function hudCard(beast) {
  const xp = Math.max(0, Math.floor(Number(beast?.xp) || 0));
  const stage = stageFromXp(xp);
  const goal = nextGoal(xp);
  const floor = STAGE_XP[stage - 1] || 0;
  const ratio = goal == null ? 1 : (xp - floor) / Math.max(1, goal - floor);
  return {
    name: beast ? shownName(beast) : "No beast yet",
    stage,
    xp,
    mood: beast?.mood || "idle",
    goal,
    ratio: Math.max(0, Math.min(1, ratio)),
    ready: !!beast,
  };
}

export function sheetGesture(startY, endY, open) {
  const dy = Number(endY) - Number(startY);
  if (!Number.isFinite(dy)) return "stay";
  if (dy <= -48) return "open";
  if (open && dy >= 48) return "close";
  return "stay";
}

export function focusBeast(session, seed) {
  if (!session?.bestiary) return { ok: false, reason: "no party" };
  const current = session.beast;
  if (current) {
    const row = session.bestiary.find((item) => item.seed === current.seed);
    if (row) {
      row.xp = current.xp;
      row.bond = current.bond;
      row.energy = current.energy;
      row.stage = current.stage;
      row.mood = current.mood;
      row.name = shownName(current);
    }
  }
  const next = session.bestiary.find((item) => item.seed === seed);
  if (!next?.genome) return { ok: false, reason: "missing genome" };
  session.beast = {
    seed: next.seed,
    genome: next.genome,
    displayName: next.name || "",
    xp: Number(next.xp) || 0,
    bond: Number(next.bond) || 1,
    energy: Number.isFinite(next.energy) ? next.energy : 100,
    stage: next.stage || stageFromXp(next.xp || 0),
    mood: next.mood || "idle",
  };
  return { ok: true, name: shownName(session.beast) };
}

function keyEvent(type, spec) {
  const init = { key: spec.key, code: spec.code, bubbles: true, cancelable: true };
  if (typeof KeyboardEvent === "function") return new KeyboardEvent(type, init);
  const event = new Event(type, init);
  event.key = spec.key;
  event.code = spec.code;
  return event;
}

export function pressCartridge(button, down, host) {
  const spec = GBA_KEYS[button];
  if (!spec || !host) return false;
  const sim = host.EJS_emulator?.gameManager?.simulateInput;
  if (typeof sim === "function") sim(0, spec.index, down ? 1 : 0);
  if (typeof host.dispatchEvent === "function") host.dispatchEvent(keyEvent(down ? "keydown" : "keyup", spec));
  return true;
}
