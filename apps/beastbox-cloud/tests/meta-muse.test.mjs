import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import runs from "../lib/companion/spark/runs.json" with { type: "json" };
import { adoptBeast, createSession, exportSession } from "../lib/companion/session.mjs";
import {
  authenticate, checkAuthorizeRequest, consumePairingCode, createAccount, createAuthCode, createPat, exchangeToken,
  getAccount, newPairingCode, normalizeScope, pkceChallenge, publicStatus, registerClient, revokeById, revokeToken,
  scopeForChoice, unpairAccount, verifyPkce,
} from "../lib/muse/auth.mjs";
import { LIMITS, rateLimit } from "../lib/muse/rate-limit.mjs";
import { MAX_SNAPSHOT_BYTES, minimalSnapshot, SNAPSHOT_SCHEMA, validateSnapshot } from "../lib/muse/snapshot.mjs";
import { createMemoryStore, createRedisRestStore, storageStatus, storeFromEnv } from "../lib/muse/store.mjs";
import { callTool, listTools, PROVENANCE_NOTE, syncAccount, TOOLS } from "../lib/muse/tools.mjs";
import { createBridgeTalk } from "../lib/muse/bridge-talk.mjs";
import { aiCatalog, PAIRING_METHODS, PROTOCOL_VERSIONS, SERVER_CARD_SCHEMA, SERVER_CARD_TYPE, serverCard, serverCardUrl } from "../lib/muse/discovery.mjs";
import { pairingLink, parsePairingFragment } from "../lib/muse/pairing-link.mjs";
import { defaultDeviceName, deviceById, setDeviceName } from "../lib/muse/auth.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const RESOURCE = "https://beast.example/api/mcp";
const VERIFIER = "v".repeat(20) + "-verifier-0123456789abcdefghij";

function beastSession(name = "Moss") {
  const session = createSession();
  adoptBeast(session, buildGenome({ focus: 40, calm: 40, spark: 20 }, runs[0], null), name);
  session.chat.push({ role: "you", text: "private chat line" });
  return session;
}
async function paired(store = createMemoryStore()) {
  const snapshot = minimalSnapshot(exportSession(beastSession()), { place: "shore" });
  const { account, deviceSecret } = await createAccount(store, { snapshot });
  return { store, account, deviceSecret };
}
async function oauthToken(store, accountId, choice) {
  const client = await registerClient(store, { client_name: "Meta Muse", redirect_uris: ["https://muse.example/callback"] });
  const q = { client_id: client.client_id, redirect_uri: "https://muse.example/callback", response_type: "code", code_challenge: pkceChallenge(VERIFIER), code_challenge_method: "S256", resource: RESOURCE };
  await checkAuthorizeRequest(store, q, RESOURCE);
  const code = await createAuthCode(store, { client, redirectUri: q.redirect_uri, codeChallenge: q.code_challenge, scope: scopeForChoice(choice), accountId, resource: RESOURCE });
  const tokens = await exchangeToken(store, { grant_type: "authorization_code", code, client_id: client.client_id, redirect_uri: q.redirect_uri, code_verifier: VERIFIER, resource: RESOURCE });
  return { client, code, tokens };
}
const data = (result) => result.structuredContent;

test("PKCE accepts only a matching S256 verifier", () => {
  const challenge = pkceChallenge(VERIFIER);
  assert.equal(verifyPkce(VERIFIER, challenge), true);
  assert.equal(verifyPkce(VERIFIER + "x", challenge), false);
  assert.equal(verifyPkce(VERIFIER, challenge, "plain"), false);
  assert.equal(verifyPkce("short", pkceChallenge("short")), false);
});

test("scopes: read only is the default and care always includes read", () => {
  assert.equal(scopeForChoice("read"), "beast.read");
  assert.equal(scopeForChoice("care"), "beast.read beast.care");
  assert.equal(normalizeScope("beast.care admin"), "beast.read beast.care");
  assert.equal(normalizeScope("admin"), "beast.read");
});

