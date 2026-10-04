/**
 * Chat wander cycle for the Spark Beast. Idle, walk, emote, and react.
 * Positions are a function of the tick, so the path is stable without a random draw.
 */

export function wanderFrame(tick, reactionTicks, thinking, reduced) {
  const step = Math.max(0, Math.floor(Number(tick) || 0));
  const reaction = Math.max(0, Math.floor(Number(reactionTicks) || 0));
  if (reduced) {
    return {
      mode: reaction > 0 ? "react" : "idle",
      x: 0,
      y: 0,
      visual: thinking ? "thinking" : reaction > 0 ? "celebrating" : "idle",
    };
  }
  if (thinking) return { mode: "emote", x: 0, y: -4, visual: "thinking" };
  if (reaction > 0) {
    return {
      mode: reaction > 20 ? "emote" : "react",
      x: Math.round(Math.sin(step / 3) * 12),
      y: -6,
      visual: "celebrating",
    };
  }
  const cycle = step % 180;
  if (cycle >= 60 && cycle < 150) {
    return {
      mode: "walk",
      x: Math.round(((cycle - 60) / 90) * 128 - 64),
      y: cycle % 8 < 4 ? -2 : 0,
      visual: "observing",
    };
  }
  return {
    mode: "idle",
    x: Math.round(Math.sin(step / 10) * 6),
    y: Math.round(Math.sin(step / 8) * 3),
    visual: "idle",
  };
}
