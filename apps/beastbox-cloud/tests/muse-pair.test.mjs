import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { bluetoothSupport, createMusePair, decodeTelemetry, MUSE_EEG, MUSE_SERVICE, MUSE_TELEMETRY, museInfluence, relativeBands, UNSUPPORTED_MESSAGE } from "../lib/companion/muse-pair.mjs";
import { createBeastAudio } from "../lib/companion/beast-audio-engine.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const decodeCmd = (bytes) => new TextDecoder().decode(bytes.subarray(1)).replace(/^X|\n$/g, "");

// ---- a mocked navigator.bluetooth with one Muse headband
function mockMuse({ name = "Muse-S 4F2A" } = {}) {
  const log = { requests: [], commands: [], disconnects: 0 };
  const listeners = new Map();
  const characteristic = (uuid) => ({
    uuid,
    async writeValue(bytes) { log.commands.push(decodeCmd(bytes)); },
    async startNotifications() { return this; },
    addEventListener(type, fn) { listeners.set(uuid, fn); },
    removeEventListener(type, fn) { if (listeners.get(uuid) === fn) listeners.delete(uuid); },
  });
  const deviceListeners = new Map();
  const device = {
    name,
    gatt: {
      connected: true,
      async connect() { return { async getPrimaryService(id) { assert.equal(id, MUSE_SERVICE); return { async getCharacteristic(uuid) { return characteristic(uuid); } }; } }; },
      disconnect() { log.disconnects++; this.connected = false; },
    },
    addEventListener(type, fn) { deviceListeners.set(type, fn); },
    removeEventListener(type) { deviceListeners.delete(type); },
  };
  const nav = { bluetooth: { async requestDevice(options) { log.requests.push(options); return device; } } };
  const emit = (uuid, view) => listeners.get(uuid)?.({ target: { value: view } });
  return { nav, log, listeners, deviceListeners, emit };
}
// Encode 12 samples (µV) into one Muse EEG packet (inverse of decodeEegPacket).
function eegPacket(seq, samples) {
  const raw = samples.map((uv) => Math.max(0, Math.min(4095, Math.round(uv / 0.48828125 + 0x800))));
  const bytes = new Uint8Array(2 + 18);
  bytes[0] = seq & 0xff; bytes[1] = (seq >> 8) & 0xff;
  for (let i = 0, o = 2; i < 12; i += 2, o += 3) {
    const a = raw[i], b = raw[i + 1];
    bytes[o] = a >> 4; bytes[o + 1] = ((a & 0xf) << 4) | (b >> 8); bytes[o + 2] = b & 0xff;
  }
  return new DataView(bytes.buffer);
}
function stream(mock, hz, seconds = 2, amp = 40) {
  let n = 0;
  for (let seq = 0; seq < (256 * seconds) / 12; seq++) {
    const samples = Array.from({ length: 12 }, () => { const t = n++ / 256; return amp * Math.sin(2 * Math.PI * hz * t) + 3 * Math.sin(2 * Math.PI * 41 * t); });
    for (const uuid of Object.values(MUSE_EEG)) mock.emit(uuid, eegPacket(seq, samples));
  }
}
const telemetry = (percent) => { const v = new DataView(new ArrayBuffer(10)); v.setUint16(2, Math.round(percent * 512)); return v; };

test("without navigator.bluetooth the panel says so honestly and never pairs", async () => {
  for (const nav of [undefined, {}, { bluetooth: {} }]) {
    assert.deepEqual(bluetoothSupport(nav), { supported: false, message: UNSUPPORTED_MESSAGE });
    const pair = createMusePair({ getNavigator: () => nav });
    assert.equal(pair.getSnapshot().status, "unsupported");
    assert.equal(pair.getSnapshot().message, "Bluetooth pairing needs Chrome or Edge on Android, Windows, Mac or ChromeOS.");
    assert.equal(await pair.connect(), false);
    assert.equal(pair.getSnapshot().status, "unsupported");
  }
});

