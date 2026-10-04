/** Text context for a real model. This file does not call a model or invent a reply. */

import { placeById, topMemories } from "./adventure.mjs";
import { sensorSummary } from "./sensors.mjs";
import { shownName, stageFromXp } from "./session.mjs";

export function buildChatContext(input) {
  const session = input.session;
  const trail = input.trail;
  const sensors = input.sensors;
  const sensorLog = Array.isArray(input.sensorLog) ? input.sensorLog : [];
  const place = placeById(trail?.place);
  const beast = session?.beast;
  const recent = [...sensorLog].slice(-4);
  if (sensors) recent.push(sensorSummary(sensors));
  return {
    name: shownName(beast),
    location: place.name,
    nearby: place.nearby.slice(),
    mood: beast?.mood || "idle",
    level: beast?.stage || stageFromXp(beast?.xp || 0),
    xp: beast?.xp || 0,
    bond: beast?.bond || 0,
    energy: beast?.energy ?? 100,
    memories: topMemories(session || { chat: [], mind: {}, beast }, 4),
    sensors: recent.filter(Boolean).slice(-4),
  };
}

export function renderContextPrompt(context, userText, limit = 700) {
  const nearby = (context.nearby || []).join(", ") || "nothing listed";
  const memories = (context.memories || []).join(" | ") || "No stored memories yet.";
  const sensors = (context.sensors || []).join(" | ") || "Sensors are off.";
  const lines = [
    `Game companion ${context.name} is in ${context.location}. Nearby: ${nearby}.`,
    `Mood ${context.mood}. Stage ${context.level}. XP ${context.xp}. Bond ${context.bond}. Energy ${context.energy}.`,
    `Memories: ${memories}`,
    `Recent sensors: ${sensors}`,
    "Reply in one or two short sentences as this companion. Mention only sensors that are listed as on.",
    `Keeper says: ${String(userText || "").trim()}`,
  ];
  let text = lines.join("\n");
  if (text.length > limit) text = text.slice(0, limit);
  return text;
}
