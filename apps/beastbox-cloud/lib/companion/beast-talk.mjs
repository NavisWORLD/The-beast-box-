/**
 * Talk to Beast: one shared, honest chat client for every public talk surface.
 *
 * The Beast (name, personality, memories) is the identity. The model is only
 * the voice it borrows for one reply. Every reply returned here came from a
 * successful, verified model request; failures return `ok:false` with plain
 * help text. Nothing in this file writes a canned or invented reply.
 */
import { Stream } from "../../public/spark/engine.mjs";
import { beastIdentity, shownName } from "./session.mjs";
import { interpretModelResult } from "./brain.mjs";

export const TALK_ROUTES = Object.freeze(["guest-rawrphos", "local-ollama", "hf-byok"]);
export const DEFAULT_ROUTE = "guest-rawrphos";
export const DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434";
export const DEFAULT_OLLAMA_MODEL = "companion-glacecoil";
export const DEFAULT_HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct";
export const MAX_MESSAGE = 400;
const GUEST_LIMIT = 700;
const MODEL_TAG = /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,79}$/;
const HF_MODEL = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?$/;
const CATCHPHRASES = ["oh crumbs", "tiny beep", "hehe", "psst", "star crumb", "wiggle"];
const HABITS = ["rhymes one word", "adds a little squeak", "asks a tiny question back", "counts on its paws"];

export const ROUTE_INFO = Object.freeze({
  "guest-rawrphos": {
    label: "RAWRPHØS guest",
    model: "rawrphos-native · 14K checkpoint",
    detail: "Free Beast Box host. Small native model, stateless, daily quota.",
  },
  "local-ollama": {
    label: "My local Ollama",
    model: DEFAULT_OLLAMA_MODEL,
    detail: "A model running on your own computer (e.g. companion-glacecoil).",
  },
  "hf-byok": {
    label: "My Hugging Face key",
    model: DEFAULT_HF_MODEL,
    detail: "Your own token; any usage is billed to your Hugging Face account.",
  },
});

const ZEREF = Object.freeze({
  key: "zeref:bb-7f9c2a03",
  name: "Zeref",
  kind: "Moonwraith, a cosmic black moon cat dragon",
  traits: ["playful", "curious", "affectionate", "a little mischievous"],
  catchphrase: "*soft moon-purr*",
  habit: "purrs when happy",
  source: "zeref",
});

function clean(value, max) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, max);
}

function cageTraits(temperament) {
  const words = { curiosity: "curious", energy: "energetic", playfulness: "playful", caution: "careful", independence: "independent" };
  return Object.entries(temperament || {})
    .filter(([key, value]) => words[key] && Number.isFinite(value))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([key]) => words[key]);
}

/**
 * Build the identity frame for whichever Beast this visitor actually has:
 * their saved Spark Beast first, then their Beast Cage creature, then Zeref.
 */
export function talkPersona({ beast = null, cage = null } = {}) {
  const genome = beast?.genome;
  if (beast && genome) {
    const seed = String(genome.seed || beast.seed || beastIdentity(beast) || "beast");
    const voice = new Stream(seed, "companion-voice");
    const temperament = clean(genome.temperament, 24).toLowerCase();
    return {
      key: "spark:" + (beastIdentity(beast) || seed.slice(0, 24)),
      name: clean(shownName(beast), 40) || "Beast",
      kind: clean(`a ${[genome.element, genome.body].filter(Boolean).join(" ")} from ${genome.island || "the Lost Cosmos"}`, 90),
      traits: [temperament || "gentle", "loyal", "curious"].filter((v, i, a) => a.indexOf(v) === i),
      catchphrase: voice.pick(CATCHPHRASES),
      habit: voice.pick(HABITS),
      source: "spark",
    };
  }
  if (cage && typeof cage === "object" && typeof cage.name === "string") {
    const traits = cageTraits(cage.temperament);
    return {
      key: "cage:" + clean(cage.id || cage.seed, 40),
      name: clean(cage.name, 40) || "Beast",
      kind: `a ${clean(cage.family, 20) || "cosmic"} creature from the Beast Cage`,
      traits: traits.length ? traits : ["curious"],
      catchphrase: "hehe",
      habit: "hums while it explores",
      source: "cage",
    };
  }
  return { ...ZEREF, traits: ZEREF.traits.slice() };
}

/** Identity text: who is speaking. The model is only asked to voice it. */
export function personaFrame(persona) {
  const p = persona || ZEREF;
  return [
    `You are ${p.name}, ${p.kind}, the keeper's Beast Box companion.`,
    `Personality: ${p.traits.join(", ")}. It ${p.habit} and sometimes says "${p.catchphrase}".`,
    "You are a small game companion, not a person. Reply in one or two short, kind sentences as " + p.name + ".",
  ].join(" ");
}