test("Pair Muse asks the browser chooser for service 0xfe8d and starts the stream", async () => {
  const mock = mockMuse();
  const pair = createMusePair({ getNavigator: () => mock.nav });
  assert.equal(pair.getSnapshot().status, "idle");
  assert.equal(await pair.connect(), true);
  assert.deepEqual(mock.log.requests[0], { filters: [{ services: [0xfe8d] }], optionalServices: [0xfe8d] });
  assert.deepEqual(mock.log.commands, ["h", "p21", "s", "d"]);
  const snap = pair.getSnapshot();
  assert.equal(snap.status, "connected");
  assert.equal(snap.deviceName, "Muse-S 4F2A");
  assert.equal(snap.signal.available, false, "no signal until a full window arrives");
  for (const uuid of [...Object.values(MUSE_EEG), MUSE_TELEMETRY]) assert.ok(mock.listeners.has(uuid), uuid);
});

test("battery comes from the Muse telemetry characteristic", async () => {
  const mock = mockMuse();
  const pair = createMusePair({ getNavigator: () => mock.nav });
  await pair.connect();
  assert.equal(pair.getSnapshot().battery, null);
  mock.emit(MUSE_TELEMETRY, telemetry(87));
  assert.equal(pair.getSnapshot().battery, 87);
  assert.equal(decodeTelemetry(telemetry(42.4)).battery, 42);
});

test("live band levels follow the signal and feed the sensor path", async () => {
  const calm = mockMuse();
  const a = createMusePair({ getNavigator: () => calm.nav });
  await a.connect();
  stream(calm, 10);
  const relaxed = a.getSnapshot();
  assert.ok(relaxed.windows > 0);
  assert.equal(Object.entries(relaxed.bands).sort((x, y) => y[1] - x[1])[0][0], "alpha");
  assert.equal(relaxed.signal.mode, "muse");
  assert.equal(relaxed.signal.reason, "muse");
  assert.ok(relaxed.influence.active);
  assert.equal(relaxed.influence.mood, "calm");

  const busy = mockMuse();
  const b = createMusePair({ getNavigator: () => busy.nav });
  await b.connect();
  stream(busy, 21);
  const focused = b.getSnapshot();
  assert.equal(Object.entries(focused.bands).sort((x, y) => y[1] - x[1])[0][0], "beta");
  assert.ok(focused.signal.focus > focused.signal.calm);
  assert.ok(focused.influence.energy > relaxed.influence.energy, "more beta, more animation energy");
  assert.ok(focused.influence.intensity > relaxed.influence.intensity, "more beta, more music intensity");
});

test("Disconnect halts the headband, drops the link and clears every level", async () => {
  const mock = mockMuse();
  const pair = createMusePair({ getNavigator: () => mock.nav });
  await pair.connect();
  stream(mock, 10, 1);
  mock.emit(MUSE_TELEMETRY, telemetry(60));
  await pair.disconnect();
  assert.equal(mock.log.commands.at(-1), "h");
  assert.equal(mock.log.disconnects, 1);
  const snap = pair.getSnapshot();
  assert.equal(snap.status, "idle");
  assert.equal(snap.battery, null);
  assert.deepEqual(Object.values(snap.bands), [0, 0, 0, 0, 0]);
  assert.equal(snap.signal.available, false);
  assert.equal(snap.influence.active, false);
  assert.equal(mock.listeners.size, 0, "notification handlers removed");
  assert.equal(pair.pushSamples("AF7", new Array(300).fill(1)), false, "nothing is read after disconnect");
});

test("a headband that drops out resets the panel; a cancelled chooser connects nothing", async () => {
  const mock = mockMuse();
  const pair = createMusePair({ getNavigator: () => mock.nav });
  await pair.connect();
  mock.deviceListeners.get("gattserverdisconnected")();
  assert.equal(pair.getSnapshot().status, "idle");
  const cancel = createMusePair({ getNavigator: () => ({ bluetooth: { async requestDevice() { const e = new Error("User cancelled the requestDevice() chooser."); e.name = "NotFoundError"; throw e; } } }) });
  assert.equal(await cancel.connect(), false);
  assert.match(cancel.getSnapshot().message, /cancelled/);
});

