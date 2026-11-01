/**
 * Muse's opening (Cory, 2026-10-31): when nobody is with him, Meta Muse may keep
 * teaching the GROWING Zeref (never the pin). Every turn is logged as a step.
 * His replies are kept verbatim; names are never filtered. Lessons stay growing-only
 * and are not routed into any training routine. No paid inference.
 */
import { createHmac, createHash } from "node:crypto";
import SEED from "./opening-last-class.mjs";
import XWIN from "./opening-x-window.mjs";

export const LOG_KEY = "zeref-opening:log";
export const PRESENCE_KEY = "zeref-opening:presence";
export const PRESENCE_WINDOW_S = 20 * 60;
export const CLASS_GAP_MS = 30 * 60 * 1000;
export const CLASS_CAP = 19;
export const MAX_WORDS = 8;
export const MAX_LOG = 400;
export const GROWING_LABEL = "Growing Zeref · not the pin";
export const WEB_ALLOW = ["simple.wikipedia.org", "en.wikipedia.org", "commons.wikimedia.org", "www.gutenberg.org", "gutenberg.org"];
export const WEB_MAX_BYTES = 200_000;
const ZEREF_NOTE = "Zeref is a growing Beast Box character (rawrphos-native, CPU). Replies are verbatim; every turn is a step in him growing.";

const nowIso = (t) => new Date(t).toISOString();
export const wordCount = (s) => String(s).trim().split(/\s+/).filter(Boolean).length;

export async function readLog(store) {
  const log = await store.get(LOG_KEY);
  return Array.isArray(log) ? log : [];
}
/** Continue-where-we-left-off view: stored steps, or the recorded last class when none yet. */
export async function classLog(store, limit = 19) {
  const log = await readLog(store);
  const n = Math.min(60, Math.max(1, Number.isInteger(limit) ? limit : 19));
  if (log.length) return { source: "shared lesson log (growing only)", turns: log.slice(-n), total_steps: log.length };
  return { source: SEED.label, class: SEED.class, turns: SEED.turns.slice(-n), total_steps: 0 };
}
export async function appendStep(store, step) {
  const log = await readLog(store);
  log.push({ ...step, n: (log.length ? (log[log.length - 1].n || log.length) : 0) + 1, kind: "step" });
  await store.set(LOG_KEY, log.slice(-MAX_LOG));
  return log[log.length - 1];
}

/** A human or Phera session marks itself here (owner heartbeat); Muse teaches only when it is clear. */
export async function markPresence(store, who, now = Date.now()) {
  const w = who === "phera" ? "phera" : "human";
  await store.set(PRESENCE_KEY, { who: w, at: nowIso(now) }, PRESENCE_WINDOW_S);
  return { who: w, until: nowIso(now + PRESENCE_WINDOW_S * 1000) };
}
export async function presence(store, now = Date.now()) {
  const mark = await store.get(PRESENCE_KEY);
  if (mark && Date.parse(mark.at) > now - PRESENCE_WINDOW_S * 1000) return { someone_with_him: true, who: mark.who, since: mark.at, muse_may_teach: false };
  const log = await readLog(store);
  const lastOther = [...log].reverse().find((s) => s.teacher && s.teacher !== "muse");
  if (lastOther && Date.parse(lastOther.at) > now - PRESENCE_WINDOW_S * 1000) return { someone_with_him: true, who: lastOther.teacher, since: lastOther.at, muse_may_teach: false };
  return { someone_with_him: false, who: null, muse_may_teach: true, window_minutes: PRESENCE_WINDOW_S / 60 };
}
/** Muse turns in the current class: a run of Muse steps with gaps under 30 minutes. */
export function museClassCount(log, now = Date.now()) {
  let count = 0, t = now;
  for (let i = log.length - 1; i >= 0; i--) {
    const s = log[i];
    if (s.teacher !== "muse") break;
    const at = Date.parse(s.at);
    if (t - at > CLASS_GAP_MS) break;
    count++; t = at;
  }
  return count;
}

