/**
 * Pair Muse: a shared Web Bluetooth link to a Muse 2 / Muse S headband
 * (GATT service 0xfe8d), built on the existing Spark Muse kit
 * (lib/companion/spark/muse.mjs) and the opt-in sensor path
 * (lib/companion/sensors.mjs readSignal).
 *
 * Soft consumer EEG signals only: relative band levels for play. Not medical,
 * not mind-reading. Samples stay in this page's memory and are never uploaded,
 * saved, or added to the chat context.
 */
import { bandPowers, decodeEegPacket, deriveTraits, encodeCommand, WINDOW } from "./spark/muse.mjs";
import { readSignal } from "./sensors.mjs";

export const MUSE_SERVICE = 0xfe8d;
export const MUSE_CONTROL = "273e0001-4c4d-454d-96be-f03bac821358";
export const MUSE_TELEMETRY = "273e000b-4c4d-454d-96be-f03bac821358";
export const MUSE_EEG = {
  TP9: "273e0003-4c4d-454d-96be-f03bac821358",
  AF7: "273e0004-4c4d-454d-96be-f03bac821358",
  AF8: "273e0005-4c4d-454d-96be-f03bac821358",
  TP10: "273e0006-4c4d-454d-96be-f03bac821358",
};
export const BANDS = ["delta", "theta", "alpha", "beta", "gamma"];
export const UNSUPPORTED_MESSAGE = "Bluetooth pairing needs Chrome or Edge on Android, Windows, Mac or ChromeOS.";
export const MUSE_LABEL = "Soft consumer EEG signals for play. Not medical and not mind-reading. Band levels stay in this page and nothing is uploaded.";
const STEP = 64; // recompute band levels every 64 new samples (4 per second at 256 Hz)

/** Feature-detect Web Bluetooth (missing on iOS Safari and Firefox). */
export function bluetoothSupport(nav = typeof navigator === "undefined" ? undefined : navigator) {
  const supported = Boolean(nav && nav.bluetooth && typeof nav.bluetooth.requestDevice === "function");
  return { supported, message: supported ? "Web Bluetooth is available. Pairing opens the browser's own device chooser." : UNSUPPORTED_MESSAGE };
}

/** Absolute band powers to relative 0..1 levels that sum to 1. */
export function relativeBands(bands) {
  const total = BANDS.reduce((sum, name) => sum + Math.max(0, Number(bands && bands[name]) || 0), 0);
  const out = {};
  for (const name of BANDS) out[name] = total > 0 ? Math.round((Math.max(0, Number(bands[name]) || 0) / total) * 1000) / 1000 : 0;
  return out;
}

/** Soft exponential smoothing so the bars and the beast never jump. */
export function smoothBands(previous, next, amount = 0.3) {
  if (!previous) return { ...next };
  const out = {};
  for (const name of BANDS) out[name] = Math.round(((previous[name] || 0) * (1 - amount) + (next[name] || 0) * amount) * 1000) / 1000;
  return out;
}

/** Muse telemetry packet (muse-js layout): battery percent is uint16 at byte 2 / 512. */
export function decodeTelemetry(packet) {
  const view = packet instanceof DataView ? packet : new DataView(packet.buffer, packet.byteOffset, packet.byteLength);
  if (view.byteLength < 4) return { battery: null };
  const battery = view.getUint16(2) / 512;
  return { battery: Number.isFinite(battery) ? Math.max(0, Math.min(100, Math.round(battery))) : null };
}

/**
 * How the soft signal plays: beast mood, animation energy, and music intensity.
 * Takes a readSignal() result plus relative bands.
 */
export function museInfluence(signal, bands) {
  if (!signal || !signal.available || !bands) return { active: false, mood: "idle", energy: 0.5, intensity: 0 };
  const calm = bands.alpha + bands.theta * 0.5;
  const drive = bands.beta + bands.gamma;
  const drowsy = bands.delta + bands.theta;
  const energy = Math.max(0.1, Math.min(1, 0.35 + drive * 1.4 - bands.alpha * 0.5));
  const intensity = Math.max(0, Math.min(1, drive * 1.6 - calm * 0.4));
  let mood = "idle";
  if (drowsy > 0.6) mood = "drowsy";
  else if (signal.spark >= 25 && drive > calm) mood = "sparky";
  else if (signal.focus > signal.calm) mood = "focused";
  else if (calm >= drive) mood = "calm";
  return { active: true, mood, energy: Math.round(energy * 100) / 100, intensity: Math.round(intensity * 100) / 100 };
}

const OFF_BANDS = Object.freeze({ delta: 0, theta: 0, alpha: 0, beta: 0, gamma: 0 });

