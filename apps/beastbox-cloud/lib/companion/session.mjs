/**
 * Play session that survives tab switches. The beast, chat, training score,
 * and emulator heartbeat live on this object. Views only read it.
 */

import { createMind, importMind, isKidSafe, observeText, replyFromMind } from "./learn.mjs";

export const TABS = ["play", "cage", "train", "talk", "bestiary", "gba", "lab"];
export const STAGE_XP = [0, 40, 120];

export function stageFromXp(xp) {
  const value = Math.max(0, Math.floor(Number(xp) || 0));
  if (value >= 120) return 3;
  if (value >= 40) return 2;
  return 1;
}

export function nextGoal(xp) {
  const stage = stageFromXp(xp);
  if (stage >= 3) return null;
  return STAGE_XP[stage];
}

export function createSession() {
  return {
    tab: "play",
    beast: null,
    bestiary: [],
    chat: [],
    mind: createMind(),
    emulator: { mounted: true, ticks: 0, booted: false },
    train: { score: 0, rounds: 0 },
    mood: "idle",
  };
}

export function switchTab(session, tab) {
  if (!TABS.includes(tab)) throw new Error("unknown tab");
  session.tab = tab;
  return session;
}

export function tickEmulator(session) {
  session.emulator.ticks += 1;
  return session.emulator.ticks;
}

export function shownName(beast) {
  if (!beast) return "Beast";
  return beast.displayName || beast.genome?.names?.[String(beast.stage)] || beast.genome?.names?.[beast.stage] || "Beast";
}

export function adoptBeast(session, genome, displayName = "") {
  const beast = {
    seed: genome.seed,
    genome,
    displayName: String(displayName || "").slice(0, 24),
    xp: 0,
    bond: 1,
    energy: 100,
    stage: 1,
    mood: "idle",
  };
  session.beast = beast;
  if (!session.bestiary.some((item) => item.seed === genome.seed)) {
    session.bestiary.push({ seed: genome.seed, name: shownName(beast), island: genome.island, body: genome.body, genome });
  }
  session.mood = "happy";
  return beast;
}

export function grantXp(session, amount, reason) {
  const beast = session.beast;
  if (!beast) return { ok: false, reason: "no beast" };
  const before = beast.stage;
  const gain = Math.max(0, Math.min(40, Math.floor(amount)));
  beast.xp += gain;
  beast.energy = Math.max(0, Math.min(100, beast.energy - (reason === "rest" ? -12 : 4)));
  if (reason === "rest") beast.energy = Math.min(100, beast.energy + 16);
  beast.stage = stageFromXp(beast.xp);
  beast.mood = beast.stage > before ? "evolve" : reason === "rest" ? "sleep" : "happy";
  session.mood = beast.mood;
  const entry = session.bestiary.find((item) => item.seed === beast.seed);
  if (entry) entry.name = shownName(beast);
  return { ok: true, gain, xp: beast.xp, stage: beast.stage, evolved: beast.stage > before, from: before };
}

export function careAction(session, kind) {
  const table = { pet: 4, feed: 6, rest: 2, spark: 3 };
  if (!(kind in table)) throw new Error("unknown care");
  if (session.beast) session.beast.bond = Math.min(100, (session.beast.bond || 0) + (kind === "pet" ? 2 : 1));
  return grantXp(session, table[kind], kind);
}

export function finishTraining(session, hits, total = 6) {
  const score = Math.max(0, Math.min(total, Math.floor(hits)));
  session.train.rounds += 1;
  session.train.score += score;
  const result = grantXp(session, 2 + score * 3, "train");
  return { ...result, score, total };
}

export function talk(session, text) {
  const name = shownName(session.beast);
  const safe = isKidSafe(text);
  session.chat.push({ role: "you", text: String(text || "").slice(0, 400) });
  if (safe) observeText(session.mind, text);
  const reply = replyFromMind(session.mind, text, name);
  if (safe) observeText(session.mind, reply);
  session.chat.push({ role: "beast", text: reply });
  if (session.chat.length > 80) session.chat.splice(0, session.chat.length - 80);
  if (session.beast && safe) {
    session.beast.bond = Math.min(100, session.beast.bond + 1);
    session.beast.mood = "happy";
    session.mood = "happy";
  }
  return { reply, steps: session.mind.steps, safe };
}

export function exportSession(session) {
  return {
    schema: "beastbox-companion-session-v1",
    tab: session.tab,
    beast: session.beast,
    bestiary: session.bestiary,
    chat: session.chat,
    mind: session.mind,
    emulator: { mounted: true, ticks: session.emulator.ticks, booted: !!session.emulator.booted },
    train: session.train,
    mood: session.mood,
    pet: session.pet || null,
  };
}

export function importSession(raw) {
  const session = createSession();
  if (!raw || raw.schema !== "beastbox-companion-session-v1") return session;
  if (TABS.includes(raw.tab)) session.tab = raw.tab;
  session.beast = raw.beast || null;
  session.bestiary = Array.isArray(raw.bestiary) ? raw.bestiary : [];
  session.chat = Array.isArray(raw.chat) ? raw.chat.slice(-80) : [];
  session.mind = importMind(raw.mind);
  session.emulator.ticks = Number(raw.emulator?.ticks) || 0;
  session.emulator.booted = !!raw.emulator?.booted;
  session.train = {
    score: Number(raw.train?.score) || 0,
    rounds: Number(raw.train?.rounds) || 0,
  };
  session.mood = raw.mood || "idle";
  session.pet = raw.pet && raw.pet.modelWeightsTrained === false ? raw.pet : null;
  return session;
}
