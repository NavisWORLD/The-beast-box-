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
      label: "RAWRPHØS guest 14K (stateless host). Context is sent only inside this message.",
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
    if (payload?.provider === "rawrphos-local" && payload?.model === "rawrphos-native" && payload?.step === 14000 && payload?.guest_stateless === true) {
      const reply = textOf(payload.reply);
      if (reply) return { ok: true, reply: String(reply), source: "guest-rawrphos", model: "rawrphos-native", step: 14000 };
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
