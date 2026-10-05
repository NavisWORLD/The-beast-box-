/**
 * Meta Muse connector tools for one paired Beast Box beast.
 *
 * Read tools never change state. Write tools change only the paired beast's care
 * save (they are queued for the browser and mirrored on the connector copy).
 * Nothing here buys, sends, posts or shares anything. No tool is sensitive.
 */
import { randomBytes } from "node:crypto";
import { buildMoveset } from "../companion/beast-moves.mjs";
import { careAction, grantXp, nextGoal, shownName } from "../companion/session.mjs";
import { nameBeast, placeById } from "../companion/adventure.mjs";
import { renderContextPrompt } from "../companion/context.mjs";
import { guestSafeContext } from "../companion/ask-beast.mjs";
import { isKidSafe } from "../companion/learn.mjs";
import { canCare, getAccount, updateAccount } from "./auth.mjs";

export const MAX_PENDING_ACTIONS = 50;
export const PROVENANCE_NOTE = "Seeded from recorded IBM Quantum measurement counts saved in Beast Box. There is no live quantum link.";
export const COMPANION_LABEL = "In-character reply from a Beast Box game companion model (RAWRPHØS guest-safe brain). It is a game character, not a conscious mind, and not Meta Muse.";

const requestId = { type: "string", minLength: 1, maxLength: 64, description: "Optional idempotency key. Repeating a call with the same request_id returns the first result instead of applying the action twice." };
const noArgs = { type: "object", properties: {}, additionalProperties: false };

