/** Browser-safe helpers for the Pair panel QR code / one-tap link (no server imports). */
const mcpUrlOf = (origin) => origin + "/api/mcp";

/**
 * One-tap pairing link. The pairing code rides in the URL fragment so it is never sent
 * to a server or written to request logs; the landing page reads it in the browser.
 */
export function pairingLink(origin, { code = "", deviceId = "" } = {}) {
  const frag = new URLSearchParams({ connector: mcpUrlOf(origin) });
  if (code) frag.set("code", code);
  if (deviceId) frag.set("device", deviceId);
  return origin + "/connect/meta-muse/pair#" + frag.toString();
}
export function parsePairingFragment(hash) {
  const p = new URLSearchParams(String(hash || "").replace(/^#/, ""));
  const connector = p.get("connector") || "";
  let ok = false;
  try { const u = new URL(connector); ok = (u.protocol === "https:" || u.hostname === "localhost" || u.hostname === "127.0.0.1") && u.pathname === "/api/mcp"; } catch { ok = false; }
  const code = (p.get("code") || "").toUpperCase();
  const device = p.get("device") || "";
  return { connector: ok ? connector : "", code: /^[A-Z2-9]{4}-[A-Z2-9]{4}$/.test(code) ? code : "", device: /^bbd_[a-f0-9]{20}$/.test(device) ? device : "" };
}