test("authorize requests need a registered client, exact redirect URI, S256 PKCE and this resource", async () => {
  const store = createMemoryStore();
  await assert.rejects(registerClient(store, { redirect_uris: ["http://evil.example/cb"] }), /https/);
  const client = await registerClient(store, { client_name: "Muse", redirect_uris: ["https://muse.example/cb", "http://127.0.0.1:7777/cb"] });
  const base = { client_id: client.client_id, redirect_uri: "https://muse.example/cb", response_type: "code", code_challenge: pkceChallenge(VERIFIER), code_challenge_method: "S256" };
  await checkAuthorizeRequest(store, base, RESOURCE);
  await assert.rejects(checkAuthorizeRequest(store, { ...base, redirect_uri: "https://muse.example/other" }, RESOURCE), /redirect URI/);
  await assert.rejects(checkAuthorizeRequest(store, { ...base, code_challenge_method: "plain" }, RESOURCE), /PKCE/);
  await assert.rejects(checkAuthorizeRequest(store, { ...base, resource: "https://other.example/mcp" }, RESOURCE), /resource/);
  await assert.rejects(checkAuthorizeRequest(store, { ...base, client_id: "bbm_client_" + "0".repeat(24) }, RESOURCE), /Unknown client/);
});

test("pairing codes are short, single use and map to one account", async () => {
  const { store, account } = await paired();
  const { code } = await newPairingCode(store, account.id);
  assert.match(code, /^[A-Z2-9]{4}-[A-Z2-9]{4}$/);
  assert.equal((await consumePairingCode(store, code.toLowerCase().replace("-", " "))).id, account.id);
  assert.equal(await consumePairingCode(store, code), null);
});

test("authorization codes are single use and need the right PKCE verifier", async () => {
  const { store, account } = await paired();
  const { client, code, tokens } = await oauthToken(store, account.id, "read");
  assert.equal(tokens.scope, "beast.read");
  assert.match(tokens.access_token, /^bbm_at_/);
  await assert.rejects(exchangeToken(store, { grant_type: "authorization_code", code, client_id: client.client_id, redirect_uri: "https://muse.example/callback", code_verifier: VERIFIER }), /already used/);
  const code2 = await createAuthCode(store, { client, redirectUri: "https://muse.example/callback", codeChallenge: pkceChallenge(VERIFIER), scope: "beast.read", accountId: account.id, resource: RESOURCE });
  await assert.rejects(exchangeToken(store, { grant_type: "authorization_code", code: code2, client_id: client.client_id, redirect_uri: "https://muse.example/callback", code_verifier: VERIFIER + "nope" }), /PKCE/);
});

test("read-only tokens can read but every write tool is blocked", async () => {
  const { store, account } = await paired();
  const { tokens } = await oauthToken(store, account.id, "read");
  const auth = await authenticate(store, "Bearer " + tokens.access_token);
  assert.equal(auth.scope, "beast.read");
  const beast = data(await callTool("get_beast", {}, { store, auth }));
  assert.equal(beast.beast.name, "Moss");
  for (const name of ["feed_beast", "play_with_beast", "rename_beast", "talk_to_beast"]) {
    const out = await callTool(name, { name: "X", message: "hi" }, { store, auth, talk: async () => ({ reply: "rawr" }) });
    assert.equal(out.isError, true, name);
    assert.equal(data(out).error.code, "insufficient_scope", name);
  }
  assert.equal((await getAccount(store, account.id)).actions.length, 0);
});

