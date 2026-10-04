/**
 * Pet dragon motion and growth claims.
 * The recorded quantum seed only phases the animation.
 * On-device Hebbian weights can grow from verified text.
 * A selected Brain Bay model is named, not trained.
 */

import { observeText } from "./learn.mjs";

export const DRAGON_TRAITS = { focus: 0, calm: 0, spark: 0 };
export const DRAGON_RUN_KEY = "ibm_marrakesh:d93d8pgoamcc73dc3afg";

export function petPose(tick, signal = {}, reduced = false) {
  const step = Math.max(0, Math.floor(Number(tick) || 0));
  const seed = Math.abs(Math.floor(Number(signal.seed) || 1));
  const tokens = Math.max(0, Math.floor(Number(signal.tokens) || 0));
  const sensor = Math.max(0, Math.min(1, Number(signal.sensor) || 0));
  const chat = signal.chat === true;
  const live = chat || tokens > 0 || sensor > 0;
  const phase = step + (seed % 97);
  let claim = "quantum-seed";
  if (signal.learned === true) claim = "on-device-weights";
  else if (live) claim = "live-signal";
  if (reduced) {
    return { x: 0, y: 0, mode: "idle", visual: chat ? "thinking" : "idle", claim, looping: true };
  }
  const bob = Math.round(Math.sin((phase + tokens) / 9) * 6);
  if (chat) return { x: bob, y: -4, mode: "emote", visual: "thinking", claim, looping: true };
  if (sensor > 0.15) return { x: bob, y: 0, mode: "react", visual: "listening", claim, looping: true };
  if (tokens > 0 && phase % 80 < 18) return { x: bob, y: -6, mode: "emote", visual: "celebrating", claim, looping: true };
  if (phase % 100 < 34) return { x: Math.round(Math.sin(phase / 12) * 5), y: bob, mode: "idle", visual: "idle", claim, looping: true };
  return { x: Math.round(Math.sin(phase / 7) * 8), y: Math.round(Math.cos(phase / 11) * 4), mode: "walk", visual: "observing", claim, looping: true };
}

export function petClaim(pose) {
  if (pose?.claim === "on-device-weights") {
    return "On-device Hebbian weights grew from verified text. The selected Brain Bay model weights were not trained.";
  }
  if (pose?.claim === "live-signal") {
    return "Motion follows a live chat or sensor flag plus the recorded quantum seed. Model activation tensors are not read.";
  }
  return "Motion is seeded by the recorded quantum seed. No live model signal is connected.";
}

export function noteModelActivity(session, text, model) {
  if (!session?.mind) return { learned: false, source: "no-session", modelWeightsTrained: false };
  const learned = observeText(session.mind, text);
  session.pet = {
    model: String(model || session.pet?.model || ""),
    steps: session.mind.steps,
    learned: learned.learned === true,
    source: learned.learned ? "on-device-hebbian" : "no-growth",
    modelWeightsTrained: false,
  };
  return session.pet;
}