/** Single bounded prompt for text-only routes (guest host, HF). The keeper's words always survive. */
export function framePrompt(persona, history, text, limit = GUEST_LIMIT) {
  const p = persona || ZEREF;
  const said = clean(text, MAX_MESSAGE);
  const tail = `\nKeeper: ${said}\n${p.name}:`;
  let head = personaFrame(p);
  const recent = (Array.isArray(history) ? history : []).slice(-2)
    .map((turn) => (turn.role === "you" ? "Keeper: " : p.name + ": ") + clean(turn.text, 110));
  let body = recent.length ? "\n" + recent.join("\n") : "";
  if (head.length + body.length + tail.length > limit) body = "";
  if (head.length + tail.length > limit) head = head.slice(0, Math.max(0, limit - tail.length));
  return (head + body + tail).slice(0, limit);
}

export function validOllamaUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) &&
      !url.username && !url.password && !url.search && !url.hash && (url.pathname === "/" || url.pathname === "");
  } catch {
    return false;
  }
}

/** Plain-language steps for connecting a working brain. Shown with every offline state. */
export function connectHelp(route) {
  const origin = typeof location !== "undefined" ? location.origin : "https://www.beastboxcosmos.xyz";
  const common = [
    "Your Beast, its name and its memories stay the same whichever brain you pick.",
  ];
  if (route === "local-ollama") return [
    "Install Ollama from ollama.com and pull a model, e.g. `ollama pull qwen2.5:0.5b` (or create companion-glacecoil from the Beast Box Modelfile).",
    `Start it so this site may call it: OLLAMA_ORIGINS=${origin} ollama serve`,
    "Use Chrome, Edge or Firefox on that same computer and allow local-network access if asked. iPhone Safari cannot reach a computer's Ollama.",
    ...common,
  ];
  if (route === "hf-byok") return [
    "Create a free token at huggingface.co/settings/tokens (\"Make calls to Inference Providers\").",
    "Paste it here and confirm charges. The key goes only to Hugging Face for this one request and is not saved on Beast Box servers.",
    ...common,
  ];
  return [
    "The free RAWRPHØS guest brain has a small daily quota per visitor and may be busy or switched off.",
    "Try again later, or pick My local Ollama or My Hugging Face key above to use your own model.",
    ...common,
  ];
}

function failure(route, error, status = 0) {
  return { ok: false, route, status, error: clean(error, 220) || "The model did not answer.", help: connectHelp(route) };
}

function fetchFailed(error) {
  return error instanceof TypeError || /failed to fetch|load failed|networkerror|network request failed/i.test(String(error?.message || ""));
}

async function readJson(response, max = 64000) {
  const raw = await response.text();
  if (raw.length > max) throw new Error("Response too large");
  try { return JSON.parse(raw); } catch { throw new Error("The model sent an unreadable response"); }
}

/**
 * Send one message to the chosen brain.
 * @param {{route?:string,persona?:any,history?:any[],text:string,fetchImpl?:typeof fetch,signal?:AbortSignal,
 *   ollama?:{url?:string,model?:string},hf?:{key?:string,model?:string,spendConfirmed?:boolean}}} input
 */
