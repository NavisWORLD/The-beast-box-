/**
 * Play session that survives tab switches. The beast, chat, training score,
 * and emulator heartbeat live on this object. Views only read it.
 */

import { createMind, importMind, isKidSafe, observeText, replyFromMind } from "./learn.mjs";
import {recordCreatureExperience as recordBehaviorFeedback,validateBehavior} from "./behavior.mjs";

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

export function progressFromLocalGrowth(beast) {
  const growth = beast?.localGrowth || {};
  const stage = Math.floor(Number(growth.stage ?? beast?.stage) || 1);
  return {
    trust: 0,
    bond: Math.max(0, Math.min(100, Math.floor(Number(growth.bond ?? beast?.bond) || 0))),
    evolution_stage: Math.max(0, Math.min(2, stage - 1)),
  };
}

export function beastIdentity(beast) {
  if (!beast) return null;
  return beast.qbeast?.profile?.id || beast.id || (beast.seed ? `seed:${beast.seed}` : null);
}

function mirrorGrowth(session) {
  const beast = session.beast;
  if (!beast) return null;
  const prior = beast.localGrowth && typeof beast.localGrowth === "object" ? beast.localGrowth : {};
  beast.localGrowth = {
    schema: "qbeast-local-growth-v1",
    status: "unsigned-local",
    signature: "none",
    qbeast_id: beastIdentity(beast),
    seed: beast.seed,
    xp: beast.xp,
    bond: beast.bond,
    energy: beast.energy,
    stage: beast.stage,
    mood: beast.mood,
    train: { score: session.train?.score || 0, rounds: session.train?.rounds || 0 },
    memory_steps: session.mind?.steps || 0,
    game: prior.game || beast.game || {},
    applied: Array.isArray(prior.applied) ? prior.applied : [],
    model: prior.model || null,
    note: "Pending local growth. Not a signed QBEAST progress update.",
  };
  if (beast.qbeast) beast.qbeastProgress = "pending-unsigned";
  return beast.localGrowth;
}

export function swapBrain(session, provider) {
  if (!session.beast) return { ok: false, reason: "no beast" };
  const id = beastIdentity(session.beast);
  const xp = session.beast.xp;
  const bond = session.beast.bond;
  const steps = session.mind?.steps || 0;
  mirrorGrowth(session);
  session.beast.localGrowth.model = { provider: String(provider || "unset").slice(0, 64), swapped: true };
  if (beastIdentity(session.beast) !== id || session.beast.xp !== xp || session.beast.bond !== bond || (session.mind?.steps || 0) !== steps) {
    throw new Error("brain swap changed creature state");
  }
  return { ok: true, qbeast_id: id, xp, bond, memory_steps: steps, model: session.beast.localGrowth.model.provider };
}

const GAME_FIELDS = ["game_xp", "game_level", "game_stage", "discovered", "inventory", "beacons", "echoes", "flags", "native_save"];

export function applyGameReturn(session, payload) {
  if (!session.beast) return { ok: false, reason: "no beast" };
  if (!payload || payload.schema !== "lost-cosmos-return-v1") return { ok: false, reason: "schema" };
  const id = beastIdentity(session.beast);
  if (payload.qbeast_id !== id) return { ok: false, reason: "identity" };
  const eventId = String(payload.event_id || "");
  if (!eventId || eventId.length > 80) return { ok: false, reason: "event" };
  mirrorGrowth(session);
  if (session.beast.localGrowth.applied.includes(eventId)) return { ok: true, duplicate: true, qbeast_id: id };
  const game = { ...session.beast.localGrowth.game };
  for (const key of GAME_FIELDS) {
    if (payload[key] !== undefined) game[key] = payload[key];
  }
  session.beast.game = game;
  session.beast.localGrowth.game = game;
  session.beast.localGrowth.applied = [...session.beast.localGrowth.applied, eventId].slice(-64);
  return { ok: true, duplicate: false, qbeast_id: id, game };
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
  mirrorGrowth(session);
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
  beast.stage = beast.qbeast ? Math.max(1, Math.min(3, beast.nativeStage || 1)) : stageFromXp(beast.xp);
  beast.mood = beast.stage > before ? "evolve" : reason === "rest" ? "sleep" : "happy";
  session.mood = beast.mood;
  const entry = session.bestiary.find((item) => item.seed === beast.seed);
  if (entry) entry.name = shownName(beast);
  mirrorGrowth(session);
  return { ok: true, gain, xp: beast.xp, stage: beast.stage, evolved: beast.stage > before, from: before, qbeast_id: beastIdentity(beast) };
}