test("care tokens feed, play and rename using the cage care rules and queue actions for the browser", async () => {
  const { store, account } = await paired();
  const { tokens } = await oauthToken(store, account.id, "care");
  const auth = await authenticate(store, "Bearer " + tokens.access_token);
  const fed = data(await callTool("feed_beast", { request_id: "r1" }, { store, auth }));
  assert.equal(fed.care.experience, 6);
  assert.equal(fed.care.bond, 2);
  const again = data(await callTool("feed_beast", { request_id: "r1" }, { store, auth }));
  assert.equal(again.repeated_request, true);
  assert.equal(again.care.experience, 6);
  const played = data(await callTool("play_with_beast", { activity: "spark" }, { store, auth }));
  assert.equal(played.care.experience, 9);
  assert.equal(data(await callTool("play_with_beast", { activity: "dance" }, { store, auth })).error.code, "invalid_input");
  const named = data(await callTool("rename_beast", { name: "Sir <Moss>" }, { store, auth }));
  assert.equal(named.care.name, "Sir Moss");
  const acct = await getAccount(store, account.id);
  assert.deepEqual(acct.actions.map((a) => a.type), ["feed", "play", "rename"]);
  assert.ok(acct.actions.every((a) => a.seed === acct.snapshot.beast.seed));
  assert.equal(acct.lastActivity.tool, "rename_beast");
});

test("talk_to_beast is labeled a game companion, never invents replies, and is kid-safe mirrored", async () => {
  const { store, account } = await paired();
  const pat = await createPat(store, account.id, "care");
  const auth = await authenticate(store, "Bearer " + pat.token);
  const none = data(await callTool("talk_to_beast", { message: "hello" }, { store, auth }));
  assert.equal(none.error.code, "companion_unavailable");
  let prompt = "";
  const said = data(await callTool("talk_to_beast", { message: "hello" }, { store, auth, talk: async (p) => { prompt = p; return { reply: "Rrr, the shore is warm!", model: "rawrphos-native" }; } }));
  assert.equal(said.reply, "Rrr, the shore is warm!");
  assert.match(said.label, /game companion/);
  assert.match(said.label, /not a conscious mind/);
  assert.match(prompt, /Game companion Moss is in Pale Shore/);
  assert.match(prompt, /Memories: No stored memories yet/);
  assert.doesNotMatch(prompt, /private chat line/);
  const failed = data(await callTool("talk_to_beast", { message: "hello" }, { store, auth, talk: async () => ({ reply: "", error: "host down" }) }));
  assert.equal(failed.error.message, "host down");
  assert.equal((await getAccount(store, account.id)).actions.length, 1);
});

test("read tools report seed provenance, care, Lost Cosmos progress and moves honestly", async () => {
  const { store, account } = await paired();
  const auth = await authenticate(store, "Bearer " + (await createPat(store, account.id, "read")).token);
  const beast = data(await callTool("get_beast", {}, { store, auth })).beast;
  assert.equal(beast.seed_provenance.note, PROVENANCE_NOTE);
  assert.match(beast.seed_provenance.note, /no live quantum link/i);
  assert.equal(beast.seed_provenance.backend, runs[0].backend);
  assert.ok(beast.element && beast.species && beast.stats);
  const care = data(await callTool("get_care_status", {}, { store, auth })).care;
  assert.equal(care.next_stage_at_experience, 40);
  const lost = data(await callTool("get_lost_cosmos_progress", {}, { store, auth })).lost_cosmos;
  assert.equal(lost.field_location, "Pale Shore");
  assert.match(lost.note, /not shared/);
  const moves = data(await callTool("list_moves", {}, { store, auth }));
  assert.ok(moves.moves.length >= 3);
  assert.equal(data(await callTool("delete_everything", {}, { store, auth })).error.code, "unknown_tool");
});