export async function talkToBeast(input) {
  const route = TALK_ROUTES.includes(input?.route) ? input.route : DEFAULT_ROUTE;
  const persona = input?.persona || ZEREF;
  const text = clean(input?.text, MAX_MESSAGE);
  const fetchImpl = input?.fetchImpl || globalThis.fetch;
  const signal = input?.signal;
  const history = Array.isArray(input?.history) ? input.history : [];
  if (!text) return failure(route, "Type a message first.");
  try {
    if (route === "local-ollama") {
      const base = String(input?.ollama?.url || DEFAULT_OLLAMA_URL).replace(/\/+$/, "");
      const model = String(input?.ollama?.model || DEFAULT_OLLAMA_MODEL).trim();
      if (!validOllamaUrl(base)) return failure(route, "Local Ollama must be on this computer (http://127.0.0.1:11434 or http://localhost:11434).");
      if (!MODEL_TAG.test(model) || model.includes("://")) return failure(route, "Enter the tag of a model you installed in Ollama, e.g. qwen2.5:0.5b.");
      const messages = [{ role: "system", content: personaFrame(persona) }];
      for (const turn of history.slice(-6)) messages.push({ role: turn.role === "you" ? "user" : "assistant", content: clean(turn.text, 400) });
      messages.push({ role: "user", content: text });
      const response = await fetchImpl(base + "/api/chat", {
        method: "POST", mode: "cors", credentials: "omit", redirect: "error", signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, stream: false, messages, options: { num_predict: 160, temperature: 0.6 } }),
      });
      const payload = await readJson(response).catch(() => null);
      if (!response.ok) {
        const reason = typeof payload?.error === "string" ? payload.error : "";
        return failure(route, response.status === 404 || /not found/i.test(reason)
          ? `Ollama is running but the model "${model}" is not installed. Run: ollama pull ${model}`
          : `Ollama answered with an error (${response.status}). ${clean(reason, 120)}`, response.status);
      }
      const reply = typeof payload?.message?.content === "string" ? payload.message.content.trim() : "";
      if (payload?.done !== true || !reply || reply.length > 6000) return failure(route, "Ollama sent no usable reply.");
      return { ok: true, route, reply, model: clean(payload.model || model, 80), label: ROUTE_INFO[route].label, at: Date.now() };
    }
    if (route === "hf-byok") {
      const key = String(input?.hf?.key || "").trim();
      const model = String(input?.hf?.model || DEFAULT_HF_MODEL).trim();
      if (!/^[A-Za-z0-9_-]{20,300}$/.test(key)) return failure(route, "Paste your personal Hugging Face token (it starts with hf_).");
      if (!HF_MODEL.test(model) || model.length > 150) return failure(route, "Enter a Hugging Face model ID like owner/model-name.");
      if (input?.hf?.spendConfirmed !== true) return failure(route, "Confirm that any charges go to your own Hugging Face account.");
      const response = await fetchImpl("/api/guest", {
        method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error", signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: "huggingface-byok", text: framePrompt(persona, history, text), hf_key: key, model, spend_confirmed: true }),
      });
      const payload = await readJson(response).catch(() => null);
      if (!response.ok) return failure(route, typeof payload?.error === "string" ? payload.error : `Hugging Face request failed (${response.status}).`, response.status);
      const reply = typeof payload?.reply === "string" ? payload.reply.trim() : "";
      if (payload?.provider !== "huggingface-byok" || !reply || reply.length > 6000) return failure(route, "Hugging Face sent no verified reply.");
      return { ok: true, route, reply, model: clean(payload.model || model, 150), label: ROUTE_INFO[route].label, at: Date.now() };
    }
    const response = await fetchImpl("/api/guest", {
      method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error", signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: "rawrphos-local", text: framePrompt(persona, history, text) }),
    });
    const payload = await readJson(response).catch(() => null);
    if (!response.ok) {
      const reason = typeof payload?.error === "string" ? payload.error : "";
      const status = response.status;
      const message = status === 429 ? `The free guest brain is resting: ${reason || "usage limit reached"}.`
        : status === 403 && /trial/i.test(reason) ? "The free guest brain's trial period has ended."
          : status === 503 ? `The free guest brain is offline right now (${reason || "host unavailable"}).`
            : reason || `The guest brain did not answer (${status}).`;
      return failure(route, message, status);
    }
    const read = interpretModelResult("guest-rawrphos", payload);
    if (!read.ok || !read.reply || read.reply.length > 6000) return failure(route, read.reason || "The guest brain sent no verified reply.");
    return { ok: true, route, reply: read.reply, model: "rawrphos-native · 14K", label: ROUTE_INFO[route].label, at: Date.now() };
  } catch (error) {
    if (signal?.aborted) return failure(route, "The request was cancelled or timed out. No reply was received.");
    if (fetchFailed(error)) {
      return failure(route, route === "local-ollama"
        ? "Couldn't reach Ollama on this computer. It may not be running, or it hasn't allowed this website yet (see steps below)."
        : "Couldn't reach the Beast Box server. Check your connection and try again.");
    }
    return failure(route, error instanceof Error ? error.message : "The model did not answer.");
  }
}

/** Bounded per-Beast chat log (verified replies only) so minimizing or navigating never wipes it. */
export const LOG_PREFIX = "beastbox-talk-log-v1:";
export const MAX_LOG = 24;
export function readTalkLog(storage, key) {
  try {
    const rows = JSON.parse(storage?.getItem(LOG_PREFIX + key) || "[]");
    return Array.isArray(rows) ? rows.filter((r) => r && (r.role === "you" || r.role === "beast") && typeof r.text === "string").slice(-MAX_LOG) : [];
  } catch {
    return [];
  }
}
export function writeTalkLog(storage, key, rows) {
  try { storage?.setItem(LOG_PREFIX + key, JSON.stringify(rows.slice(-MAX_LOG))); return true; } catch { return false; }
}