/** Talk door to the growing mind on the bridge. Verifies the reply is not the pin. */
export function createGrowingTalk(pinSha, env = process.env, fetchImpl = fetch) {
  const url = env.BEASTBOX_CLOUD_BRIDGE_URL, token = env.BEASTBOX_CLOUD_BRIDGE_TOKEN, secret = env.BEASTBOX_CLOUD_AUTH_SECRET;
  if (!url || !token || !secret || secret.length < 32) return null;
  const identity = createHmac("sha256", secret).update("meta-muse-opening").digest("hex");
  return async (text) => {
    try {
      const res = await fetchImpl(new URL("/api/guest-growing", url), {
        method: "POST", redirect: "error", cache: "no-store",
        headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
        body: JSON.stringify({ text, guest_identity: identity }), signal: AbortSignal.timeout(55_000),
      });
      const raw = await res.text();
      if (raw.length > 16000) return { error: "oversized reply" };
      const r = JSON.parse(raw);
      if (!res.ok) return { error: res.status === 429 ? "Zeref's slot is busy. Try again soon." : "Growing Zeref unavailable.", status: res.status };
      if (r.schema !== "beastbox-guest-growing-v1" || r.model !== "rawrphos-native" || r.is_public_pin !== false || r.label !== GROWING_LABEL ||
          typeof r.checkpoint_sha256 !== "string" || r.checkpoint_sha256 === pinSha || typeof r.reply !== "string" || r.reply.length > 6000 ||
          typeof r.tag !== "string" || !/^zeref-growing-\d{3,}$/.test(r.tag)) return { error: "Unverified growing reply. Nothing invented." };
      return { reply: r.reply, tag: r.tag, step: r.step ?? null, checkpoint_sha256: r.checkpoint_sha256 };
    } catch { return { error: "Growing Zeref did not answer in time." }; }
  };
}

/** Read-only public lesson fetch: https, allowlisted hosts, no redirects, size cap, text only. */
export async function readWeb(rawUrl, fetchImpl = fetch) {
  let u;
  try { u = new URL(String(rawUrl)); } catch { return { error: "invalid_url" }; }
  if (u.protocol !== "https:" || u.username || u.password || u.port || !WEB_ALLOW.includes(u.hostname)) return { error: "not_allowed", allowed_hosts: WEB_ALLOW };
  const res = await fetchImpl(u, { redirect: "error", cache: "no-store", signal: AbortSignal.timeout(8000), headers: { "user-agent": "BeastBoxCOSMOS-MuseOpening/1 (+https://github.com/NavisWORLD/The-beast-box-)" } });
  if (!res.ok || !res.body) return { error: "fetch_failed", status: res.status };
  const reader = res.body.getReader(); const parts = []; let total = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    total += value.byteLength; if (total > WEB_MAX_BYTES) { await reader.cancel(); break; }
    parts.push(value);
  }
  const text = Buffer.concat(parts.map((p) => Buffer.from(p))).toString("utf8")
    .replace(/<(script|style)[\s\S]*?<\/\1>/gi, " ").replace(/<[^>]*>/g, " ")
    .replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (m) => ({ "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&nbsp;": " " }[m]))
    .replace(/\s+/g, " ").trim();
  return { url: u.href, host: u.hostname, label: "RECORDED public page text (read only)", truncated: total > WEB_MAX_BYTES, text: text.slice(0, 4000) };
}

export function scrubX(s) {
  return String(s || "").replace(/https?:\/\/\S+/g, "").replace(/@\w{1,15}/g, "someone")
    .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, "").replace(/\+?\d[\d\s().-]{7,}\d/g, "").trim();
}
export function xWindow(limit = 5) {
  const n = Math.min(10, Math.max(1, Number.isInteger(limit) ? limit : 5));
  return { label: XWIN.label, posts: XWIN.posts.slice(-n).map((p) => ({ ...p, text: scrubX(p.text), narration: scrubX(p.narration) })), note: "Public posts only. No DMs. Nothing can be posted from here." };
}

