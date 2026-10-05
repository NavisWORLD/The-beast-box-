/**
 * Pairing, OAuth 2.1 (authorization code + PKCE S256, refresh rotation, revocation)
 * and personal access tokens for the Meta Muse connector.
 *
 * Only SHA-256 hashes of tokens and codes are stored. Raw tokens are returned once
 * and never logged. Every record is keyed to one paired account (one browser link).
 */
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

export const SCOPE_READ = "beast.read";
export const SCOPE_CARE = "beast.care";
export const SCOPES = [SCOPE_READ, SCOPE_CARE];
export const ACCESS_TTL = 3600;
export const REFRESH_TTL = 60 * 60 * 24 * 30;
export const CODE_TTL = 300;
export const PAIR_TTL = 600;
export const CLIENT_TTL = 60 * 60 * 24 * 180;
export const ACCOUNT_TTL = 60 * 60 * 24 * 180;
export const PAT_TTL = 60 * 60 * 24 * 180;
const PAIR_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

export const hashToken = (value) => createHash("sha256").update(String(value)).digest("hex");
export const randomToken = (prefix, bytes = 32) => prefix + randomBytes(bytes).toString("base64url");
const b64url = (buf) => Buffer.from(buf).toString("base64url");
const iso = (ms) => new Date(ms).toISOString();

export class AuthError extends Error {
  constructor(code, message, status = 400) { super(message); this.code = code; this.status = status; }
}

/** "read" -> beast.read ; "care" -> beast.read beast.care */
export function scopeForChoice(choice) { return choice === "care" ? `${SCOPE_READ} ${SCOPE_CARE}` : SCOPE_READ; }
/** Narrow a requested scope string to the supported set, always including read. */
export function normalizeScope(requested) {
  const parts = String(requested || "").split(/\s+/).filter((s) => SCOPES.includes(s));
  return parts.includes(SCOPE_CARE) ? `${SCOPE_READ} ${SCOPE_CARE}` : SCOPE_READ;
}
export const canCare = (scope) => String(scope || "").split(/\s+/).includes(SCOPE_CARE);

/** PKCE S256: BASE64URL(SHA256(verifier)) === challenge. Plain is not supported. */
export function verifyPkce(verifier, challenge, method = "S256") {
  if (method !== "S256") return false;
  if (typeof verifier !== "string" || !/^[A-Za-z0-9._~-]{43,128}$/.test(verifier)) return false;
  if (typeof challenge !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(challenge)) return false;
  const expected = Buffer.from(b64url(createHash("sha256").update(verifier).digest()));
  const given = Buffer.from(challenge);
  return expected.length === given.length && timingSafeEqual(expected, given);
}
export function pkceChallenge(verifier) { return b64url(createHash("sha256").update(verifier).digest()); }