export function careAction(session, kind) {
  const table = { pet: 4, feed: 6, rest: 2, spark: 3 };
  if (!(kind in table)) throw new Error("unknown care");
  if (session.beast) session.beast.bond = Math.min(100, (session.beast.bond || 0) + (kind === "pet" ? 2 : 1));
  const result = grantXp(session, table[kind], kind);
  // Real care is a bounded feedback event, not quantum evidence or model learning.
  if (/^[0-9a-f]{16,128}$/i.test(session.beast?.seed || "")) {
    recordBehaviorFeedback(session, {kind: "care:" + kind, place: session.beast.behavior?.events?.at(-1)?.place || "grove", reward: kind === "rest" ? .4 : 1});
  }
  return result;
}

export function finishTraining(session, hits, total = 6) {
  const score = Math.max(0, Math.min(total, Math.floor(hits)));
  session.train.rounds += 1;
  session.train.score += score;
  const result = grantXp(session, 2 + score * 3, "train");
  if(/^[0-9a-f]{16,128}$/i.test(session.beast?.seed||''))recordBehaviorFeedback(session,{kind:'training',place:session.beast.behavior?.events?.at(-1)?.place||'grove',reward:score/Math.max(1,total)});
  return { ...result, score, total };
}

export function talk(session, text) {
  const name = shownName(session.beast);
  const safe = isKidSafe(text);
  session.chat.push({ role: "you", text: String(text || "").slice(0, 400) });
  // Local Hebbian pattern update. Not inference-model training and not QBEAST identity.
  const reply = replyFromMind(session.mind, text, name);
  // Read prior experience before learning the current turn. Authored pattern prose
  // is not an external experience and must not recursively train itself.
  if (safe) observeText(session.mind, text,{seed:session.beast?.seed||''});
  session.chat.push({ role: "beast", text: reply });
  if (session.chat.length > 80) session.chat.splice(0, session.chat.length - 80);
  if (session.beast && safe) {
    session.beast.bond = Math.min(100, session.beast.bond + 1);
    session.beast.mood = "happy";
    session.mood = "happy";
    mirrorGrowth(session);
  }
  return { reply, steps: session.mind.steps, safe, qbeast_id: beastIdentity(session.beast) };
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
  session.beast = raw.beast ? structuredClone(raw.beast) : null;
  session.bestiary = Array.isArray(raw.bestiary) ? structuredClone(raw.bestiary) : [];
  session.chat = Array.isArray(raw.chat) ? structuredClone(raw.chat.slice(-80)) : [];
  session.mind = importMind(raw.mind);
  session.emulator.ticks = Number(raw.emulator?.ticks) || 0;
  session.emulator.booted = !!raw.emulator?.booted;
  session.train = {
    score: Number(raw.train?.score) || 0,
    rounds: Number(raw.train?.rounds) || 0,
  };
  session.mood = raw.mood || "idle";
  session.pet = raw.pet && raw.pet.modelWeightsTrained === false ? raw.pet : null;
  if (session.beast) {
    if(session.beast.behavior)session.beast.behavior=structuredClone(validateBehavior(session.beast.behavior,session.beast));
    mirrorGrowth(session);
  }
  return session;
}

// Non-authoritative deterministic behavior: no native progress or XP rewards.
export {advanceCreature,recordCreatureExperience} from './behavior.mjs';