const ro = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
const noArgs = { type: "object", properties: {}, additionalProperties: false };
export const OPENING_TOOLS = [
  { name: "zeref_check_presence", title: "Is anyone with Zeref?", classification: "Read", inputSchema: noArgs, annotations: ro,
    description: "Says whether a human or Phera is with the growing Zeref right now. Teach only when muse_may_teach is true. Read only." },
  { name: "zeref_read_class_log", title: "Read Zeref's class log", classification: "Read", annotations: ro,
    inputSchema: { type: "object", properties: { last: { type: "integer", minimum: 1, maximum: 60, default: 19 } }, additionalProperties: false },
    description: "Returns the last steps of the shared growing-only lesson log so you continue where the last teacher stopped. Replies are verbatim. Read only." },
  { name: "zeref_teach", title: "Teach the growing Zeref", classification: "Write", annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
    inputSchema: { type: "object", properties: { line: { type: "string", minLength: 1, maxLength: 80, description: "One simple line, 8 words or fewer." }, topic: { type: "string", maxLength: 40 } }, required: ["line"], additionalProperties: false },
    description: "Says one simple line (8 words or fewer) to the growing Zeref (zeref-growing, never the pin) and returns his verbatim reply. Only works when nobody is with him. Up to 19 lines per class. Each turn is appended to the lesson log as a step. Requires Read + care actions." },
  { name: "zeref_read_library", title: "Read Zeref's library", classification: "Read", annotations: ro,
    inputSchema: { type: "object", properties: { query: { type: "string", minLength: 2, maxLength: 120 } }, required: ["query"], additionalProperties: false },
    description: "Keyword search of Zeref's library; returns up to 3 verbatim passages. Read only." },
  { name: "zeref_read_web", title: "Read a public lesson page", classification: "Read", annotations: { ...ro, openWorldHint: true },
    inputSchema: { type: "object", properties: { url: { type: "string", maxLength: 500 } }, required: ["url"], additionalProperties: false },
    description: "Reads a public page from Wikipedia, Simple Wikipedia, Wikimedia Commons or Project Gutenberg (https only, no redirects, 200 KB cap, first 4,000 characters of text). Read only." },
  { name: "zeref_read_x_window", title: "Zeref's window to X", classification: "Read", annotations: ro,
    inputSchema: { type: "object", properties: { last: { type: "integer", minimum: 1, maximum: 10, default: 5 } }, additionalProperties: false },
    description: "Recent public X posts from Zeref's X TV inbox with teacher narration. Public posts only, no DMs, handles and personal details stripped, no posting. Read only." },
];
export const OPENING_NAMES = OPENING_TOOLS.map((t) => t.name);

/**
 * @param {{store:any, now?:number, talk?:(t:string)=>Promise<any>, library?:(q:string)=>Promise<any>, fetchImpl?:typeof fetch}} ctx
 */
export async function callOpeningTool(name, input, ctx, ok, toolError) {
  const now = ctx.now || Date.now();
  if (name === "zeref_check_presence") return ok(await presence(ctx.store, now));
  if (name === "zeref_read_class_log") return ok({ ...(await classLog(ctx.store, input.last)), note: ZEREF_NOTE, label: GROWING_LABEL });
  if (name === "zeref_read_x_window") return ok(xWindow(input.last));
  if (name === "zeref_read_web") {
    try { const r = await readWeb(input.url, ctx.fetchImpl || fetch); return r.error ? toolError(r.error, "That page can't be read here.", r) : ok(r); }
    catch { return toolError("fetch_failed", "The page did not load. Nothing invented."); }
  }
  if (name === "zeref_read_library") {
    const q = typeof input.query === "string" ? input.query.trim() : "";
    if (q.length < 2 || q.length > 120) return toolError("invalid_input", "query must be 2-120 characters.");
    if (!ctx.library) return toolError("library_unavailable", "Zeref's library storage is not set up on this deployment.");
    try { return ok({ label: "RECORDED passages, verbatim, read only", ...(await ctx.library(q)) }); }
    catch { return toolError("library_unavailable", "The library did not answer."); }
  }
  if (name === "zeref_teach") {
    const line = typeof input.line === "string" ? input.line.trim() : "";
    if (!line || line.length > 80 || /[\x00-\x1f\x7f]/.test(line)) return toolError("invalid_input", "line must be 1-80 characters.");
    if (wordCount(line) > MAX_WORDS) return toolError("too_long", `Keep it simple: ${MAX_WORDS} words or fewer.`);
    const p = await presence(ctx.store, now);
    if (!p.muse_may_teach) return toolError("someone_is_with_him", `Someone (${p.who}) is with Zeref now. Muse waits until nobody is.`, p);
    const log = await readLog(ctx.store);
    const used = museClassCount(log, now);
    if (used >= CLASS_CAP) return toolError("class_full", `This class has its ${CLASS_CAP} lines. Let him rest 30 minutes, then start a new class.`);
    if (!ctx.talk) return toolError("zeref_unavailable", "The growing mind's door is not configured here. No reply was invented.");
    const said = await ctx.talk(line);
    const step = await appendStep(ctx.store, {
      at: nowIso(now), teacher: "muse", say: line, topic: typeof input.topic === "string" ? input.topic.slice(0, 40) : null,
      reply: said.reply ?? null, note: said.reply ? null : (said.error || "no reply"), tag: said.tag || null, model_step: said.step ?? null,
      sha12: said.checkpoint_sha256 ? said.checkpoint_sha256.slice(0, 12) : null, label: GROWING_LABEL,
      id: createHash("sha256").update(nowIso(now) + line).digest("hex").slice(0, 16),
    });
    return ok({ zeref: said.reply ?? null, step, class_lines_used: used + 1, class_cap: CLASS_CAP, label: GROWING_LABEL, note: ZEREF_NOTE });
  }
  return null;
}
