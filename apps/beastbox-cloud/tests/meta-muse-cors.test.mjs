import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { corsHeaders, corsOrigin, MUSE_CORS_ACTIONS, MUSE_CORS_ORIGINS, preflight, withCors } from "../lib/muse/cors.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const PROD = { NODE_ENV: "production" };
const DEV = { NODE_ENV: "development" };
const PAGES = "https://navisworld.github.io";
const req = (origin, method = "POST") => new Request("https://www.beastboxcosmos.xyz/api/muse/sync", { method, headers: origin ? { Origin: origin } : {} });

test("CORS allow-list: only GitHub Pages (navisworld.github.io) in production, exact match", () => {
  assert.deepEqual([...MUSE_CORS_ORIGINS], [PAGES]);
  for (const action of ["storage", "link", "code", "sync", "device"]) assert.equal(corsOrigin(PAGES, action, PROD), PAGES);
  for (const bad of ["https://evil.github.io", "http://navisworld.github.io", "https://navisworld.github.io.evil.com", "https://navisworld.github.io/", "null", "", undefined]) {
    assert.equal(corsOrigin(bad, "sync", PROD), "", String(bad));
  }
  assert.equal(corsOrigin("http://localhost:8080", "sync", PROD), "", "no localhost in production");
  assert.equal(corsOrigin("http://127.0.0.1:8099", "sync", DEV), "http://127.0.0.1:8099", "localhost allowed in dev");
  assert.equal(corsOrigin("http://localhost:8099.evil.com", "sync", DEV), "");
});

test("CORS covers only the pairing and sync routes, not tokens, grants, OAuth or /api/mcp", () => {
  assert.deepEqual([...MUSE_CORS_ACTIONS], ["storage", "link", "code", "sync", "device"]);
  for (const action of ["pat", "grant", "oauth", "mcp", "", "../pat"]) assert.equal(corsOrigin(PAGES, action, PROD), "", action);
});

test("CORS headers: echo the one origin, Vary: Origin, bearer header allowed, never credentials", () => {
  const h = corsHeaders(PAGES, "link", PROD);
  assert.equal(h["Access-Control-Allow-Origin"], PAGES);
  assert.equal(h.Vary, "Origin");
  assert.match(h["Access-Control-Allow-Methods"], /POST/);
  assert.match(h["Access-Control-Allow-Methods"], /DELETE/);
  assert.match(h["Access-Control-Allow-Headers"], /Authorization/);
  assert.match(h["Access-Control-Allow-Headers"], /Content-Type/);
  assert.equal(h["Access-Control-Allow-Credentials"], undefined);
  assert.deepEqual(corsHeaders("https://evil.example", "link", PROD), {});
});

test("withCors decorates allowed responses (including 503 storage_not_configured) and leaves others untouched", async () => {
  const res = withCors(req(PAGES), "link", Response.json({ error: "storage_not_configured" }, { status: 503, headers: { "Cache-Control": "no-store" } }), PROD);
  assert.equal(res.status, 503);
  assert.equal(res.headers.get("access-control-allow-origin"), PAGES);
  assert.equal(res.headers.get("cache-control"), "no-store");
  assert.equal((await res.json()).error, "storage_not_configured");
  const same = withCors(req(null), "link", Response.json({ ok: true }), PROD);
  assert.equal(same.headers.get("access-control-allow-origin"), null);
  const foreign = withCors(req("https://evil.example"), "sync", Response.json({ error: "same_origin_required" }, { status: 403 }), PROD);
  assert.equal(foreign.headers.get("access-control-allow-origin"), null);
  assert.equal(foreign.status, 403);
  const pat = withCors(req(PAGES), "pat", Response.json({}), PROD);
  assert.equal(pat.headers.get("access-control-allow-origin"), null);
});

test("OPTIONS preflight: 204 with CORS for allowed origin, 204 with only Allow otherwise", () => {
  const ok = preflight(req(PAGES, "OPTIONS"), "sync", PROD);
  assert.equal(ok.status, 204);
  assert.equal(ok.headers.get("access-control-allow-origin"), PAGES);
  assert.match(ok.headers.get("access-control-allow-headers"), /Authorization/);
  assert.equal(ok.headers.get("access-control-max-age"), "600");
  assert.match(ok.headers.get("allow"), /OPTIONS/);
  const no = preflight(req("https://evil.example", "OPTIONS"), "sync", PROD);
  assert.equal(no.status, 204);
  assert.equal(no.headers.get("access-control-allow-origin"), null);
  assert.match(no.headers.get("allow"), /POST/);
  assert.equal(preflight(req(PAGES, "OPTIONS"), "pat", PROD).headers.get("access-control-allow-origin"), null);
});

test("route wiring: allow-listed origins pass the origin check per action; every method and OPTIONS carry CORS", () => {
  const route = read("app/api/muse/[action]/route.ts");
  assert.match(route, /from '@\/lib\/muse\/cors\.mjs'/);
  assert.match(route, /sameOrigin\(request\) \|\| !!corsOrigin\(request\.headers\.get\('origin'\), action\)/);
  assert.doesNotMatch(route, /if \(!sameOrigin\(request\)\)/, "no bare same-origin check left that would block the allow-list");
  for (const m of ["GET", "POST", "DELETE"]) assert.match(route, new RegExp(`export async function ${m}\\(request: Request, ctx: Ctx\\) \\{\\n  const \\{ action \\} = await ctx\\.params;\\n  return withCors\\(request, action,`), m);
  assert.match(route, /export async function OPTIONS\(request: Request, ctx: Ctx\) \{[\s\S]*?return preflight\(request, action\);/);
  // pat and grant still go through device(), whose corsOrigin() check rejects those actions.
  assert.match(route, /action === 'pat'/);
  assert.match(route, /action === 'grant'/);
});

test("MCP endpoint and OAuth keep their own origin rules (unchanged by this CORS)", () => {
  assert.doesNotMatch(read("app/api/mcp/route.ts"), /cors\.mjs/);
  assert.doesNotMatch(read("app/api/muse/oauth/[step]/route.ts"), /cors\.mjs/);
});
