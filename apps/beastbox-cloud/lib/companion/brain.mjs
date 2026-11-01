
// Public RAWRPHOS pin, mirrored from lib/rawrphos-public-pin.json (a test enforces equality).
// 14000 stays accepted as the documented rollback baseline.
export const RAWRPHOS_PUBLIC_PIN = Object.freeze({ step: 35824, checkpoint_sha256: "a0b564cfe5ca7a1c3e73f617816e8223e08ea18ff8da8fcde37b717f63595397" });
const RAWRPHOS_BASE_PIN = Object.freeze({ step: 14000, checkpoint_sha256: "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5" });
function pinnedGuestStep(payload) {
  for (const pin of [RAWRPHOS_PUBLIC_PIN, RAWRPHOS_BASE_PIN]) {
    if (payload?.step !== pin.step) continue;
    const sha = payload?.checkpoint_sha256;
    if (sha === undefined || sha === pin.checkpoint_sha256) return pin.step;
  }
  return null;
}
/**
 * Model routing for the adventure chat.
 * A missing or unverified model result is a failure, not a substitute sentence.
 */

export function chooseBrain({ ownerReady = false, providerKind = "", guestReady = false } = {}) {
  const kind = String(providerKind || "");
  if (ownerReady && kind && kind !== "UNKNOWN" && kind !== "reference") {
    return {
      route: "owner-bridge",
      label: `Brain Bay · ${kind}`,
      endpoint: "/api/bridge/chat-start",
    };
  }
  if (guestReady) {
    return {
      route: "guest-rawrphos",
      label: `RAWRPHØS guest ${RAWRPHOS_PUBLIC_PIN.step} (stateless host). Context is sent only inside this message.`,
      endpoint: "/api/guest",
    };
  }
  return {
    route: "local-mind",
    label: "On-device pattern memory. No language model is connected.",
    endpoint: null,
  };
}

export function guestBody(prompt) {
  return { provider: "rawrphos-local", text: String(prompt || "").slice(0, 700) };
}

export function ownerChatBody(prompt, requestId) {
  return {
    text: String(prompt || "").slice(0, 8192),
    context_ids: [],
    request_id: requestId,
  };
}

function textOf(value) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

export function interpretModelResult(route, payload) {
  if (route === "owner-bridge") {
    const completed = payload?.result?.result || payload?.result;
    const reply = textOf(completed?.response);
    if (reply) return { ok: true, reply: String(reply), source: "owner-bridge" };
    const job = textOf(payload?.response);
    if (job) return { ok: true, reply: String(job), source: "owner-bridge" };
    return { ok: false, reason: textOf(payload?.error) || "Brain Bay returned no verified text" };
  }
  if (route === "guest-rawrphos") {
    if (payload?.provider === "rawrphos-local" && payload?.model === "rawrphos-native" && pinnedGuestStep(payload) !== null && payload?.guest_stateless === true) {
      const reply = textOf(payload.reply);
      if (reply) return { ok: true, reply: String(reply), source: "guest-rawrphos", model: "rawrphos-native", step: pinnedGuestStep(payload) };
    }
    return { ok: false, reason: textOf(payload?.error) || "RAWRPHØS guest returned no verified text" };
  }
  return { ok: false, reason: "local pattern memory is not a language model" };
}

export function fallbackAfterFailure(reason) {
  return {
    route: "local-mind",
    label: "On-device pattern memory. No language model is connected.",
    failure: reason || "The selected model did not answer",
  };
}
