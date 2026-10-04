/**
 * Talk path for the field sheet. Adventure keeps its own caller.
 * A missing model reply stays empty. This module does not invent a sentence.
 */

import { chooseBrain, fallbackAfterFailure, guestBody, interpretModelResult, ownerChatBody } from "./brain.mjs";
import { renderContextPrompt } from "./context.mjs";

function defaultUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "00000000-0000-4000-8000-000000000000";
}

/**
 * @param {{
 *   context?: object,
 *   saying?: string,
 *   fetchImpl: (url: string, init?: RequestInit) => Promise<{ ok?: boolean, json: () => Promise<any> }>,
 *   sleep?: (ms: number) => Promise<void>,
 *   now?: () => number,
 *   uuid?: () => string,
 *   deadlineMs?: number,
 * }} [input]
 */
export async function askBeast(input = {}) {
  const context = input.context;
  const saying = input.saying;
  const fetchImpl = input.fetchImpl;
  const sleep = input.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const now = input.now || (() => Date.now());
  const uuid = input.uuid || defaultUuid;
  const deadlineMs = Number.isFinite(input.deadlineMs) ? input.deadlineMs : 40_000;
  const guestPrompt = renderContextPrompt(context, saying, 700);
  const ownerPrompt = renderContextPrompt(context, saying, 4000);
  let route = chooseBrain({ ownerReady: false, guestReady: false });
  try {
    const statusResponse = await fetchImpl("/api/status", { cache: "no-store", credentials: "same-origin" });
    const status = await statusResponse.json();
    route = chooseBrain({
      ownerReady: status?.owner === true && status?.backendReachable === true,
      providerKind: typeof status?.providerKind === "string" ? status.providerKind : "",
      guestReady: false,
    });
  } catch {
    route = chooseBrain({});
  }

  let reply = "";
  let label = route.label;
  let pending = false;

  if (route.route === "owner-bridge") {
    try {
      const requestId = uuid();
      const started = await fetchImpl("/api/bridge/chat-start", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ownerChatBody(ownerPrompt, requestId)),
      });
      const job = await started.json();
      if (started.ok && typeof job?.job_id === "string") {
        let state = job;
        const deadline = now() + deadlineMs;
        while (state.state === "running" && now() < deadline) {
          await sleep(2000);
          const polled = await fetchImpl("/api/bridge/chat-job?id=" + encodeURIComponent(job.job_id), {
            cache: "no-store",
            credentials: "same-origin",
          });
          state = await polled.json();
        }
        if (state.state === "running") {
          pending = true;
          label = "Brain Bay is still running. No substitute reply was invented.";
        } else {
          const read = interpretModelResult("owner-bridge", state);
          if (read.ok && read.reply) {
            reply = read.reply;
            label = route.label;
          } else label = fallbackAfterFailure(read.reason).failure;
        }
      } else label = fallbackAfterFailure(typeof job?.error === "string" ? job.error : "Brain Bay did not start a chat").failure;
    } catch (error) {
      label = fallbackAfterFailure(error instanceof Error ? error.message : "Brain Bay did not answer").failure;
    }
  }

  if (!reply && !pending) {
    try {
      const guestRoute = chooseBrain({ guestReady: true });
      const guest = await fetchImpl("/api/guest", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(guestBody(guestPrompt)),
      });
      const payload = await guest.json();
      const read = interpretModelResult("guest-rawrphos", payload);
      if (read.ok && read.reply) {
        reply = read.reply;
        label = guestRoute.label;
      } else if (route.route !== "owner-bridge") label = fallbackAfterFailure(read.reason).failure;
    } catch (error) {
      if (route.route !== "owner-bridge") {
        label = fallbackAfterFailure(error instanceof Error ? error.message : "RAWRPHØS guest did not answer").failure;
      }
    }
  }

  return { reply, label, pending };
}
