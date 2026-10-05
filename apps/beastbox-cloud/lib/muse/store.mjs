/**
 * Server storage for the Meta Muse connector.
 *
 * Production needs a Redis REST store (Vercel Marketplace "Upstash for Redis" sets
 * KV_REST_API_URL / KV_REST_API_TOKEN; plain Upstash uses UPSTASH_REDIS_REST_URL /
 * UPSTASH_REDIS_REST_TOKEN). Without one the connector answers 503 and says so.
 * An in-memory store exists only for tests and `next dev`; it is never used in production.
 */

export const STORE_ENV = [
  ["KV_REST_API_URL", "KV_REST_API_TOKEN"],
  ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"],
];

export const STORE_OPTIONS = [
  { id: "vercel-kv", label: "Vercel KV / Marketplace Redis", vars: STORE_ENV[0] },
  { id: "upstash-redis-rest", label: "Upstash Redis REST", vars: STORE_ENV[1] },
];

export function createMemoryStore(now = () => Date.now()) {
  const map = new Map();
  const live = (key) => {
    const item = map.get(key);
    if (!item) return null;
    if (item.exp && item.exp <= now()) { map.delete(key); return null; }
    return item;
  };
  return {
    kind: "memory",
    async get(key) { const item = live(key); return item ? JSON.parse(item.value) : null; },
    async set(key, value, ttlSec = 0) { map.set(key, { value: JSON.stringify(value), exp: ttlSec ? now() + ttlSec * 1000 : 0 }); },
    async del(key) { map.delete(key); },
    async incr(key, ttlSec) {
      const item = live(key);
      const next = (item ? Number(JSON.parse(item.value)) : 0) + 1;
      map.set(key, { value: JSON.stringify(next), exp: item?.exp || (ttlSec ? now() + ttlSec * 1000 : 0) });
      return next;
    },
    size() { return map.size; },
  };
}

/** Upstash-compatible Redis REST client (no SDK). Values are JSON strings. */
export function createRedisRestStore({ url, token, fetchImpl = fetch }) {
  const base = String(url).replace(/\/+$/, "");
  async function pipeline(commands) {
    const res = await fetchImpl(base + "/pipeline", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify(commands),
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error("storage request failed (" + res.status + ")");
    const out = await res.json();
    if (!Array.isArray(out)) throw new Error("storage returned an invalid response");
    for (const item of out) if (item && item.error) throw new Error("storage command failed");
    return out.map((item) => item && item.result);
  }
  return {
    kind: "redis-rest",
    async get(key) { const [raw] = await pipeline([["GET", key]]); return raw == null ? null : JSON.parse(raw); },
    async set(key, value, ttlSec = 0) {
      await pipeline([ttlSec ? ["SET", key, JSON.stringify(value), "EX", String(Math.ceil(ttlSec))] : ["SET", key, JSON.stringify(value)]]);
    },
    async del(key) { await pipeline([["DEL", key]]); },
    async incr(key, ttlSec) {
      const [count] = await pipeline([["INCR", key], ["EXPIRE", key, String(Math.ceil(ttlSec)), "NX"]]);
      return Number(count);
    },
  };
}

/** Which storage is configured. Only variable names are reported, never values. */
export function storageStatus(env = process.env) {
  const options = STORE_OPTIONS.map((option) => {
    const vars = [...option.vars];
    const found = vars.filter((name) => Boolean(env[name]));
    const missing = vars.filter((name) => !env[name]);
    return { id: option.id, label: option.label, vars, found, missing, complete: missing.length === 0 };
  });
  const active = options.find((option) => option.complete);
  if (active) return {
    configured: true, kind: "redis-rest", via: active.id, lookingFor: active.label,
    found: active.found, missing: [], options,
  };
  if (env.NODE_ENV !== "production") return {
    configured: true, kind: "memory-dev", via: "next dev / tests only", lookingFor: "Development memory store",
    found: [], missing: [], options,
  };
  const ranked = [...options].sort((a, b) => b.found.length - a.found.length);
  return {
    configured: false, kind: "none", via: "", lookingFor: ranked[0]?.found.length ? ranked[0].label : "Vercel KV or Upstash Redis REST",
    found: options.flatMap((option) => option.found),
    missing: options.flatMap((option) => option.missing),
    options,
  };
}

/** The store for this deployment, or null when production storage is missing. */
export function storeFromEnv(env = process.env) {
  for (const [u, t] of STORE_ENV) {
    if (env[u] && env[t]) return createRedisRestStore({ url: env[u], token: env[t] });
  }
  if (env.NODE_ENV === "production") return null;
  const g = globalThis;
  if (!g.__beastboxMuseDevStore) g.__beastboxMuseDevStore = createMemoryStore();
  return g.__beastboxMuseDevStore;
}