export function createMusePair({ getNavigator = () => (typeof navigator === "undefined" ? undefined : navigator) } = {}) {
  const support = bluetoothSupport(getNavigator());
  const state = {
    supported: support.supported,
    status: support.supported ? "idle" : "unsupported",
    message: support.supported ? "Not paired. Your headband stays off until you choose Pair Muse." : UNSUPPORTED_MESSAGE,
    deviceName: "",
    battery: null,
    bands: { ...OFF_BANDS },
    traits: null,
    signal: readSignal({}),
    influence: museInfluence(null, null),
    windows: 0,
  };
  const listeners = new Set();
  let cached = { ...state };
  const emit = () => { cached = { ...state, bands: { ...state.bands } }; for (const fn of listeners) fn(); };
  let device = null, control = null, onDisconnected = null;
  const rings = new Map();
  const handlers = [];

  function reset(status, message) {
    for (const ring of rings.values()) ring.data.fill(0);
    rings.clear();
    state.status = status; state.message = message;
    state.bands = { ...OFF_BANDS }; state.traits = null; state.battery = status === "connected" ? state.battery : null;
    state.signal = readSignal({}); state.influence = museInfluence(null, null); state.windows = 0;
    emit();
  }

  /** Feed decoded samples for one electrode (also used by tests and the Bluetooth handler). */
  function pushSamples(channel, samples) {
    if (state.status !== "connected") return false;
    let ring = rings.get(channel);
    if (!ring) { ring = { data: new Float64Array(WINDOW), write: 0, filled: 0, fresh: 0 }; rings.set(channel, ring); }
    for (const sample of samples) {
      ring.data[ring.write] = sample; ring.write = (ring.write + 1) % WINDOW;
      if (ring.filled < WINDOW) ring.filled++;
      ring.fresh++;
    }
    if (ring.filled < WINDOW || ring.fresh < STEP) return false;
    ring.fresh = 0;
    const ordered = new Float64Array(WINDOW);
    for (let i = 0; i < WINDOW; i++) ordered[i] = ring.data[(ring.write + i) % WINDOW];
    const powers = bandPowers(ordered);
    ordered.fill(0);
    const traits = deriveTraits(powers);
    state.bands = smoothBands(state.windows ? state.bands : null, relativeBands(powers));
    state.traits = state.traits ? {
      focus: Math.round(state.traits.focus * 0.7 + traits.focus * 0.3),
      calm: Math.round(state.traits.calm * 0.7 + traits.calm * 0.3),
      spark: Math.round(state.traits.spark * 0.7 + traits.spark * 0.3),
    } : traits;
    state.signal = readSignal({ museTraits: state.traits });
    state.influence = museInfluence(state.signal, state.bands);
    if (!state.windows) state.message = `Live soft band levels from ${state.deviceName || "your Muse"}. They stay in this page.`;
    state.windows++;
    emit();
    return true;
  }

  async function connect() {
    const nav = getNavigator();
    if (!bluetoothSupport(nav).supported) { reset("unsupported", UNSUPPORTED_MESSAGE); return false; }
    if (state.status === "connecting" || state.status === "connected") return state.status === "connected";
    state.status = "connecting"; state.message = "Choose your Muse in the browser's Bluetooth chooser."; emit();
    try {
      device = await nav.bluetooth.requestDevice({ filters: [{ services: [MUSE_SERVICE] }], optionalServices: [MUSE_SERVICE] });
      const server = await device.gatt.connect();
      const service = await server.getPrimaryService(MUSE_SERVICE);
      control = await service.getCharacteristic(MUSE_CONTROL);
      const send = (cmd) => control.writeValue(encodeCommand(cmd));
      await send("h");
      await send("p21");
      state.status = "connected";
      state.deviceName = device.name || "Muse";
      state.message = `Connected to ${state.deviceName}. Waiting for a full second of signal.`;
      try {
        const telemetry = await service.getCharacteristic(MUSE_TELEMETRY);
        await telemetry.startNotifications();
        const onTelemetry = (event) => { const t = decodeTelemetry(event.target.value); if (t.battery !== null) { state.battery = t.battery; emit(); } };
        telemetry.addEventListener("characteristicvaluechanged", onTelemetry);
        handlers.push([telemetry, onTelemetry]);
      } catch { /* battery is optional */ }
      for (const [name, uuid] of Object.entries(MUSE_EEG)) {
        try {
          const characteristic = await service.getCharacteristic(uuid);
          await characteristic.startNotifications();
          const onEeg = (event) => { pushSamples(name, decodeEegPacket(event.target.value).samples); };
          characteristic.addEventListener("characteristicvaluechanged", onEeg);
          handlers.push([characteristic, onEeg]);
        } catch { /* some firmware exposes fewer electrodes */ }
      }
      onDisconnected = () => { cleanup(); reset("idle", "The headband disconnected. Pair again when you are ready."); };
      device.addEventListener("gattserverdisconnected", onDisconnected);
      await send("s");
      await send("d");
      emit();
      return true;
    } catch (error) {
      cleanup();
      const cancelled = error && (error.name === "NotFoundError" || /cancel/i.test(String(error.message)));
      reset("idle", cancelled ? "Pairing was cancelled. Nothing was connected." : `Muse did not connect: ${error && error.message ? error.message : "unknown error"}.`);
      return false;
    }
  }

  function cleanup() {
    for (const [target, fn] of handlers.splice(0)) { try { target.removeEventListener("characteristicvaluechanged", fn); } catch { /* gone */ } }
    if (device && onDisconnected) { try { device.removeEventListener("gattserverdisconnected", onDisconnected); } catch { /* gone */ } }
    onDisconnected = null;
  }

  async function disconnect() {
    const wasConnected = state.status === "connected";
    try { if (control && wasConnected) await control.writeValue(encodeCommand("h")); } catch { /* already gone */ }
    cleanup();
    try { device && device.gatt && device.gatt.connected !== false && device.gatt.disconnect(); } catch { /* already gone */ }
    device = null; control = null;
    state.battery = null; state.deviceName = "";
    reset(state.supported ? "idle" : "unsupported", state.supported ? "Disconnected. The headband is off and its band levels were cleared." : UNSUPPORTED_MESSAGE);
  }

  return {
    connect, disconnect, pushSamples,
    subscribe(fn) { listeners.add(fn); return () => { listeners.delete(fn); }; },
    getSnapshot() { return cached; },
  };
}

let shared = null;
/** One Muse link per tab, shared by the cage, the GO screen and the owner deck. */
export function getMusePair() {
  if (typeof window === "undefined") return createMusePair({ getNavigator: () => undefined });
  if (!shared) shared = createMusePair();
  return shared;
}
