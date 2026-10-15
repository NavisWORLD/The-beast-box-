/**
 * Pluggable creature voice. The browser voice works today; a Grok/xAI TTS
 * provider is a named slot that stays "not configured" until the owner adds a
 * backend key (GROK_TTS_API_KEY or XAI_API_KEY on Vercel). The key never reaches
 * the browser; this module only reads the public status route.
 */
export const VOICE_PROVIDERS = Object.freeze(["browser", "grok-tts"]);
export async function voiceStatus(fetchImpl = globalThis.fetch) {
  const browser = typeof globalThis.speechSynthesis !== "undefined";
  let grok = { configured: false, reason: "Grok voice is not set up yet. Add a backend key to enable it." };
  try {
    const r = await fetchImpl("/api/voice", { cache: "no-store" });
    const j = r.ok ? await r.json() : null;
    if (j && j.schema === "beastbox-voice-v1") grok = { configured: j.grok === true, reason: j.grok ? "Grok voice key is configured on the backend." : grok.reason };
  } catch {}
  return { browser, grok, default: "browser" };
}
export function speakWith(provider, text, { name = "Beast" } = {}) {
  const line = String(text || "").slice(0, 400);
  if (!line) return { ok: false, error: "Nothing to say." };
  if (provider === "grok-tts") return { ok: false, error: "Grok voice is not connected yet; using the browser voice is available instead." };
  if (typeof globalThis.speechSynthesis === "undefined") return { ok: false, error: "This browser has no speech voice." };
  const u = new SpeechSynthesisUtterance(line);
  u.rate = 1; u.pitch = 1.15;
  globalThis.speechSynthesis.cancel(); globalThis.speechSynthesis.speak(u);
  return { ok: true, provider: "browser", label: `${name} · browser voice (device TTS, not a model voice)` };
}