export function pairingCode() {
  const bytes = randomBytes(8);
  let out = "";
  for (let i = 0; i < 8; i++) out += PAIR_ALPHABET[bytes[i] % PAIR_ALPHABET.length];
  return out.slice(0, 4) + "-" + out.slice(4);
}
export const cleanPairingCode = (code) => {
  const raw = String(code || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return raw.length === 8 ? raw.slice(0, 4) + "-" + raw.slice(4) : "";
};

// ---------------------------------------------------------------- accounts

async function saveAccount(store, account) { await store.set("acct:" + account.id, account, ACCOUNT_TTL); }
export async function getAccount(store, accountId) { return accountId ? store.get("acct:" + accountId) : null; }

export const cleanDeviceName = (name) => String(name || "").replace(/[^\w .·'()-]/g, "").replace(/\s+/g, " ").trim().slice(0, 60);
export const defaultDeviceName = (beastName) => cleanDeviceName("Beast Box · " + (beastName || "my beast"));

/**
 * A browser opts in: one account per link, a device secret for that browser only.
 * `deviceId` is a public, non-secret id used only to look up the device name for the
 * server card and pairing link. It grants nothing.
 * @param {any} store
 * @param {{ snapshot?: any, deviceName?: string, now?: number }} [options]
 */
export async function createAccount(store, { snapshot = null, deviceName = "", now = Date.now() } = {}) {
  const id = randomBytes(12).toString("hex");
  const deviceSecret = randomToken("bbm_dev_");
  const deviceId = "bbd_" + randomBytes(10).toString("hex");
  const name = cleanDeviceName(deviceName) || defaultDeviceName(snapshot && snapshot.beast && (snapshot.beast.displayName || (snapshot.beast.genome && snapshot.beast.genome.names && snapshot.beast.genome.names["1"])));
  const account = { id, deviceId, deviceName: name, createdAt: iso(now), lastActivityAt: null, lastActivity: null, snapshot, actions: [], tokens: [], requests: {} };
  await saveAccount(store, account);
  await store.set("dev:" + hashToken(deviceSecret), { accountId: id }, ACCOUNT_TTL);
  await store.set("devid:" + deviceId, { accountId: id }, ACCOUNT_TTL);
  return { account, deviceSecret };
}
export async function setDeviceName(store, accountId, name) {
  const clean = cleanDeviceName(name);
  if (!clean) throw new AuthError("invalid_device_name", "Device name must contain 1-60 letters, digits, spaces or . · ' ( ) -.");
  return updateAccount(store, accountId, (account) => { account.deviceName = clean; return { deviceName: clean }; });
}
/** Public lookup for the server card: returns only the device name, or null. */
export async function deviceById(store, deviceId) {
  if (typeof deviceId !== "string" || !/^bbd_[a-f0-9]{20}$/.test(deviceId)) return null;
  const link = await store.get("devid:" + deviceId);
  const account = link ? await getAccount(store, link.accountId) : null;
  return account ? { deviceId, deviceName: account.deviceName } : null;
}
export async function deviceAccount(store, secret) {
  if (typeof secret !== "string" || !secret.startsWith("bbm_dev_") || secret.length > 120) return null;
  const link = await store.get("dev:" + hashToken(secret));
  return link ? getAccount(store, link.accountId) : null;
}
export async function updateAccount(store, accountId, mutate) {
  const account = await getAccount(store, accountId);
  if (!account) throw new AuthError("not_paired", "This beast is no longer paired.", 401);
  const result = await mutate(account);
  await saveAccount(store, account);
  return result === undefined ? account : result;
}

export async function newPairingCode(store, accountId, now = Date.now()) {
  const code = pairingCode();
  await store.set("pair:" + code, { accountId }, PAIR_TTL);
  return { code, expiresAt: iso(now + PAIR_TTL * 1000) };
}
export async function consumePairingCode(store, code) {
  const clean = cleanPairingCode(code);
  if (!clean) return null;
  const hit = await store.get("pair:" + clean);
  if (!hit) return null;
  await store.del("pair:" + clean);
  return getAccount(store, hit.accountId);
}

/** Unpair: revoke every token, drop the device link and delete the stored snapshot. */
export async function unpairAccount(store, accountId, deviceSecret = "") {
  const account = await getAccount(store, accountId);
  if (account) for (const t of account.tokens || []) await store.del("tok:" + t.hash);
  if (deviceSecret) await store.del("dev:" + hashToken(deviceSecret));
  if (account && account.deviceId) await store.del("devid:" + account.deviceId);
  await store.del("acct:" + accountId);
  return { unpaired: true, revokedTokens: account ? (account.tokens || []).length : 0 };
}

// ---------------------------------------------------------------- OAuth clients (RFC 7591)

export function validRedirectUri(uri) {
  try {
    const u = new URL(uri);
    if (u.hash) return false;
    if (u.protocol === "https:") return true;
    return u.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(u.hostname);
  } catch { return false; }
}
export async function registerClient(store, body, now = Date.now()) {
  const uris = Array.isArray(body && body.redirect_uris) ? body.redirect_uris.filter((u) => typeof u === "string") : [];
  if (!uris.length || uris.length > 5 || !uris.every(validRedirectUri)) throw new AuthError("invalid_redirect_uri", "redirect_uris must be https URLs (or http on localhost).");
  const client = {
    client_id: "bbm_client_" + randomBytes(12).toString("hex"),
    client_name: typeof body.client_name === "string" ? body.client_name.replace(/[^\w .()'-]/g, "").slice(0, 60) || "MCP client" : "MCP client",
    redirect_uris: uris,
    grant_types: ["authorization_code", "refresh_token"],
    response_types: ["code"],
    token_endpoint_auth_method: "none",
    client_id_issued_at: Math.floor(now / 1000),
  };
  await store.set("client:" + client.client_id, client, CLIENT_TTL);
  return client;
}
export async function getClient(store, clientId) {
  return typeof clientId === "string" && /^bbm_client_[a-f0-9]{24}$/.test(clientId) ? store.get("client:" + clientId) : null;
}

/** Validate an /authorize request before showing consent. */
export async function checkAuthorizeRequest(store, q, resource) {
  const client = await getClient(store, q.client_id);
  if (!client) throw new AuthError("invalid_client", "Unknown client. Register the client first.");
  if (!client.redirect_uris.includes(q.redirect_uri)) throw new AuthError("invalid_redirect_uri", "This redirect URI is not registered for the client.");
  if (q.response_type !== "code") throw new AuthError("unsupported_response_type", "Only response_type=code is supported.");
  if (q.code_challenge_method !== "S256" || !/^[A-Za-z0-9_-]{43}$/.test(String(q.code_challenge || ""))) throw new AuthError("invalid_request", "PKCE with code_challenge_method=S256 is required.");
  if (q.resource && q.resource !== resource) throw new AuthError("invalid_target", "The resource must be this connector's /api/mcp URL.");
  return client;
}

export async function createAuthCode(store, { client, redirectUri, codeChallenge, scope, accountId, resource }) {
  const code = randomToken("bbm_code_", 24);
  await store.set("code:" + hashToken(code), { clientId: client.client_id, clientName: client.client_name, redirectUri, codeChallenge, scope: normalizeScope(scope), accountId, resource }, CODE_TTL);
  return code;
}

async function issue(store, { accountId, clientId, clientName, scope, kind, label = "", now = Date.now() }) {
  const ttl = kind === "pat" ? PAT_TTL : ACCESS_TTL;
  const prefix = kind === "pat" ? "bbm_pat_" : "bbm_at_";
  const token = randomToken(prefix);
  const id = randomBytes(6).toString("hex");
  const record = { accountId, kind, scope, clientId, id, expAt: now + ttl * 1000 };
  await store.set("tok:" + hashToken(token), record, ttl);
  const tokens = [{ hash: hashToken(token), id, kind, scope, clientId, clientName: clientName || label || (kind === "pat" ? "Muse Code token" : "MCP client"), createdAt: iso(now), expAt: iso(record.expAt), lastUsedAt: null }];
  let refresh = null;
  if (kind === "oauth") {
    refresh = randomToken("bbm_rt_");
    await store.set("tok:" + hashToken(refresh), { accountId, kind: "refresh", scope, clientId, id, expAt: now + REFRESH_TTL * 1000 }, REFRESH_TTL);
    tokens.push({ hash: hashToken(refresh), id, kind: "refresh", scope, clientId, clientName, createdAt: iso(now), expAt: iso(now + REFRESH_TTL * 1000), lastUsedAt: null });
  }
  await updateAccount(store, accountId, (account) => {
    const live = (account.tokens || []).filter((t) => Date.parse(t.expAt) > now);
    account.tokens = [...live, ...tokens].slice(-40);
  });
  return { token, refresh, id, expiresIn: ttl };
}

/** Token endpoint: authorization_code (with PKCE) or refresh_token (rotating). */
export async function exchangeToken(store, params, now = Date.now()) {
  const grant = params.grant_type;
  if (grant === "authorization_code") {
    const key = "code:" + hashToken(String(params.code || ""));
    const record = await store.get(key);
    if (!record) throw new AuthError("invalid_grant", "The authorization code is invalid, expired or already used.");
    await store.del(key); // single use
    if (record.clientId !== params.client_id) throw new AuthError("invalid_grant", "The code was issued to a different client.");
    if (record.redirectUri !== params.redirect_uri) throw new AuthError("invalid_grant", "redirect_uri does not match the authorization request.");
    if (!verifyPkce(params.code_verifier, record.codeChallenge)) throw new AuthError("invalid_grant", "PKCE verification failed.");
    if (params.resource && record.resource && params.resource !== record.resource) throw new AuthError("invalid_target", "The resource does not match the authorization request.");
    const out = await issue(store, { accountId: record.accountId, clientId: record.clientId, clientName: record.clientName, scope: record.scope, kind: "oauth", now });
    return { access_token: out.token, token_type: "Bearer", expires_in: out.expiresIn, refresh_token: out.refresh, scope: record.scope };
  }
  if (grant === "refresh_token") {
    const key = "tok:" + hashToken(String(params.refresh_token || ""));
    const record = await store.get(key);
    if (!record || record.kind !== "refresh" || record.expAt <= now) throw new AuthError("invalid_grant", "The refresh token is invalid, expired or revoked.");
    if (record.clientId !== params.client_id) throw new AuthError("invalid_grant", "The refresh token was issued to a different client.");
    await store.del(key); // rotation
    const client = await getClient(store, record.clientId);
    const scope = params.scope ? normalizeScope(params.scope) : record.scope;
    const narrowed = canCare(record.scope) ? scope : record.scope; // never widen
    const out = await issue(store, { accountId: record.accountId, clientId: record.clientId, clientName: client && client.client_name, scope: narrowed, kind: "oauth", now });
    return { access_token: out.token, token_type: "Bearer", expires_in: out.expiresIn, refresh_token: out.refresh, scope: narrowed };
  }
  throw new AuthError("unsupported_grant_type", "Use authorization_code or refresh_token.");
}

/** RFC 7009: revoking an unknown token is not an error. Revokes the token's pair too. */
export async function revokeToken(store, token) {
  const hash = hashToken(String(token || ""));
  const record = await store.get("tok:" + hash);
  if (!record) return { revoked: false };
  await store.del("tok:" + hash);
  const account = await getAccount(store, record.accountId);
  if (account) {
    const siblings = (account.tokens || []).filter((t) => t.id === record.id);
    for (const t of siblings) await store.del("tok:" + t.hash);
    account.tokens = (account.tokens || []).filter((t) => t.id !== record.id);
    await saveAccount(store, account);
  }
  return { revoked: true };
}
export async function revokeById(store, accountId, id) {
  return updateAccount(store, accountId, async (account) => {
    const hit = (account.tokens || []).filter((t) => t.id === id);
    for (const t of hit) await store.del("tok:" + t.hash);
    account.tokens = (account.tokens || []).filter((t) => t.id !== id);
    return { revoked: hit.length > 0 };
  });
}

export async function createPat(store, accountId, choice, now = Date.now()) {
  const scope = scopeForChoice(choice);
  const out = await issue(store, { accountId, clientId: "muse-code-pat", scope, kind: "pat", label: choice === "care" ? "Muse Code token (read + care)" : "Muse Code token (read only)", now });
  return { token: out.token, id: out.id, scope, expiresAt: iso(now + out.expiresIn * 1000) };
}

/** Resolve a Bearer token for /api/mcp. Refresh tokens and device secrets are not accepted. */
export async function authenticate(store, header, now = Date.now()) {
  const match = /^Bearer ([A-Za-z0-9_-]{20,200})$/.exec(String(header || ""));
  if (!match) return null;
  const token = match[1];
  if (!token.startsWith("bbm_at_") && !token.startsWith("bbm_pat_")) return null;
  const hash = hashToken(token);
  const record = await store.get("tok:" + hash);
  if (!record || record.kind === "refresh" || record.expAt <= now) return null;
  const account = await getAccount(store, record.accountId);
  if (!account) return null;
  return { accountId: record.accountId, scope: record.scope, clientId: record.clientId, kind: record.kind, tokenId: record.id, tokenHash: hash };
}

/** Panel status for the paired browser. Never includes token values or hashes. */
export function publicStatus(account, now = Date.now()) {
  const grants = new Map();
  for (const t of account.tokens || []) {
    if (Date.parse(t.expAt) <= now) continue;
    const g = grants.get(t.id) || { id: t.id, kind: t.kind === "pat" ? "pat" : "oauth", client: t.clientName, scope: t.scope, readOnly: !canCare(t.scope), createdAt: t.createdAt, lastUsedAt: null };
    if (t.lastUsedAt && (!g.lastUsedAt || t.lastUsedAt > g.lastUsedAt)) g.lastUsedAt = t.lastUsedAt;
    grants.set(t.id, g);
  }
  return {
    paired: true,
    deviceId: account.deviceId || null,
    deviceName: account.deviceName || null,
    createdAt: account.createdAt,
    lastActivityAt: account.lastActivityAt,
    lastActivity: account.lastActivity,
    connections: [...grants.values()],
    pendingActions: (account.actions || []).length,
    snapshotSyncedAt: account.snapshot ? account.snapshot.syncedAt : null,
  };
}
