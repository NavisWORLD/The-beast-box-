/** Optional Muse 2 / S / S Athena EEG via Web Bluetooth. Derived traits only. Not a medical device. */

import { EEG_RATE, WINDOW, bandPowers, deriveTraits } from "./signal.mjs";

const MUSE_SERVICE = 0xfe8d;
const CONTROL = "273e0001-4c4d-454d-96be-f03bac821358";
const AF7 = "273e0004-4c4d-454d-96be-f03bac821358";

function encodeCommand(cmd) {
  const encoded = new TextEncoder().encode(`X${cmd}\n`);
  encoded[0] = encoded.length - 1;
  return encoded;
}

function decodeUnsigned12(samples) {
  const out = [];
  for (let i = 0; i < samples.length; i++) {
    if (i % 3 === 0) out.push((samples[i] << 4) | (samples[i + 1] >> 4));
    else {
      out.push(((samples[i] & 0xf) << 8) | samples[i + 1]);
      i += 1;
    }
  }
  return out;
}

function decodeEeg(packet) {
  const bytes = new Uint8Array(packet.buffer, packet.byteOffset, packet.byteLength);
  const raw = decodeUnsigned12(bytes.subarray(2));
  return raw.map((n) => 0.48828125 * (n - 0x800));
}

export function bluetoothNote() {
  const nav = navigator;
  const ua = nav.userAgent || "";
  const ios = /iPad|iPhone|iPod/.test(ua) || (nav.platform === "MacIntel" && nav.maxTouchPoints > 1);
  const safari = /safari/i.test(ua) && !/chrome|android|crios|fxios|edg/i.test(ua);
  if (ios || safari) return "Safari and iOS do not implement Web Bluetooth. The simulated headband on this page still works.";
  if (!nav.bluetooth) return "This browser has no Web Bluetooth. Use desktop Chrome, Edge, or Opera, or the simulated headband.";
  if (!window.isSecureContext) return "Web Bluetooth needs a secure page. http://127.0.0.1 is fine.";
  return "";
}

export async function connectMuse(onTraits) {
  if (!navigator.bluetooth) throw new Error(bluetoothNote() || "Web Bluetooth is unavailable");
  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: [MUSE_SERVICE] }],
    optionalServices: [MUSE_SERVICE],
  });
  const server = await device.gatt.connect();
  const service = await server.getPrimaryService(MUSE_SERVICE);
  const control = await service.getCharacteristic(CONTROL);
  const send = (cmd) => control.writeValue(encodeCommand(cmd));
  const ring = new Float64Array(WINDOW);
  let write = 0;
  let filled = 0;
  await send("h");
  await send("p21");
  const channel = await service.getCharacteristic(AF7);
  await channel.startNotifications();
  channel.addEventListener("characteristicvaluechanged", (event) => {
    const samples = decodeEeg(event.target.value);
    for (const sample of samples) {
      ring[write] = sample;
      write = (write + 1) % WINDOW;
      if (filled < WINDOW) filled += 1;
    }
    if (filled < WINDOW) return;
    const ordered = new Float64Array(WINDOW);
    for (let i = 0; i < WINDOW; i++) ordered[i] = ring[(write + i) % WINDOW];
    const traits = deriveTraits(bandPowers(ordered, EEG_RATE));
    ordered.fill(0);
    onTraits(traits);
  });
  await send("s");
  return {
    name: device.name || "Muse",
    stop() {
      ring.fill(0);
      try { device.gatt.disconnect(); } catch { /* already gone */ }
    },
  };
}
