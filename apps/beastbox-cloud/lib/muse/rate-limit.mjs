/** Fixed-window rate limits. Keys are hashes, never raw tokens. */
export const LIMITS = {
  mcp: { limit: 120, windowSec: 60 },
  read: { limit: 60, windowSec: 60 },
  write: { limit: 20, windowSec: 60 },
  talk: { limit: 6, windowSec: 60 },
  link: { limit: 10, windowSec: 3600 },
  oauth: { limit: 30, windowSec: 60 },
  sync: { limit: 30, windowSec: 60 },
};

export async function rateLimit(store, bucket, id, now = Date.now()) {
  const rule = LIMITS[bucket];
  if (!rule) throw new Error("unknown rate limit bucket");
  const window = Math.floor(now / 1000 / rule.windowSec);
  const count = await store.incr(`rl:${bucket}:${id}:${window}`, rule.windowSec + 5);
  const resetAt = (window + 1) * rule.windowSec;
  return {
    ok: count <= rule.limit,
    limit: rule.limit,
    remaining: Math.max(0, rule.limit - count),
    retryAfter: Math.max(1, Math.ceil(resetAt - now / 1000)),
  };
}