test("relative bands and influence are bounded", () => {
  const r = relativeBands({ delta: 1, theta: 1, alpha: 6, beta: 1, gamma: 1 });
  assert.equal(r.alpha, 0.6);
  assert.deepEqual(museInfluence(null, null), { active: false, mood: "idle", energy: 0.5, intensity: 0 });
  const inf = museInfluence({ available: true, focus: 90, calm: 5, spark: 5 }, { delta: 0, theta: 0, alpha: 0, beta: 1, gamma: 0 });
  assert.ok(inf.energy <= 1 && inf.intensity <= 1);
});

test("Muse intensity lifts the beast music battle layer", () => {
  const fake = () => {
    const param = (v) => ({ value: v, setValueAtTime(x) { this.value = x; }, setTargetAtTime(x) { this.value = x; }, exponentialRampToValueAtTime() {}, cancelScheduledValues() {} });
    const node = (extra) => ({ connect() {}, ...extra });
    return { currentTime: 0, sampleRate: 8000, state: "running", destination: {},
      createGain: () => node({ gain: param(1) }), createOscillator: () => node({ frequency: param(1), detune: param(0), start() {}, stop() {} }),
      createBiquadFilter: () => node({ frequency: param(1), Q: param(1) }), createBufferSource: () => node({ start() {}, stop() {} }),
      createBuffer: (c, len) => ({ getChannelData: () => new Float32Array(len) }),
      createDynamicsCompressor: () => node({ threshold: param(0), knee: param(0), ratio: param(0), attack: param(0), release: param(0) }) };
  };
  const audio = createBeastAudio({ createContext: fake });
  audio.unlock();
  audio.setScene({ id: "habitat", seedKey: "k", element: "frost", enabled: true });
  assert.equal(audio.stats().battleGain, 0);
  audio.setIntensity(0.8);
  assert.ok(audio.stats().battleGain > 0.3);
  audio.setIntensity(0);
  assert.equal(audio.stats().battleGain, 0);
});

test("Pair Muse is wired into the GO menu, Settings, the owner deck and the cage, and never uploads", () => {
  const src = read("lib/companion/muse-pair.mjs");
  assert.doesNotMatch(src, /fetch\(|XMLHttpRequest|sendBeacon|localStorage|WebSocket/);
  assert.match(src, /0xfe8d/);
  const panel = read("components/muse-pair-panel.tsx");
  assert.match(panel, /Disconnect Muse/);
  assert.match(read("lib/companion/muse-pair.mjs"), /Not medical and not mind-reading/);
  const go = read("components/beast-go.tsx");
  assert.match(go, /data-pair-muse="menu"/);
  assert.match(go, /data-pair-muse="settings"/);
  assert.match(go, /<MusePairPanel/);
  const deck = read("components/studio.tsx");
  assert.ok(deck.includes('<Gamepad2 size={18}/>LOST COSMOS</Link><Link className="nav-item" href="/beast-cage/go#pair-muse"'), "Pair Muse sits right after LOST COSMOS");
  assert.ok(deck.includes("<Bluetooth size={18}/>PAIR MUSE</Link>"));
  assert.match(read("components/beast-cage-portal.tsx"), /<MusePairPanel\/>/);
  const route = read("app/api/gba-rom/route.ts");
  assert.match(route, /303865b4d1c9d0297e5b59e3945e5ee74dbafdcc344aec8deb9434ab87f9899a/);
  assert.match(read("app/api/gba-release/route.ts"), /lost_cosmos_main_commit:'12ed44df23ffc9a5c55c7a31a9bf45e423540c53'/);
});
