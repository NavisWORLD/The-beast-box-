/**
 * End-to-end: the official MCP SDK client over Streamable HTTP against a running Beast Box.
 * Skipped unless BEASTBOX_E2E_URL is set, e.g.
 *   BEASTBOX_E2E_URL=http://localhost:3100 node --test tests/meta-muse-e2e.test.mjs
 */
import assert from "node:assert/strict";
import test from "node:test";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import runs from "../lib/companion/spark/runs.json" with { type: "json" };
import { adoptBeast, createSession, exportSession } from "../lib/companion/session.mjs";
import { minimalSnapshot } from "../lib/muse/snapshot.mjs";
import { pkceChallenge } from "../lib/muse/auth.mjs";

const BASE = process.env.BEASTBOX_E2E_URL;
const skip = BASE ? false : "set BEASTBOX_E2E_URL to run against a dev server";

async function device(path, { method = "POST", secret, body } = {}) {
  const res = await fetch(BASE + "/api/muse/" + path, {
    method, headers: { Origin: BASE, "Content-Type": "application/json", ...(secret ? { Authorization: "Bearer " + secret } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { status: res.status, data: await res.json() };
}
async function mcp(token) {
  const client = new Client({ name: "beastbox-e2e", version: "1.0.0" });
  await client.connect(new StreamableHTTPClientTransport(new URL(BASE + "/api/mcp"), { requestInit: { headers: { Authorization: "Bearer " + token } } }));
  return client;
}
const payload = (result) => result.structuredContent || JSON.parse(result.content[0].text);

test("MCP SDK client: initialize, list tools, read, and read-only vs care writes", { skip }, async () => {
  const session = createSession();
  adoptBeast(session, buildGenome({ focus: 40, calm: 40, spark: 20 }, runs[0], null), "Moss");
  const link = await device("link", { body: { consent: "share-beast-snapshot", snapshot: minimalSnapshot(exportSession(session), { place: "grove" }) } });
  assert.equal(link.status, 201, JSON.stringify(link.data));
  const secret = link.data.deviceSecret;

  const unauth = await fetch(BASE + "/api/mcp", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: "{}" });
  assert.equal(unauth.status, 401);
  assert.match(unauth.headers.get("www-authenticate"), /resource_metadata=".*\/\.well-known\/oauth-protected-resource\/api\/mcp"/);

  const readPat = (await device("pat", { secret, body: { access: "read" } })).data.token;
  const reader = await mcp(readPat);
  assert.equal(reader.getServerVersion().name, "beastbox");
  const { tools } = await reader.listTools();
  assert.equal(tools.length, 8);
  assert.equal(tools.find((t) => t.name === "get_beast").annotations.readOnlyHint, true);
  assert.equal(tools.find((t) => t.name === "feed_beast").annotations.readOnlyHint, false);
  const beast = payload(await reader.callTool({ name: "get_beast", arguments: {} }));
  assert.equal(beast.beast.name, "Moss");
  assert.match(beast.beast.seed_provenance.note, /no live quantum link/i);
  const blocked = await reader.callTool({ name: "feed_beast", arguments: {} });
  assert.equal(blocked.isError, true);
  assert.equal(payload(blocked).error.code, "insufficient_scope");
  await reader.close();

  const carePat = (await device("pat", { secret, body: { access: "care" } })).data.token;
  const carer = await mcp(carePat);
  const fed = await carer.callTool({ name: "feed_beast", arguments: {} });
  assert.equal(fed.isError, undefined);
  assert.equal(payload(fed).care.experience, 6);
  await carer.close();

  const sync = await device("sync", { secret, body: { ack: [] } });
  assert.equal(sync.data.actions[0].type, "feed");
  assert.equal(sync.data.status.lastActivity.tool, "feed_beast");
  assert.equal((await device("link", { method: "DELETE", secret })).status, 200);
  const gone = await fetch(BASE + "/api/mcp", { method: "POST", headers: { Authorization: "Bearer " + carePat, "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }) });
  assert.equal(gone.status, 401);
});

test("OAuth 2.1: metadata, dynamic registration, consent with pairing code, PKCE token, read-only grant, revocation", { skip }, async () => {
  const prm = await (await fetch(BASE + "/.well-known/oauth-protected-resource/api/mcp")).json();
  assert.equal(prm.resource, BASE + "/api/mcp");
  const as = await (await fetch(prm.authorization_servers[0] + "/.well-known/oauth-authorization-server")).json();
  assert.deepEqual(as.code_challenge_methods_supported, ["S256"]);
  const reg = await (await fetch(as.registration_endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_name: "E2E Muse", redirect_uris: ["http://127.0.0.1:7777/cb"] }) })).json();
  const session = createSession();
  adoptBeast(session, buildGenome({ focus: 40, calm: 40, spark: 20 }, runs[1], null), "Ember");
  const { data: link } = await device("link", { body: { consent: "share-beast-snapshot", snapshot: minimalSnapshot(exportSession(session), {}) } });
  const { data: pair } = await device("code", { secret: link.deviceSecret, body: {} });
  const verifier = "e2e-verifier-" + "x".repeat(40);
  const q = { client_id: reg.client_id, redirect_uri: "http://127.0.0.1:7777/cb", response_type: "code", code_challenge: pkceChallenge(verifier), code_challenge_method: "S256", state: "s123", scope: "beast.read beast.care", resource: prm.resource };
  const page = await fetch(as.authorization_endpoint + "?" + new URLSearchParams(q));
  const html = await page.text();
  assert.match(html, /Read only/);
  assert.match(html, /Read \+ care actions/);
  const form = new URLSearchParams({ ...q, pairing_code: pair.code, access: "read", decision: "allow" });
  const consent = await fetch(BASE + "/api/muse/oauth/authorize", { method: "POST", redirect: "manual", headers: { Origin: BASE, "Content-Type": "application/x-www-form-urlencoded" }, body: form });
  assert.equal(consent.status, 303);
  const back = new URL(consent.headers.get("location"));
  assert.equal(back.searchParams.get("state"), "s123");
  const reuse = await fetch(BASE + "/api/muse/oauth/authorize", { method: "POST", redirect: "manual", headers: { Origin: BASE, "Content-Type": "application/x-www-form-urlencoded" }, body: form });
  assert.match(reuse.headers.get("location"), /pair_error=1/);
  const tok = await (await fetch(as.token_endpoint, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ grant_type: "authorization_code", code: back.searchParams.get("code"), client_id: reg.client_id, redirect_uri: q.redirect_uri, code_verifier: verifier, resource: prm.resource }) })).json();
  assert.equal(tok.scope, "beast.read");
  const client = await mcp(tok.access_token);
  assert.equal(payload(await client.callTool({ name: "get_beast", arguments: {} })).beast.name, "Ember");
  assert.equal(payload(await client.callTool({ name: "rename_beast", arguments: { name: "Nope" } })).error.code, "insufficient_scope");
  await client.close();
  await fetch(as.revocation_endpoint, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ token: tok.access_token }) });
  const revoked = await fetch(BASE + "/api/mcp", { method: "POST", headers: { Authorization: "Bearer " + tok.access_token, "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }) });
  assert.equal(revoked.status, 401);
  await device("link", { method: "DELETE", secret: link.deviceSecret });
});

test("discovery from the base URL alone: AI catalog -> server card -> /api/mcp -> OAuth metadata -> dynamic registration", { skip }, async () => {
  const catRes = await fetch(BASE + "/.well-known/ai-catalog.json");
  assert.equal(catRes.status, 200);
  assert.match(catRes.headers.get("content-type"), /application\/ai-catalog\+json/);
  assert.equal(catRes.headers.get("access-control-allow-origin"), "*");
  const catalog = await catRes.json();
  const entry = catalog.entries.find((e) => e.type === "application/mcp-server-card+json");
  const cardRes = await fetch(entry.url, { headers: { Accept: "application/mcp-server-card+json" } });
  assert.match(cardRes.headers.get("content-type"), /application\/mcp-server-card\+json/);
  const etag = cardRes.headers.get("etag");
  const card = await cardRes.json();
  assert.equal((await fetch(entry.url, { headers: { "If-None-Match": etag } })).status, 304);
  for (const alias of ["/.well-known/mcp.json", "/.well-known/mcp-server-card"]) assert.deepEqual(await (await fetch(BASE + alias)).json(), card, alias);
  assert.deepEqual(await (await fetch(BASE + "/.well-known/mcp/catalog.json")).json(), catalog);
  const remote = card.remotes.find((r) => r.type === "streamable-http");
  assert.equal(remote.url, BASE + "/api/mcp");

  const probe = await fetch(remote.url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} }) });
  assert.equal(probe.status, 401);
  const prmUrl = /resource_metadata="([^"]+)"/.exec(probe.headers.get("www-authenticate"))[1];
  const prm = await (await fetch(prmUrl)).json();
  assert.equal(prm.resource, remote.url);
  assert.deepEqual(await (await fetch(BASE + "/.well-known/oauth-protected-resource")).json(), prm);
  const as = await (await fetch(prm.authorization_servers[0] + "/.well-known/oauth-authorization-server")).json();
  assert.equal(as.issuer, BASE);
  assert.ok(as.registration_endpoint);

  const reg = await fetch(as.registration_endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_name: "Discovery E2E", redirect_uris: ["https://client.example/cb"], token_endpoint_auth_method: "none" }) });
  assert.equal(reg.status, 201);
  const client = await reg.json();
  assert.match(client.client_id, /^bbm_client_/);
  assert.equal(client.client_secret, undefined);
  const bad = await fetch(as.registration_endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ redirect_uris: ["http://evil.example/cb"] }) });
  assert.equal(bad.status, 400);
  assert.equal((await bad.json()).error, "invalid_redirect_uri");
});

