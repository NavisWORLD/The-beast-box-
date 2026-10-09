/**
 * Shared adventure rules. Movement, follow, and reactions are deterministic.
 * Spark traits, care needs, growth, and sensor readings decide the pose.
 */

import { isKidSafe, observeText } from "./learn.mjs";
import { careAction, finishTraining, grantXp, shownName, stageFromXp, talk } from "./session.mjs";

export const PLACES = [
  { id: "grove", name: "Eridoria Grove", x: 18, y: 62, nearby: ["fern", "glow moth", "still water"] },
  { id: "shore", name: "Pale Shore", x: 52, y: 76, nearby: ["tide pool", "shell", "soft wind"] },
  { id: "observatory", name: "Crown Observatory", x: 78, y: 34, nearby: ["lens", "star chart", "quiet dome"] },
  { id: "nest", name: "Nest Hollow", x: 34, y: 24, nearby: ["warm moss", "sleeping stones"] },
];

export function placeById(id) {
  return PLACES.find((place) => place.id === id) || PLACES[0];
}

export function createTrail(placeId = "grove") {
  const place = placeById(placeId);
  return {
    place: place.id,
    player: { x: place.x, y: place.y },
    beast: { x: place.x, y: Math.min(96, place.y + 8) },
    facing: "right",
    moving: false,
  };
}

export function goTo(trail, placeId) {
  const place = PLACES.find((item) => item.id === placeId);
  if (!place) throw new Error("unknown place");
  const facing = place.x < trail.player.x ? "left" : "right";
  return { ...trail, place: place.id, player: { x: place.x, y: place.y }, facing, moving: true };
}

export function followStep(trail) {
  const dx = trail.player.x - trail.beast.x;
  const dy = trail.player.y - trail.beast.y;
  const dist = Math.hypot(dx, dy);
  if (dist < 4) return { ...trail, moving: false };
  const step = Math.min(6, dist - 3);
  return {
    ...trail,
    moving: true,
    facing: dx < 0 ? "left" : "right",
    beast: {
      x: trail.beast.x + (dx / dist) * step,
      y: trail.beast.y + (dy / dist) * step,
    },
  };
}

export function needsOf(beast) {
  return {
    energy: beast?.energy ?? 100,
    bond: beast?.bond ?? 0,
    rest: (beast?.energy ?? 100) < 30,
    company: (beast?.bond ?? 0) < 12,
  };
}

function trait(genome, key, fallback) {
  const value = genome?.inputs?.traits?.[key];
  return Number.isFinite(value) ? value : fallback;
}

/**
 * Pose is one of idle, walk, follow, react, emote.
 * Emote names match the pixel stage: happy, sleep, evolve, listen, look, spark.
 */
export function reactionFor({ genome, beast, trail, sensors }) {
  const needs = needsOf(beast);
  const stage = beast?.stage || stageFromXp(beast?.xp || 0);
  const mood = beast?.mood || "idle";
  const spark = trait(genome, "spark", sensors?.signal?.spark ?? 20);
  const calm = trait(genome, "calm", sensors?.signal?.calm ?? 40);
  const focus = trait(genome, "focus", sensors?.signal?.focus ?? 40);
  if (mood === "evolve") return { pose: "emote", emote: "evolve", reason: "growth crossed a stage" };
  if (needs.rest || mood === "sleep") return { pose: "emote", emote: "sleep", reason: "energy is low" };
  if (sensors?.mic?.available && sensors.mic.onset) return { pose: "react", emote: "listen", reason: "heard a sound" };
  if (sensors?.camera?.available && sensors.camera.motion >= 0.18) return { pose: "react", emote: "look", reason: "saw motion" };
  if (sensors?.signal?.available && sensors.signal.mode === "muse" && sensors.signal.spark >= 60) {
    return { pose: "emote", emote: "spark", reason: "Muse spark is high" };
  }
  if (spark >= 70 && mood === "happy") return { pose: "emote", emote: "happy", reason: "spark trait is bright" };
  if (trail?.moving && Math.hypot(trail.player.x - trail.beast.x, trail.player.y - trail.beast.y) > 8) {
    return { pose: "follow", emote: calm >= 60 ? "soft" : "watch", reason: "following you" };
  }
  if (trail?.moving) return { pose: "walk", emote: "watch", reason: "walking" };
  if (needs.company) return { pose: "idle", emote: "watch", reason: "bond is still small" };
  if (focus >= 70) return { pose: "idle", emote: "watch", reason: "focus is high" };
  return { pose: "idle", emote: calm >= 60 ? "soft" : "watch", reason: "resting nearby" };
}

export function eyesFor(reaction) {
  if (reaction?.emote === "sleep") return "closed";
  if (reaction?.emote === "happy" || reaction?.emote === "spark" || reaction?.emote === "evolve") return "sparkle";
  return "open";
}

export function nameBeast(session, name) {
  if (!session.beast) return { ok: false, reason: "no beast" };
  const clean = String(name || "").replace(/[^\w .'-]/g, "").trim().slice(0, 24);
  if (!clean) return { ok: false, reason: "empty name" };
  session.beast.displayName = clean;
  const entry = session.bestiary.find((item) => item.seed === session.beast.seed);
  if (entry) entry.name = shownName(session.beast);
  return { ok: true, name: clean };
}

export function talkAndGrow(session, text) {
  const result = talk(session, text);
  if (!result.safe || !session.beast) return { ...result, xp: session.beast?.xp || 0, evolved: false };
  const growth = grantXp(session, 3, "talk");
  return { ...result, ...growth };
}

export function rememberExchange(session, userText, beastText, {learnReply=true}={}) {
  const you = String(userText || "").slice(0, 400);
  const beastLine = String(beastText || "").slice(0, 400);
  const safe = isKidSafe(you) && isKidSafe(beastLine);
  session.chat.push({ role: "you", text: you });
  if (safe) observeText(session.mind, you,{seed:session.beast?.seed||''});
  session.chat.push({ role: "beast", text: beastLine });
  if (safe && learnReply) observeText(session.mind, beastLine,{seed:session.beast?.seed||''});
  if (session.chat.length > 80) session.chat.splice(0, session.chat.length - 80);
  if (!session.beast || !safe) return { safe, xp: session.beast?.xp || 0, evolved: false, stage: session.beast?.stage || 1 };
  session.beast.bond = Math.min(100, (session.beast.bond || 0) + 1);
  return { safe, ...grantXp(session, 3, "talk") };
}

export function care(session, kind) {
  return careAction(session, kind);
}

export function train(session, hits, total = 6) {
  return finishTraining(session, hits, total);
}

export function topMemories(session, limit = 4) {
  const lines = [];
  for (const turn of session.chat || []) {
    const text = String(turn?.text || "").replace(/\s+/g, " ").trim();
    if (!text) continue;
    lines.push(`${turn.role === "you" ? "You" : shownName(session.beast)}: ${text}`.slice(0, 140));
  }
  const vocab = Object.entries(session.mind?.vocab || {})
    .sort((a, b) => (b[1]?.count || 0) - (a[1]?.count || 0))
    .slice(0, 3)
    .map(([word, row]) => `${word} ×${row.count}`);
  if (vocab.length) lines.push(`Words kept: ${vocab.join(", ")}`);
  return lines.slice(-limit);
}
