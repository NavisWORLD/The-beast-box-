/**
 * Muse 2 / Muse S Web Bluetooth client and a simulated headband.
 * Band powers stay in this page's memory. Nothing here writes a sample
 * into a cartridge save.
 *
 * Command framing matches muse-js 3.2.0: byte 0 is length-1, then `X${cmd}\n`.
 */

const MUSE_SERVICE = 0xfe8d;
const CONTROL = '273e0001-4c4d-454d-96be-f03bac821358';
const EEG = {
  TP9: '273e0003-4c4d-454d-96be-f03bac821358',
  AF7: '273e0004-4c4d-454d-96be-f03bac821358',
  AF8: '273e0005-4c4d-454d-96be-f03bac821358',
  TP10: '273e0006-4c4d-454d-96be-f03bac821358',
};
export const EEG_RATE = 256;
export const WINDOW = 256;

export function encodeCommand(cmd) {
  const encoded = new TextEncoder().encode(`X${cmd}\n`);
  encoded[0] = encoded.length - 1;
  return encoded;
}

export function decodeUnsigned12BitData(samples) {
  const out = [];
  for (let i = 0; i < samples.length; i++) {
    if (i % 3 === 0) out.push((samples[i] << 4) | (samples[i + 1] >> 4));
    else {
      out.push(((samples[i] & 0xf) << 8) | samples[i + 1]);
      i++;
    }
  }
  return out;
}

export function decodeEegPacket(packet) {
  const bytes = packet instanceof DataView ? new Uint8Array(packet.buffer, packet.byteOffset, packet.byteLength) : packet;
  const sequence = bytes[0] | (bytes[1] << 8);
  const raw = decodeUnsigned12BitData(bytes.subarray(2));
  return { sequence, samples: raw.map((n) => 0.48828125 * (n - 0x800)) };
}

export function bandPowers(samples, sampleRate = EEG_RATE) {
  const n = samples.length;
  const bands = { delta: 0, theta: 0, alpha: 0, beta: 0, gamma: 0 };
  const half = n >> 1;
  for (let k = 1; k < half; k++) {
    const freq = (k * sampleRate) / n;
    if (freq >= 45) break;
    let re = 0;
    let im = 0;
    for (let i = 0; i < n; i++) {
      const ang = (-2 * Math.PI * k * i) / n;
      const s = samples[i];
      re += s * Math.cos(ang);
      im += s * Math.sin(ang);
    }
    const power = re * re + im * im;
    if (freq < 4) bands.delta += power;
    else if (freq < 8) bands.theta += power;
    else if (freq < 13) bands.alpha += power;
    else if (freq < 30) bands.beta += power;
    else bands.gamma += power;
  }
  return bands;
}

export function deriveTraits(bands) {
  const sum = bands.delta + bands.theta + bands.alpha + bands.beta + bands.gamma;
  const round = (part) => (sum > 0 ? Math.max(0, Math.min(100, Math.round((100 * part) / sum))) : 0);
  return { focus: round(bands.beta), calm: round(bands.alpha), spark: round(bands.gamma) };
}

export function mockWindow() {
  const samples = new Float64Array(WINDOW);
  for (let i = 0; i < WINDOW; i++) {
    const t = i / EEG_RATE;
    samples[i] = 30 * Math.sin(2 * Math.PI * 10 * t)
      + 8 * Math.sin(2 * Math.PI * 20 * t)
      + 4 * Math.sin(2 * Math.PI * 40 * t);
  }
  return samples;
}

export function mockTraits() {
  const samples = mockWindow();
  const traits = deriveTraits(bandPowers(samples));
  samples.fill(0);
  return traits;
}

export class MuseLink {
  constructor(onTraits) {
    this.onTraits = onTraits;
    this.device = null;
    this.running = false;
    this.ring = new Float64Array(WINDOW);
    this.filled = 0;
    this.write = 0;
  }

  clear() {
    this.ring.fill(0);
    this.filled = 0;
    this.write = 0;
  }

  push(samples) {
    for (const sample of samples) {
      this.ring[this.write] = sample;
      this.write = (this.write + 1) % WINDOW;
      if (this.filled < WINDOW) this.filled++;
    }
    if (this.filled < WINDOW) return;
    const ordered = new Float64Array(WINDOW);
    for (let i = 0; i < WINDOW; i++) ordered[i] = this.ring[(this.write + i) % WINDOW];
    const traits = deriveTraits(bandPowers(ordered));
    ordered.fill(0);
    this.onTraits(traits);
  }

  async connect({ aux = false } = {}) {
    if (!navigator.bluetooth) throw new Error('Web Bluetooth is not available. Muse plug-and-play needs Chrome or Edge on an HTTPS page, after you click this button. The simulated headband still works.');
    this.device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [MUSE_SERVICE] }],
      optionalServices: [MUSE_SERVICE],
    });
    const server = await this.device.gatt.connect();
    const service = await server.getPrimaryService(MUSE_SERVICE);
    const control = await service.getCharacteristic(CONTROL);
    const send = (cmd) => control.writeValue(encodeCommand(cmd));
    await send('h');
    await send(aux ? 'p20' : 'p21');
    const channel = await service.getCharacteristic(EEG.AF7);
    await channel.startNotifications();
    channel.addEventListener('characteristicvaluechanged', (event) => {
      if (!this.running) return;
      const decoded = decodeEegPacket(event.target.value);
      this.push(decoded.samples);
    });
    await send('s');
    this.running = true;
    this.device.addEventListener('gattserverdisconnected', () => {
      this.running = false;
      this.clear();
    });
  }

  async stop() {
    this.running = false;
    this.clear();
    try { this.device?.gatt?.disconnect(); } catch { /* already gone */ }
  }
}