test("revoked, refresh, expired and unpaired tokens are rejected", async () => {
  const { store, account, deviceSecret } = await paired();
  const { client, tokens } = await oauthToken(store, account.id, "care");
  assert.equal(await authenticate(store, "Bearer " + tokens.refresh_token), null);
  const rotated = await exchangeToken(store, { grant_type: "refresh_token", refresh_token: tokens.refresh_token, client_id: client.client_id });
  await assert.rejects(exchangeToken(store, { grant_type: "refresh_token", refresh_token: tokens.refresh_token, client_id: client.client_id }), /invalid/);
  assert.equal(rotated.scope, "beast.read beast.care");
  assert.ok(await authenticate(store, "Bearer " + rotated.access_token));
  await revokeToken(store, rotated.access_token);
  assert.equal(await authenticate(store, "Bearer " + rotated.access_token), null);
  await assert.rejects(exchangeToken(store, { grant_type: "refresh_token", refresh_token: rotated.refresh_token, client_id: client.client_id }), /invalid/);

  const pat = await createPat(store, account.id, "read");
  assert.ok(await authenticate(store, "Bearer " + pat.token, Date.now()));
  assert.equal(await authenticate(store, "Bearer " + pat.token, Date.now() + 200 * 24 * 3600 * 1000), null);
  await revokeById(store, account.id, pat.id);
  assert.equal(await authenticate(store, "Bearer " + pat.token), null);

  const pat2 = await createPat(store, account.id, "care");
  const status = publicStatus(await getAccount(store, account.id));
  assert.doesNotMatch(JSON.stringify(status), /bbm_(pat|at|rt)_|"hash"/);
  await unpairAccount(store, account.id, deviceSecret);
  assert.equal(await authenticate(store, "Bearer " + pat2.token), null);
  assert.equal(await authenticate(store, "Bearer bbm_dev_" + "x".repeat(40)), null);
});

test("each pairing only sees its own beast", async () => {
  const store = createMemoryStore();
  const a = await paired(store);
  const bSnap = minimalSnapshot(exportSession(beastSession("Ember")), { place: "grove" });
  const b = await createAccount(store, { snapshot: bSnap });
  const authA = await authenticate(store, "Bearer " + (await createPat(store, a.account.id, "care")).token);
  const authB = await authenticate(store, "Bearer " + (await createPat(store, b.account.id, "read")).token);
  await callTool("feed_beast", {}, { store, auth: authA });
  assert.equal(data(await callTool("get_beast", {}, { store, auth: authB })).beast.name, "Ember");
  assert.equal(data(await callTool("get_care_status", {}, { store, auth: authB })).care.experience, 0);
});

test("rate limits are per pairing and per category", async () => {
  const store = createMemoryStore();
  const now = 1_700_000_000_000;
  for (let i = 0; i < LIMITS.talk.limit; i++) assert.equal((await rateLimit(store, "talk", "acct1", now)).ok, true);
  const blocked = await rateLimit(store, "talk", "acct1", now);
  assert.equal(blocked.ok, false);
  assert.ok(blocked.retryAfter >= 1 && blocked.retryAfter <= 60);
  assert.equal((await rateLimit(store, "talk", "acct2", now)).ok, true);
  assert.equal((await rateLimit(store, "talk", "acct1", now + 61_000)).ok, true);
  const { store: s2, account } = await paired();
  const auth = await authenticate(s2, "Bearer " + (await createPat(s2, account.id, "care")).token);
  const out = await callTool("feed_beast", {}, { store: s2, auth, limit: async () => ({ ok: false, retryAfter: 12 }) });
  assert.equal(data(out).error.code, "rate_limited");
  assert.equal(data(out).error.retry_after_seconds, 12);
});

test("browser sync acknowledges applied actions and drops actions for another beast", async () => {
  const { store, account } = await paired();
  const auth = await authenticate(store, "Bearer " + (await createPat(store, account.id, "care")).token);
  const fed = data(await callTool("feed_beast", {}, { store, auth }));
  const pending = await syncAccount(store, account.id, null, []);
  assert.equal(pending.actions.length, 1);
  assert.equal(pending.actions[0].id, fed.action.id);
  const local = beastSession();
  local.beast.xp = 6;
  const after = await syncAccount(store, account.id, minimalSnapshot(exportSession(local), { place: "grove" }), [fed.action.id]);
  assert.equal(after.actions.length, 0);
  assert.equal((await getAccount(store, account.id)).snapshot.beast.xp, 6);
  await callTool("feed_beast", {}, { store, auth });
  const other = minimalSnapshot(exportSession(beastSession("Other")), {});
  other.beast.seed = "different-seed";
  assert.equal((await syncAccount(store, account.id, other, [])).actions.length, 0);
});