test("device name appears in the per-device server card and as the MCP server title", { skip }, async () => {
  const session = createSession();
  adoptBeast(session, buildGenome({ focus: 40, calm: 40, spark: 20 }, runs[2], null), "Pip");
  const { data: link } = await device("link", { body: { consent: "share-beast-snapshot", snapshot: minimalSnapshot(exportSession(session), {}) } });
  assert.equal(link.deviceName, "Beast Box · Pip");
  const renamed = await device("device", { secret: link.deviceSecret, body: { name: "Cory's Beast Box" } });
  assert.equal(renamed.data.deviceName, "Cory's Beast Box");
  const card = await (await fetch(link.serverCardUrl)).json();
  assert.equal(card.title, "Cory's Beast Box");
  assert.equal(card._meta["io.github.navisworld/beastbox"].device.id, link.deviceId);
  assert.equal((await fetch(BASE + "/api/mcp/server-card?device=bbd_" + "0".repeat(20))).status, 404);
  const { data: pair } = await device("code", { secret: link.deviceSecret, body: {} });
  const one = new URL(pair.link);
  assert.equal(one.search, "");
  assert.match(one.hash, new RegExp("code=" + pair.code));
  const pat = (await device("pat", { secret: link.deviceSecret, body: { access: "read" } })).data.token;
  const client = await mcp(pat);
  assert.equal(client.getServerVersion().title, "Cory's Beast Box");
  await client.close();
  await device("link", { method: "DELETE", secret: link.deviceSecret });
  assert.equal((await fetch(link.serverCardUrl)).status, 404);
});

test("the MCP SDK's own OAuth discovery and RFC 7591 registration work against Beast Box", { skip }, async () => {
  const { discoverOAuthServerInfo, registerClient } = await import("@modelcontextprotocol/sdk/client/auth.js");
  const info = await discoverOAuthServerInfo(BASE + "/api/mcp");
  assert.equal(info.authorizationServerUrl.replace(/\/$/, ""), BASE);
  assert.equal(info.resourceMetadata.resource, BASE + "/api/mcp");
  assert.deepEqual(info.authorizationServerMetadata.code_challenge_methods_supported, ["S256"]);
  const client = await registerClient(info.authorizationServerUrl, { metadata: info.authorizationServerMetadata, clientMetadata: { client_name: "SDK DCR", redirect_uris: ["http://127.0.0.1:9999/cb"], grant_types: ["authorization_code", "refresh_token"], response_types: ["code"], token_endpoint_auth_method: "none" } });
  assert.match(client.client_id, /^bbm_client_/);
});
