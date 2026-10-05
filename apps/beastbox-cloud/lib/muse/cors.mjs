/**
 * CORS for the browser pairing and sync routes (/api/muse/storage, link, code, sync, device).
 *
 * The Beast Box page calls these same-origin. A small allow-list of other origins may also
 * call them so a beast that lives on another page (the Lost Cosmos Spark Beasts page on
 * GitHub Pages) can pair and sync with the same connector. The device secret travels in the
 * Authorization header; no cookies are involved, so credentials are never allowed.
 *
 * Token routes (pat, grant), OAuth and /api/mcp are not covered: they stay same-origin or
 * keep their own rules.
 */
export const MUSE_CORS_ORIGINS = Object.freeze(["https://navisworld.github.io"]);
export const MUSE_CORS_ACTIONS = Object.freeze(["storage", "link", "code", "sync", "device"]);
export const MUSE_CORS_METHODS = "GET, POST, DELETE, OPTIONS";
export const MUSE_CORS_HEADERS = "Authorization, Content-Type";

const LOCAL_DEV = /^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$/;

/**
 * The origin to echo back, or "" when this origin/action is not allowed.
 * Local http origins are allowed only outside production (next dev, tests).
 */
export function corsOrigin(origin, action, env = process.env) {
  const o = String(origin || "");
  if (!o || !MUSE_CORS_ACTIONS.includes(String(action || ""))) return "";
  if (MUSE_CORS_ORIGINS.includes(o)) return o;
  if (env.NODE_ENV !== "production" && LOCAL_DEV.test(o)) return o;
  return "";
}

/** Headers for an allowed cross-origin response (empty object when not allowed). */
export function corsHeaders(origin, action, env = process.env) {
  const allowed = corsOrigin(origin, action, env);
  if (!allowed) return {};
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": MUSE_CORS_METHODS,
    "Access-Control-Allow-Headers": MUSE_CORS_HEADERS,
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

/** Add CORS headers to a Response in place (no-op for same-origin or foreign origins). */
export function withCors(request, action, response, env = process.env) {
  const headers = corsHeaders(request.headers.get("origin"), action, env);
  for (const [k, v] of Object.entries(headers)) response.headers.set(k, v);
  return response;
}

/**
 * OPTIONS preflight. Allowed origin + action: 204 with CORS headers. Otherwise 204 with only
 * `Allow`, which is what Next.js answered before, so a foreign origin's preflight still fails.
 */
export function preflight(request, action, env = process.env) {
  const headers = { Allow: "DELETE, GET, HEAD, OPTIONS, POST", "Cache-Control": "no-store", ...corsHeaders(request.headers.get("origin"), action, env) };
  return new Response(null, { status: 204, headers });
}
