/**
 * talk_to_beast backend: the same guest-safe RAWRPHØS host that /api/guest uses.
 * No owner Brain Bay memory, no owner tools, no provider keys. Returns null when the
 * host is not configured so the tool can say so instead of inventing a reply.
 */
import { createHmac } from "node:crypto";

function validHost(value) {
  try {
    const u = new URL(value);
    return u.protocol === "https:" && !u.username && !u.password && !u.hash && !u.search &&
      !["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(u.hostname) && !u.hostname.endsWith(".local");
  } catch { return false; }
}

export function createBridgeTalk(accountId, env = process.env, fetchImpl = fetch) {
  const url = env.BEASTBOX_CLOUD_BRIDGE_URL, token = env.BEASTBOX_CLOUD_BRIDGE_TOKEN, secret = env.BEASTBOX_CLOUD_AUTH_SECRET;
  if (!url || !token || !validHost(url) || !secret || secret.length < 32) return null;
  // Opaque per-pairing quota bucket for the guest host. Grants nothing.
  const identity = createHmac("sha256", secret).update("meta-muse:" + accountId).digest("hex");
  return async (prompt) => {
    try {
      const res = await fetchImpl(new URL("/api/guest-local", url), {
        method: "POST", redirect: "error", cache: "no-store",
        headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
        body: JSON.stringify({ text: String(prompt).slice(0, 700), guest_identity: identity }),
        signal: AbortSignal.timeout(45_000),
      });
      const text = await res.text();
      if (text.length > 16000) return { reply: "", error: "The game companion host sent an oversized reply. Nothing was saved." };
      const result = JSON.parse(text);
      if (!res.ok) return { reply: "", error: res.status === 429 ? "The game companion host is rate limited. Try again later." : "The game companion host is unavailable. Nothing was saved." };
      if (result.schema !== "beastbox-guest-local-v1" || result.model !== "rawrphos-native" || result.memory_used !== false ||
          result.owner_tools_used !== false || typeof result.reply !== "string" || result.reply.length > 6000) {
        return { reply: "", error: "The game companion host sent an unverified reply. Nothing was saved." };
      }
      return { reply: result.reply.trim(), model: "rawrphos-native" };
    } catch {
      return { reply: "", error: "The game companion host did not answer in time. Nothing was saved." };
    }
  };
}
