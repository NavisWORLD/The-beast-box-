/**
 * Door-side lived snapshot receipt (PR B2).
 *
 * The bridge already read the canonical snapshot. These helpers only carry
 * that receipt through the doors and the one-voice choice. They do not admit
 * a sample, call a model, or read a visitor-supplied environment as state.
 * Guest and visitor mouths never keep an owner-conditioned receipt.
 */
export const LIVED_MOUTH_SCHEMA = 'lived-mouth-receipt-v1';

/** Guest and visitor doors never open the owner chain. This module is not the writer. */
export function ownerChainWrite(scope) {
  if (scope !== 'owner') return {wrote: false, reason: 'isolated', chain: null};
  return {wrote: false, reason: 'server', chain: null};
}
const HEX64 = /^[0-9a-f]{64}$/;
const HEX32 = /^[0-9a-f]{32}$/;
const STATUSES = new Set(['delivered', 'unavailable', 'omitted']);
const REASONS = new Set([
  'isolated', 'missing', 'stale', 'rejected', 'remote_withheld', 'budget', 'capability', 'diverged',
]);

/** SHA-256 hex via Web Crypto. The same global exists in the browser and in Node. */
async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

/** One id for every draft of this turn. Deterministic: no clock and no Math.random. */
export async function mintExchangeId(scope, identity, text) {
  return (await sha256Hex(`lived-exchange-v1\n${scope}\n${identity}\n${text}`)).slice(0, 32);
}

/** A browser environment summary is sight, not the canonical lived snapshot. */
export function environmentIsNotCanonical(environment) {
  return {ignored: environment !== undefined, snapshot: null};
}

function blank(reason, {exchangeId = null, scope = 'guest', spokenBy = null} = {}) {
  return {
    schema: LIVED_MOUTH_SCHEMA,
    status: 'unavailable',
    reason,
    sequence: null,
    state_sha256: null,
    descriptor_sha256: null,
    conditioned: false,
    changes_model_tensors: false,
    counts_as_memory_used: false,
    omitted_current_text_bytes: 0,
    scope: scope === 'owner' || scope === 'visitor' ? scope : 'guest',
    exchange_id: idOrNull(exchangeId),
    spoken_by: voiceOrNull(spokenBy),
  };
}

function idOrNull(value) {
  return typeof value === 'string' && HEX32.test(value) ? value : null;
}

function voiceOrNull(value) {
  return value === 'gated' || value === 'growing' || value === 'owner' ? value : null;
}

/**
 * Shape one bridge `lived_state` object for a door response.
 * `undefined` means the bridge did not send the field (flag off or an older
 * bridge): the caller omits the key and does not call the model again.
 */
export function mouthReceipt(raw, {exchangeId = null, scope = 'guest', spokenBy = null, environment} = {}) {
  environmentIsNotCanonical(environment);
  if (raw === undefined) return null;
  const meta = {exchangeId, scope, spokenBy};
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return blank('capability', meta);
  if ('environment' in raw || 'snapshot' in raw || 'state12' in raw || 'channels' in raw || 'state' in raw)
    return blank(scope === 'owner' ? 'rejected' : 'isolated', meta);
  const status = STATUSES.has(raw.status) ? raw.status : null;
  if (!status) return blank('capability', meta);
  if (scope !== 'owner' && (status === 'delivered' || raw.conditioned === true))
    return blank('isolated', meta);
  const sequence = Number.isInteger(raw.sequence) && raw.sequence >= 0 ? raw.sequence : null;
  const stateHash = typeof raw.state_sha256 === 'string' && HEX64.test(raw.state_sha256) ? raw.state_sha256 : null;
  const descHash = typeof raw.descriptor_sha256 === 'string' && HEX64.test(raw.descriptor_sha256) ? raw.descriptor_sha256 : null;
  if (scope !== 'owner' && (sequence !== null || stateHash !== null))
    return blank('isolated', meta);
  if (status === 'delivered' && (sequence === null || !stateHash || !descHash || raw.conditioned !== true))
    return blank('capability', meta);
  const reason = raw.reason == null ? null : (REASONS.has(raw.reason) ? raw.reason : null);
  if (status !== 'delivered' && reason == null) return blank('capability', meta);
  const omitted = Number.isInteger(raw.omitted_current_text_bytes) && raw.omitted_current_text_bytes >= 0
    ? raw.omitted_current_text_bytes : 0;
  return {
    schema: LIVED_MOUTH_SCHEMA,
    status,
    reason: status === 'delivered' ? null : reason,
    sequence,
    state_sha256: stateHash,
    descriptor_sha256: status === 'omitted' ? null : descHash,
    conditioned: status === 'delivered',
    changes_model_tensors: false,
    counts_as_memory_used: false,
    omitted_current_text_bytes: omitted,
    scope: scope === 'owner' || scope === 'visitor' ? scope : 'guest',
    exchange_id: idOrNull(exchangeId),
    spoken_by: voiceOrNull(spokenBy),
  };
}

/**
 * One exchange, two drafts. A failed growing draft keeps the gated receipt.
 * Disagreeing receipts are unavailable, never a silent success.
 * Both missing means the bridge sent no lived field: return null.
 */
export function speakLived({exchangeId, gated, growing, chosen, growingFailed = false} = {}) {
  const growingAbsent = growingFailed || growing === undefined || growing === null;
  if (gated === undefined && growingAbsent) return null;
  if (gated === undefined) return blank('capability', {exchangeId, scope: 'guest', spokenBy: chosen});
  const spoken = chosen === 'growing' && !growingFailed ? 'growing' : (chosen === 'growing' ? 'gated' : (chosen || 'gated'));
  const left = mouthReceipt(gated, {exchangeId, scope: 'guest', spokenBy: 'gated'});
  if (growingFailed) return {...left, spoken_by: voiceOrNull(spoken)};
  if (growing === undefined || growing === null)
    return blank('capability', {exchangeId, scope: 'guest', spokenBy: spoken});
  const right = mouthReceipt(growing, {exchangeId, scope: 'guest', spokenBy: 'growing'});
  const same = left.status === right.status && left.reason === right.reason
    && left.sequence === right.sequence && left.state_sha256 === right.state_sha256
    && left.descriptor_sha256 === right.descriptor_sha256;
  if (!same) return blank('diverged', {exchangeId, scope: 'guest', spokenBy: spoken});
  const picked = spoken === 'growing' ? right : left;
  return {...picked, spoken_by: voiceOrNull(spoken)};
}

/** Owner chat already nests the runtime result. Read it without a second model call. */
export function ownerTalkReceipt(payload, exchangeId) {
  const raw = payload?.lived_state ?? payload?.result?.lived_state ?? payload?.result?.result?.lived_state;
  return mouthReceipt(raw, {exchangeId, scope: 'owner', spokenBy: 'owner'});
}