test("the snapshot is minimal: no chat, memory or sensors, and the server re-picks fields", () => {
  const session = exportSession(beastSession());
  const snap = minimalSnapshot(session, { place: "grove" });
  assert.equal(snap.schema, SNAPSHOT_SCHEMA);
  const text = JSON.stringify(snap);
  assert.doesNotMatch(text, /private chat line|"chat"|"mind"|sensor/);
  const tampered = { ...snap, chat: ["x"], beast: { ...snap.beast, secret: "x" } };
  const clean = validateSnapshot(tampered);
  assert.equal(clean.chat, undefined);
  assert.equal(clean.beast.secret, undefined);
  assert.equal(validateSnapshot({ ...snap, schema: "other" }), null);
  assert.equal(validateSnapshot({ ...snap, pad: "x".repeat(MAX_SNAPSHOT_BYTES) }), null);
});

test("tools are classified Read or Write with factual annotations and no sensitive tool", () => {
  const tools = listTools();
  assert.deepEqual(tools.map((t) => t.name), ["get_beast", "get_care_status", "get_lost_cosmos_progress", "list_moves", "feed_beast", "play_with_beast", "rename_beast", "talk_to_beast"]);
  for (const t of TOOLS) {
    assert.ok(["Read", "Write"].includes(t.classification), t.name);
    assert.equal(t.annotations.readOnlyHint, t.classification === "Read", t.name);
    assert.equal(t.annotations.destructiveHint, false, t.name);
    assert.ok(t.description.length > 40 && t.description.length < 600, t.name);
    assert.doesNotMatch(t.description, /\b(best|amazing|smartest|guaranteed?|sentient)\b/i, t.name);
  }
  for (const t of tools) assert.equal(t.classification, undefined);
  assert.match(TOOLS.find((t) => t.name === "talk_to_beast").description, /not a conscious mind/);
});