/** Tool list. `classification` is the Muse review class (Read / Write); none are Sensitive write. */
export const TOOLS = [
  {
    name: "get_beast", title: "Get beast", classification: "Read",
    description: "Returns the paired Beast Box beast: name, species, element, stage, mood, stats for its current stage, and seed provenance (recorded IBM Quantum counts; no live quantum link). Read only.",
    inputSchema: noArgs,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: "get_care_status", title: "Get care status", classification: "Read",
    description: "Returns the paired beast's care values (experience, bond, energy, stage, next stage goal, mood), when the browser last synced, and how many care actions are waiting to sync. Read only.",
    inputSchema: noArgs,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: "get_lost_cosmos_progress", title: "Get Lost Cosmos progress", classification: "Read",
    description: "Returns what the shared care save records about Lost Cosmos: whether the beast is linked to a Lost Cosmos QBEAST, its native stage, the field location, training rounds and whether the cartridge has booted. In-cartridge story progress lives in the emulator save and is not available. Read only.",
    inputSchema: noArgs,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: "list_moves", title: "List moves", classification: "Read",
    description: "Lists the paired beast's seeded attack moves (name, style, charge and strike timing in milliseconds, relative power from 0 to 1) as used by the Beast Cage habitat. Read only.",
    inputSchema: noArgs,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: "feed_beast", title: "Feed beast", classification: "Write",
    description: "Feeds the paired beast once using the Beast Box care rules (+6 experience, +1 bond, energy changes). Changes only this beast's care save; the browser applies it on its next sync. Requires the Read + care actions permission.",
    inputSchema: { type: "object", properties: { request_id: requestId }, additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
  },
  {
    name: "play_with_beast", title: "Play with beast", classification: "Write",
    description: "Plays with the paired beast once using the Beast Box care rules: 'pet' (+4 experience, +2 bond) or 'spark' (+3 experience, +1 bond). Changes only this beast's care save; the browser applies it on its next sync. Requires the Read + care actions permission.",
    inputSchema: { type: "object", properties: { activity: { type: "string", enum: ["pet", "spark"], default: "pet", description: "pet or spark" }, request_id: requestId }, additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
  },
  {
    name: "rename_beast", title: "Rename beast", classification: "Write",
    description: "Sets the paired beast's display name (1-24 letters, digits, spaces, . ' -). The species and seed do not change. Changes only this beast's care save; the browser applies it on its next sync. Requires the Read + care actions permission.",
    inputSchema: { type: "object", properties: { name: { type: "string", minLength: 1, maxLength: 24 }, request_id: requestId }, required: ["name"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: "talk_to_beast", title: "Talk to beast", classification: "Write",
    description: "Sends one message (1-400 characters) to the paired beast and returns its in-character reply from the Beast Box game companion model (RAWRPHØS guest-safe brain, no owner memory). The exchange is added to the beast's care save (+3 experience, +1 bond) on the next browser sync. The reply comes from a game character, not a conscious mind. Requires the Read + care actions permission.",
    inputSchema: { type: "object", properties: { message: { type: "string", minLength: 1, maxLength: 400 }, request_id: requestId }, required: ["message"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
  },
];
export const TOOL_NAMES = TOOLS.map((t) => t.name);
const WRITE = new Set(TOOLS.filter((t) => t.classification === "Write").map((t) => t.name));

/** MCP wire format (drops the review-only `classification`). */
export function listTools() {
  return TOOLS.map(({ classification, ...tool }) => ({ ...tool, _meta: { "beastbox/classification": classification, "beastbox/sensitive": false } }));
}

const ok = (data) => ({ content: [{ type: "text", text: JSON.stringify(data, null, 1) }], structuredContent: data });
export const toolError = (code, message, extra = {}) => ({ isError: true, content: [{ type: "text", text: JSON.stringify({ error: { code, message, ...extra } }) }], structuredContent: { error: { code, message, ...extra } } });

function beastView(snapshot) {
  const b = snapshot && snapshot.beast;
  if (!b) return null;
  const g = b.genome || {};
  const stage = String(b.stage || 1);
  return {
    name: shownName({ displayName: b.displayName, genome: { names: g.names || {} }, stage: b.stage }) || (g.names && g.names[stage]) || "Spark Beast",
    species: (g.names && g.names[stage]) || g.body || "Spark Beast",
    body: g.body || null,
    element: g.element || null,
    temperament: g.temperament || null,
    stage: b.stage || 1,
    mood: b.mood || "idle",
    stats: (g.stats && g.stats[stage]) || null,
    seed_provenance: {
      seed: g.seed || b.seed || null,
      backend: g.quantum ? g.quantum.backend || null : null,
      job_id: g.quantum ? g.quantum.job_id || null : null,
      top_state: g.quantum ? g.quantum.top_state || null : null,
      counts_sha256: g.quantum ? g.quantum.counts_sha256 || null : null,
      note: PROVENANCE_NOTE,
    },
  };
}
function syncInfo(account) {
  return { last_synced_at: account.snapshot ? account.snapshot.syncedAt : null, pending_actions: (account.actions || []).length };
}
const noBeast = () => toolError("no_beast", "No beast is in the paired care save yet. Open Beast Box, meet a beast, and keep the page open so it can sync.");

/** Mirror a care action on the connector copy with the same rules the browser uses. */
export function applyToSnapshot(snapshot, action) {
  if (!snapshot || !snapshot.beast) return null;
  const session = { beast: JSON.parse(JSON.stringify(snapshot.beast)), bestiary: [], mood: snapshot.beast.mood };
  let result;
  if (action.type === "feed") result = careAction(session, "feed");
  else if (action.type === "play") result = careAction(session, action.args.activity === "spark" ? "spark" : "pet");
  else if (action.type === "rename") result = nameBeast(session, action.args.name);
  else if (action.type === "talk") {
    // Same rule as rememberExchange in the browser: only kid-safe exchanges grow the beast.
    if (!isKidSafe(action.args.you) || !isKidSafe(action.args.beast)) result = { ok: true, safe: false };
    else { session.beast.bond = Math.min(100, (session.beast.bond || 0) + 1); result = grantXp(session, 3, "talk"); }
  }
  snapshot.beast = session.beast;
  return result;
}
export const cleanName = (name) => String(name || "").replace(/[^\w .'-]/g, "").trim().slice(0, 24);

async function recordActivity(store, auth, tool, now) {
  try {
    await updateAccount(store, auth.accountId, (account) => {
      account.lastActivityAt = new Date(now).toISOString();
      account.lastActivity = { tool, at: account.lastActivityAt, via: auth.kind === "pat" ? "Muse Code token" : "OAuth client" };
      for (const t of account.tokens || []) if (t.id === auth.tokenId) t.lastUsedAt = account.lastActivityAt;
    });
  } catch { /* account removed mid-call */ }
}

/**
 * @param {string} name
 * @param {Record<string, unknown>} args
 * @param {{ store: any, auth: { accountId: string, scope: string, kind: string, tokenId: string }, now?: number,
 *   limit?: (bucket: string) => Promise<{ ok: boolean, retryAfter: number }>,
 *   talk?: (prompt: string) => Promise<{ reply: string, model?: string, error?: string }> }} ctx
 */
export async function callTool(name, args = {}, ctx) {
  const now = ctx.now || Date.now();
  if (!TOOL_NAMES.includes(name)) return toolError("unknown_tool", `Unknown tool: ${name}`);
  const input = args && typeof args === "object" ? args : {};
  const write = WRITE.has(name);
  if (write && !canCare(ctx.auth.scope)) {
    return toolError("insufficient_scope", "This Meta Muse connection is Read only. Reconnect and choose 'Read + care actions' to let Muse care for the beast.", { required_scope: "beast.care" });
  }
  if (ctx.limit) {
    const bucket = name === "talk_to_beast" ? "talk" : write ? "write" : "read";
    const rl = await ctx.limit(bucket);
    if (!rl.ok) return toolError("rate_limited", `Too many ${bucket} calls. Try again in ${rl.retryAfter} seconds.`, { retry_after_seconds: rl.retryAfter });
  }
  const account = await getAccount(ctx.store, ctx.auth.accountId);
  if (!account) return toolError("not_paired", "This beast is no longer paired with Meta Muse.");
  await recordActivity(ctx.store, ctx.auth, name, now);
  const snap = account.snapshot;

  if (name === "get_beast") {
    const beast = beastView(snap);
    return beast ? ok({ beast, ...syncInfo(account) }) : noBeast();
  }
  if (name === "get_care_status") {
    const b = snap && snap.beast;
    if (!b) return noBeast();
    const goal = b.qbeast ? null : nextGoal(b.xp || 0);
    return ok({ care: { experience: b.xp || 0, bond: b.bond || 0, energy: b.energy ?? 100, stage: b.stage || 1, next_stage_at_experience: goal, mood: b.mood || "idle", stage_source: b.qbeast ? "earned in the Lost Cosmos cartridge" : "care experience" }, ...syncInfo(account) });
  }
  if (name === "get_lost_cosmos_progress") {
    if (!snap) return noBeast();
    const b = snap.beast;
    const place = snap.place ? placeById(snap.place) : null;
    return ok({
      lost_cosmos: {
        linked_qbeast: b && b.qbeast ? { profile_id: b.qbeast.profileId, name: b.qbeast.profileName } : null,
        native_stage: b && b.nativeStage ? b.nativeStage : null,
        field_location: place ? place.name : null,
        training: snap.train || { rounds: 0, score: 0 },
        cartridge_booted: Boolean(snap.emulator && snap.emulator.booted),
        beasts_met: snap.bestiaryCount || 0,
        note: "In-cartridge story progress and items live in the emulator's own save and are not shared with this connector.",
      },
      ...syncInfo(account),
    });
  }
  if (name === "list_moves") {
    const g = snap && snap.beast && snap.beast.genome;
    if (!g) return noBeast();
    const moves = buildMoveset(g);
    return ok({ element: moves.element, moves: moves.moves.map((m) => ({ name: m.name, style: m.style, charge_ms: m.chargeMs, strike_ms: m.strikeMs, power: Math.round(m.power * 100) / 100 })), note: "Moves are derived from the recorded seed and genome traits.", ...syncInfo(account) });
  }

  // ---- writes
  if (!snap || !snap.beast) return noBeast();
  const rid = typeof input.request_id === "string" ? input.request_id.slice(0, 64) : "";
  if (rid && account.requests && account.requests[name + ":" + rid]) return ok({ ...account.requests[name + ":" + rid].result, repeated_request: true });
  if ((account.actions || []).length >= MAX_PENDING_ACTIONS) return toolError("sync_backlog", "Too many care actions are waiting for the browser to sync. Open Beast Box to apply them, then try again.");

  let action;
  let extra = {};
  if (name === "feed_beast") action = { type: "feed", args: {} };
  else if (name === "play_with_beast") {
    const activity = input.activity === undefined ? "pet" : input.activity;
    if (!["pet", "spark"].includes(activity)) return toolError("invalid_input", "activity must be 'pet' or 'spark'.");
    action = { type: "play", args: { activity } };
  } else if (name === "rename_beast") {
    const clean = cleanName(input.name);
    if (!clean) return toolError("invalid_input", "name must contain 1-24 letters, digits, spaces, . ' or -.");
    action = { type: "rename", args: { name: clean } };
  } else if (name === "talk_to_beast") {
    const message = typeof input.message === "string" ? input.message.trim() : "";
    if (!message || message.length > 400 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(message)) return toolError("invalid_input", "message must contain 1-400 characters.");
    if (!ctx.talk) return toolError("companion_unavailable", "The game companion model is not configured on this deployment. No reply was invented.");
    const b = snap.beast;
    const view = beastView(snap);
    const place = snap.place ? placeById(snap.place) : null;
    const context = guestSafeContext({ name: view.name, location: place ? place.name : "Lost Cosmos", nearby: place ? place.nearby : [], mood: b.mood, level: b.stage, xp: b.xp, bond: b.bond, energy: b.energy });
    const said = await ctx.talk(renderContextPrompt(context, message, 700));
    if (!said || !said.reply) return toolError("companion_unavailable", (said && said.error) || "The game companion model did not answer. No reply was invented and nothing was saved.");
    const reply = String(said.reply).slice(0, 1200);
    action = { type: "talk", args: { you: message, beast: reply.slice(0, 400) } };
    extra = { speaker: `${view.name} (Beast Box game companion)`, reply, model: said.model || "rawrphos-native", label: COMPANION_LABEL };
  }
  const id = "act_" + randomBytes(6).toString("hex");
  const result = await updateAccount(ctx.store, ctx.auth.accountId, (acct) => {
    const effect = applyToSnapshot(acct.snapshot, action) || {};
    acct.actions = [...(acct.actions || []), { id, ...action, seed: acct.snapshot.beast.seed, at: new Date(now).toISOString() }];
    const b = acct.snapshot.beast;
    const out = {
      ...extra,
      action: { id, type: action.type, ...action.args, status: "applied to the connector copy; the browser applies it on its next sync" },
      care: { experience: b.xp, bond: b.bond, energy: b.energy, stage: b.stage, mood: b.mood, name: b.displayName || null, evolved: Boolean(effect.evolved) },
      pending_actions: acct.actions.length,
    };
    if (action.type === "talk") delete out.action.beast;
    if (rid) {
      const cutoff = now - 24 * 3600 * 1000;
      const kept = Object.entries(acct.requests || {}).filter(([, v]) => Date.parse(v.at) > cutoff).slice(-49);
      acct.requests = Object.fromEntries([...kept, [name + ":" + rid, { at: new Date(now).toISOString(), result: out }]]);
    }
    return out;
  });
  return ok(result);
}

/** Browser sync: store the fresh snapshot, drop acknowledged actions, re-mirror the rest. */
export async function syncAccount(store, accountId, snapshot, ack = []) {
  return updateAccount(store, accountId, (account) => {
    const done = new Set(Array.isArray(ack) ? ack.filter((x) => typeof x === "string").slice(0, 100) : []);
    account.actions = (account.actions || []).filter((a) => !done.has(a.id));
    if (snapshot) {
      account.snapshot = snapshot;
      // Actions for a beast the browser no longer has selected are dropped, not applied elsewhere.
      const seed = snapshot.beast ? snapshot.beast.seed : null;
      account.actions = account.actions.filter((a) => !a.seed || a.seed === seed);
      for (const action of account.actions) applyToSnapshot(account.snapshot, action);
    }
    return { actions: account.actions.map((a) => ({ id: a.id, type: a.type, args: a.args, seed: a.seed, at: a.at })) };
  });
}