test("storage: production without a Redis REST store is reported, never faked", async () => {
  assert.equal(storeFromEnv({ NODE_ENV: "production" }), null);
  const missing = storageStatus({ NODE_ENV: "production" });
  assert.equal(missing.configured, false);
  assert.match(missing.missing[0], /KV_REST_API_URL/);
  assert.equal(missing.options.length, 2);
  assert.deepEqual(missing.options[0].vars, ["KV_REST_API_URL", "KV_REST_API_TOKEN"]);
  assert.deepEqual(missing.options[1].vars, ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"]);
  const partial = storageStatus({ NODE_ENV: "production", KV_REST_API_URL: "https://x" });
  assert.deepEqual(partial.options[0].found, ["KV_REST_API_URL"]);
  assert.deepEqual(partial.options[0].missing, ["KV_REST_API_TOKEN"]);
  const configured = storageStatus({ NODE_ENV: "production", KV_REST_API_URL: "https://x", KV_REST_API_TOKEN: "t" });
  assert.equal(configured.kind, "redis-rest");
  assert.equal(configured.lookingFor, "Vercel KV / Marketplace Redis");
  const calls = [];
  const fake = async (url, init) => { calls.push({ url, body: JSON.parse(init.body), auth: init.headers.Authorization }); return new Response(JSON.stringify([{ result: JSON.stringify({ a: 1 }) }])); };
  const store = createRedisRestStore({ url: "https://kv.example/", token: "tok", fetchImpl: fake });
  assert.deepEqual(await store.get("k"), { a: 1 });
  await store.set("k", { a: 2 }, 60);
  assert.equal(calls[0].url, "https://kv.example/pipeline");
  assert.deepEqual(calls[1].body[0], ["SET", "k", "{\"a\":2}", "EX", "60"]);
});

test("the companion bridge is only used when configured and its replies are verified", async () => {
  assert.equal(createBridgeTalk("a", {}), null);
  const env = { BEASTBOX_CLOUD_BRIDGE_URL: "https://bridge.example", BEASTBOX_CLOUD_BRIDGE_TOKEN: "t", BEASTBOX_CLOUD_AUTH_SECRET: "s".repeat(40) };
  let sent;
  const good = createBridgeTalk("acct", env, async (url, init) => { sent = { url: String(url), body: JSON.parse(init.body) }; return new Response(JSON.stringify({ schema: "beastbox-guest-local-v1", model: "rawrphos-native", memory_used: false, owner_tools_used: false, reply: "rawr" })); });
  assert.deepEqual(await good("hi"), { reply: "rawr", model: "rawrphos-native" });
  assert.equal(sent.url, "https://bridge.example/api/guest-local");
  assert.match(sent.body.guest_identity, /^[a-f0-9]{64}$/);
  const bad = createBridgeTalk("acct", env, async () => new Response(JSON.stringify({ schema: "x", reply: "made up" })));
  assert.equal((await bad("hi")).reply, "");
});

test("UI is additive: owner deck keeps LOST COSMOS and adds META MUSE; GO menu and settings open the panel", () => {
  const studio = read("components/studio.tsx");
  assert.match(studio, /LOST COSMOS<\/Link><Link className="nav-item" href="\/beast-cage\/go#meta-muse"/);
  const go = read("components/beast-go.tsx");
  assert.match(go, /data-meta-muse-entry="menu"/);
  assert.match(go, /data-meta-muse-entry="settings"/);
  assert.match(go, /sheet === 'metamuse' \? <MetaMusePanel \/>/);
  const panel = read("components/meta-muse-panel.tsx");
  assert.match(panel, /only after Meta reviews and approves them/);
  assert.match(panel, /Muse Connector Platform/);
  assert.match(panel, /Unpair/);
  assert.match(panel, /Vercel dashboard/);
  assert.match(panel, /the-beast-box/);
  assert.match(panel, /Storage/);
  assert.match(panel, /KV_REST_API_URL/);
  assert.match(panel, /UPSTASH_REDIS_REST_URL/);
  assert.match(panel, /Recheck storage/);
  assert.match(panel, /Not paired\. Nothing leaves this browser\./);
  assert.match(panel, /storage\.working === true/);
  const museRoute = read("app/api/muse/[action]/route.ts");
  assert.match(museRoute, /storageHealthPayload/);
  assert.match(museRoute, /await store\.set/);
  assert.match(museRoute, /await store\.get/);
  assert.match(museRoute, /await store\.del/);
  assert.match(read("components/companion-provider.tsx"), /<MetaMuseSync \/>/);
});

test("discovery: the server card follows the MCP Server Card v1 shape and points at /api/mcp and its OAuth", () => {
  const card = serverCard("https://beast.example");
  assert.equal(card.$schema, SERVER_CARD_SCHEMA);
  assert.match(card.name, /^[a-zA-Z0-9.-]+\/[a-zA-Z0-9._-]+$/);
  assert.ok(card.description.length >= 1 && card.description.length <= 100);
  assert.ok(card.title.length <= 100);
  assert.doesNotMatch(card.version, /[\^~><*x]/);
  assert.equal(card.remotes[0].type, "streamable-http");
  assert.equal(card.remotes[0].url, "https://beast.example/api/mcp");
  assert.equal(card.remotes[0].headers[0].isSecret, true);
  assert.ok(card.remotes[0].supportedProtocolVersions.includes("2025-06-18"));
  assert.deepEqual(card.remotes[0].supportedProtocolVersions, PROTOCOL_VERSIONS);
  const meta = card._meta["io.github.navisworld/beastbox"];
  assert.equal(meta.authorization.protectedResourceMetadata, "https://beast.example/.well-known/oauth-protected-resource/api/mcp");
  assert.equal(meta.authorization.dynamicClientRegistration, "https://beast.example/api/muse/oauth/register");
  assert.deepEqual(meta.toolClasses.sensitiveWrite, []);
  assert.equal(meta.device, null);
  assert.doesNotMatch(JSON.stringify(card), /bbm_(dev|at|pat|rt)_[A-Za-z0-9]/);
  const named = serverCard("https://beast.example", { deviceId: "bbd_" + "1".repeat(20), deviceName: "Beast Box · Moss" });
  assert.equal(named.title, "Beast Box · Moss");
  assert.equal(named._meta["io.github.navisworld/beastbox"].device.name, "Beast Box · Moss");
  const cat = aiCatalog("https://beast.example");
  assert.equal(cat.specVersion, "1.0");
  assert.equal(cat.entries[0].type, SERVER_CARD_TYPE);
  assert.equal(cat.entries[0].url, serverCardUrl("https://beast.example"));
  assert.equal(cat.entries[0].identifier, "urn:air:beast.example:mcp:beastbox");
});

test("discovery: Meta Muse device pairing is listed as unavailable, never faked", () => {
  const muse = PAIRING_METHODS.find((m) => m.id === "meta-muse-device-pairing");
  assert.equal(muse.available, false);
  assert.match(muse.how, /no public API/);
  assert.deepEqual(PAIRING_METHODS.filter((m) => m.available).map((m) => m.id), ["mcp-oauth", "muse-code-token"]);
});

test("one-tap pairing link keeps the code in the #fragment and parsing rejects junk", () => {
  const link = pairingLink("https://beast.example", { code: "ABCD-2345", deviceId: "bbd_" + "a".repeat(20) });
  const url = new URL(link);
  assert.equal(url.pathname, "/connect/meta-muse/pair");
  assert.equal(url.search, "");
  assert.deepEqual(parsePairingFragment(url.hash), { connector: "https://beast.example/api/mcp", code: "ABCD-2345", device: "bbd_" + "a".repeat(20) });
  assert.deepEqual(parsePairingFragment("#connector=javascript:alert(1)&code=<x>&device=../../"), { connector: "", code: "", device: "" });
  assert.equal(parsePairingFragment("#connector=https%3A%2F%2Fevil.example%2Fother").connector, "");
});

test("device name: defaults to 'Beast Box · <beast name>', is editable, and is the only thing the public card lookup returns", async () => {
  const { store, account, deviceSecret } = await paired();
  assert.equal(account.deviceName, defaultDeviceName("Moss"));
  assert.equal(account.deviceName, "Beast Box · Moss");
  assert.match(account.deviceId, /^bbd_[a-f0-9]{20}$/);
  assert.deepEqual(await deviceById(store, account.deviceId), { deviceId: account.deviceId, deviceName: "Beast Box · Moss" });
  await setDeviceName(store, account.id, "  Cory's   <b>Beast</b> ");
  assert.equal((await deviceById(store, account.deviceId)).deviceName, "Cory's bBeastb");
  await assert.rejects(setDeviceName(store, account.id, "<<>>"), /Device name/);
  assert.equal(await deviceById(store, "bbd_" + "0".repeat(20)), null);
  assert.equal(await deviceById(store, account.id), null);
  await unpairAccount(store, account.id, deviceSecret);
  assert.equal(await deviceById(store, account.deviceId), null);
});

test("dynamic client registration (RFC 7591): public clients, safe redirect URIs, sanitized names", async () => {
  const store = createMemoryStore();
  const c = await registerClient(store, { client_name: "Meta <Muse>", redirect_uris: ["https://muse.example/cb", "http://localhost:4000/cb"] });
  assert.match(c.client_id, /^bbm_client_[a-f0-9]{24}$/);
  assert.equal(c.client_name, "Meta Muse");
  assert.equal(c.token_endpoint_auth_method, "none");
  assert.deepEqual(c.grant_types, ["authorization_code", "refresh_token"]);
  assert.equal(c.client_secret, undefined);
  for (const bad of [[], ["ftp://x/cb"], ["https://x/cb#frag"], ["http://192.168.1.4/cb"], Array(6).fill("https://x/cb"), ["not a url"]]) {
    await assert.rejects(registerClient(store, { redirect_uris: bad }), /redirect_uris/, JSON.stringify(bad));
  }
  assert.equal((await registerClient(store, { redirect_uris: ["https://x/cb"] })).client_name, "MCP client");
});
