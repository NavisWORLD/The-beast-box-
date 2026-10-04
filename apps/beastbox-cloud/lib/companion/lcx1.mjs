/**
 * LCX1 mailbox encoder. Byte-compatible with tools/lc_mailbox.py.
 * Raw EEG samples are not an input. Only a BCP1 profile and three derived traits.
 */
export const MAILBOX_OFFSET = 24832;
export const MAILBOX_BYTES = 644;
export const MAIL_BODY = 640;
export const GROWTH_OFFSET = 25476;
export const GROWTH_BYTES = 64;
export const SRAM_SIZE = 32768;
export const FAMILIES = ['nebula', 'aurora', 'void', 'plasma', 'memory', 'signal', 'starlight'];
export const FAMILY_LOOK = ['nebula', 'aurora', 'nebula', 'starlight', 'starlight', 'aurora', 'starlight'];
export const LOOKS = { nebula: 0, aurora: 1, starlight: 2 };
export const SPECIES = ['NEBULA', 'AURORA', 'VOID', 'PLASMA', 'MEMORY', 'SIGNAL', 'STARLIGHT'];
export const FIXTURE = { world: 'EARTH', evolution: 0.25, biosphere: 0.5, lifeEvents: 1, focus: 40, calm: 70, spark: 15 };

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(bytes) {
  let c = 0xffffffff;
  for (const b of bytes) c = (CRC_TABLE[(c ^ b) & 255] ^ (c >>> 8)) >>> 0;
  return (c ^ 0xffffffff) >>> 0;
}

export function fnv1a(text) {
  let h = 2166136261;
  for (const byte of new TextEncoder().encode(text)) h = Math.imul(h ^ byte, 16777619) >>> 0;
  return h >>> 0;
}

function floorDiv(a, b) {
  return Math.floor(a / b);
}

function* generator(seed, domain) {
  let state = fnv1a(`1|${domain}|${seed}`) || 0x6d2b79f5;
  while (true) {
    state = (state ^ (state << 13)) >>> 0;
    state = (state ^ (state >>> 17)) >>> 0;
    state = (state ^ (state << 5)) >>> 0;
    yield state / 4294967296;
  }
}

export function expectedGenesis(seed) {
  const rng = generator(seed, 'stats');
  const stats = Array(10).fill(50);
  for (let n = 0; n < 270; n++) {
    const source = Math.trunc(rng.next().value * 10);
    const target = Math.trunc(rng.next().value * 10);
    if (source !== target && stats[source] > 20 && stats[target] < 80) {
      stats[source] -= 1;
      stats[target] += 1;
    }
  }
  const trng = generator(seed, 'temperament');
  const temper = Array.from({ length: 5 }, () => Math.trunc(20 + trng.next().value * 61));
  const naming = generator(seed, 'name');
  const stems = ['Neb', 'Lum', 'Ori', 'Vexa', 'Astr', 'Phera', 'Glima', 'Zori', 'Mira', 'Cosmi'];
  const ends = ['by', 'io', 'ix', 'a', 'on', 'ora', 'u', 'ra', 'yx', 'iri'];
  const name = stems[Math.trunc(naming.next().value * stems.length)] + ends[Math.trunc(naming.next().value * ends.length)];
  return { stats, temper, name };
}

export function livingSeed(world, evolution, biosphere, lifeEvents) {
  const raw = String(world).toUpperCase().replace(/[^A-Z0-9]/g, '');
  const w = raw || 'WORLD';
  const evo = Math.trunc(Math.max(0, Number(evolution)) * 1000);
  const bio = Math.trunc(Math.max(0, Math.min(1, Number(biosphere))) * 1000);
  const life = Math.trunc(Math.max(0, Number(lifeEvents)));
  return `lu1|${w}|${evo}|${bio}|${life}`;
}

export function applyTraits(temper, focus, calm, spark) {
  const shifts = [
    floorDiv(calm - 50, 5),
    floorDiv(spark - 50, 5),
    floorDiv(spark - 40, 6),
    floorDiv(calm - 40, 5),
    floorDiv(focus - 50, 5),
  ];
  return temper.map((v, i) => Math.max(20, Math.min(80, v + shifts[i])));
}

export function buildBcp1({ family, stats, temper, hue, publicId }) {
  if (family < 0 || family > 6) throw new Error('family out of range');
  if (stats.reduce((a, b) => a + b, 0) !== 500) throw new Error('BCP1 budget');
  if ([...stats, ...temper].some((x) => x < 20 || x > 80)) throw new Error('BCP1 range');
  if (!publicId) throw new Error('public id is zero');
  const p = new Uint8Array(64);
  p.set([0x42, 0x43, 0x50, 0x31, 1, family, LOOKS[FAMILY_LOOK[family]], 0]);
  p.set(stats, 8);
  p.set(temper, 18);
  p[23] = hue & 0xff;
  p[24] = publicId & 255;
  p[25] = (publicId >>> 8) & 255;
  p[26] = (publicId >>> 16) & 255;
  p[27] = (publicId >>> 24) & 255;
  const sum = crc32(p.subarray(0, 60));
  p[60] = sum & 255;
  p[61] = (sum >>> 8) & 255;
  p[62] = (sum >>> 16) & 255;
  p[63] = (sum >>> 24) & 255;
  return p;
}

function traitCheck(focus, calm, spark) {
  for (const [name, value] of [['focus', focus], ['calm', calm], ['spark', spark]]) {
    if (!Number.isInteger(value) || value < 0 || value > 100) throw new Error(`${name} must be an integer 0..100`);
  }
}

export function livingProfile({ world, evolution, biosphere, lifeEvents, focus, calm, spark }) {
  traitCheck(focus, calm, spark);
  const seed = livingSeed(world, evolution, biosphere, lifeEvents);
  const family = fnv1a(seed) % 7;
  const genesis = expectedGenesis(seed);
  const temper = applyTraits(genesis.temper, focus, calm, spark);
  const hue = Math.max(-32, Math.min(31, floorDiv(spark - calm, 2)));
  const publicId = fnv1a(`identity|1|${seed}`) || 1;
  const gameSeed = fnv1a(`lost-cosmos|${seed}`) || 1;
  const callsign = (String(world).toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12)) || 'LIVING';
  const bcp1 = buildBcp1({ family, stats: genesis.stats, temper, hue, publicId });
  return { bcp1, gameSeed, callsign, family, species: 128 + family, speciesName: SPECIES[family], publicId, focus, calm, spark, seed, hue };
}

export function beastProfile({ seed, familyName, hue = 0, focus = 50, calm = 50, spark = 50 }) {
  traitCheck(focus, calm, spark);
  const family = FAMILIES.indexOf(familyName);
  if (family < 0) throw new Error('unknown family');
  const genesis = expectedGenesis(seed);
  const publicId = fnv1a(`identity|1|${seed}`) || 1;
  const gameSeed = fnv1a(`lost-cosmos|${seed}`) || 1;
  const bcp1 = buildBcp1({ family, stats: genesis.stats, temper: genesis.temper, hue, publicId });
  const callsign = genesis.name.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12) || 'BEAST';
  return { bcp1, gameSeed, callsign, family, species: 128 + family, speciesName: SPECIES[family], publicId, focus, calm, spark, seed, hue, name: genesis.name };
}

export function profileFromBcp1(bytes, { focus = 50, calm = 50, spark = 50, callsign = 'BEAST', gameSeed = 0 } = {}) {
  traitCheck(focus, calm, spark);
  if (!(bytes instanceof Uint8Array) || bytes.length !== 64) throw new Error('BCP1 must be 64 bytes');
  if (bytes[0] !== 0x42 || bytes[1] !== 0x43 || bytes[2] !== 0x50 || bytes[3] !== 0x31 || bytes[4] !== 1) throw new Error('BCP1 header');
  const family = bytes[5];
  if (family > 6 || bytes[6] > 2 || bytes[7] !== 0) throw new Error('BCP1 family');
  for (let i = 28; i < 60; i++) if (bytes[i]) throw new Error('BCP1 reserved');
  const stats = [...bytes.subarray(8, 18)];
  const temper = [...bytes.subarray(18, 23)];
  if (stats.reduce((a, b) => a + b, 0) !== 500 || [...stats, ...temper].some((x) => x < 20 || x > 80)) throw new Error('BCP1 budget');
  const publicId = (bytes[24] | (bytes[25] << 8) | (bytes[26] << 16) | (bytes[27] << 24)) >>> 0;
  if (!publicId) throw new Error('public id is zero');
  const sum = crc32(bytes.subarray(0, 60));
  const got = (bytes[60] | (bytes[61] << 8) | (bytes[62] << 16) | (bytes[63] << 24)) >>> 0;
  if (sum !== got) throw new Error('BCP1 crc');
  const hue = (bytes[23] << 24) >> 24;
  const call = String(callsign).toUpperCase().replace(/[^A-Z0-9 ]/g, '').slice(0, 12) || 'BEAST';
  return {
    bcp1: bytes.slice(), gameSeed: (gameSeed >>> 0) || publicId, callsign: call, family,
    species: 128 + family, speciesName: SPECIES[family], publicId, focus, calm, spark, seed: 'bcp1', hue,
  };
}

export function profileFromBeastJson(details, traits = {}) {
  if (!details || details.schema !== 'beast-cage-creature-v1' || details.version !== 1) throw new Error('Beast Box schema');
  if (typeof details.seed !== 'string' || !details.seed) throw new Error('Beast Box seed');
  const hue = Number(details.appearance?.hueShift || 0);
  const profile = beastProfile({
    seed: details.seed,
    familyName: details.family,
    hue,
    focus: traits.focus ?? 50,
    calm: traits.calm ?? 50,
    spark: traits.spark ?? 50,
  });
  const genesis = expectedGenesis(details.seed);
  if (details.game?.stats) {
    const names = ['hp', 'energy', 'signal', 'memory', 'resonance', 'agility', 'chaos', 'stability', 'curiosity', 'evolution'];
    for (let i = 0; i < names.length; i++) {
      if (details.game.stats[names[i]] !== genesis.stats[i]) throw new Error('Beast Box stat mismatch');
    }
  }
  if (details.temperament) {
    const keys = ['curiosity', 'energy', 'playfulness', 'caution', 'independence'];
    for (let i = 0; i < keys.length; i++) {
      if (details.temperament[keys[i]] !== undefined && details.temperament[keys[i]] !== genesis.temper[i]) {
        throw new Error('Beast Box temperament mismatch');
      }
    }
  }
  return profile;
}

export function buildMailbox(profile) {
  const buf = new Uint8Array(MAILBOX_BYTES);
  buf.set([0x4c, 0x43, 0x58, 0x31, 1, 1, profile.focus, profile.calm, profile.spark], 0);
  const seed = profile.gameSeed >>> 0;
  buf[10] = seed & 255;
  buf[11] = (seed >>> 8) & 255;
  buf[12] = (seed >>> 16) & 255;
  buf[13] = (seed >>> 24) & 255;
  const call = new TextEncoder().encode(profile.callsign).slice(0, 12);
  buf.set(call, 14);
  if (profile.bcp1.length !== 64) throw new Error('BCP1 must be 64 bytes');
  buf.set(profile.bcp1, 32);
  const sum = crc32(buf.subarray(0, MAIL_BODY));
  buf[640] = sum & 255;
  buf[641] = (sum >>> 8) & 255;
  buf[642] = (sum >>> 16) & 255;
  buf[643] = (sum >>> 24) & 255;
  return buf;
}

export function buildSave(profile) {
  const mail = buildMailbox(profile);
  if (MAILBOX_OFFSET + mail.length > GROWTH_OFFSET) throw new Error('mailbox collides with the cage record');
  const sav = new Uint8Array(SRAM_SIZE);
  sav.fill(0xff);
  sav.set(mail, MAILBOX_OFFSET);
  return sav;
}

function write32(buf, offset, value) {
  const n = value >>> 0;
  buf[offset] = n & 255;
  buf[offset + 1] = (n >>> 8) & 255;
  buf[offset + 2] = (n >>> 16) & 255;
  buf[offset + 3] = (n >>> 24) & 255;
}

/** LCG1 sits in the 124-byte gap before the first V11.1 manual slot. */
export function buildGrowth({ publicId, epoch = 0, layer = 0, points = 0, memoryCrc = 0, chainCrc = 0, trade = false, grown = false }) {
  if (!publicId) throw new Error('public id is zero');
  const epochNum = typeof epoch === 'bigint' ? epoch : BigInt(epoch);
  if (epochNum < 0n || epochNum > 0xffffffffn) throw new Error('epoch does not fit the cartridge field');
  if (!Number.isInteger(layer) || layer < 0 || layer > 999) throw new Error('growth layer');
  if (!Number.isInteger(points) || points < 0 || points > 999) throw new Error('growth points');
  const buf = new Uint8Array(GROWTH_BYTES);
  buf.set([0x4c, 0x43, 0x47, 0x31, 1, (trade ? 1 : 0) | (grown ? 2 : 0)], 0);
  write32(buf, 8, Number(epochNum));
  buf[12] = layer & 255;
  buf[13] = (layer >>> 8) & 255;
  buf[14] = points & 255;
  buf[15] = (points >>> 8) & 255;
  write32(buf, 16, memoryCrc);
  write32(buf, 20, chainCrc);
  write32(buf, 24, publicId);
  write32(buf, 60, crc32(buf.subarray(0, 60)));
  return buf;
}

/**
 * Optional 32x32 4bpp art inside the LCX1 body. buildSave stays flag 1 only.
 * Palette is 16 BGR555 words. Tiles are 512 bytes, GBA 4-tile-wide order.
 */
export function attachFieldArt(sav, art) {
  if (!(sav instanceof Uint8Array) || sav.length !== SRAM_SIZE) throw new Error('save size');
  if (!art || art.tiles?.length !== 512 || art.palette?.length !== 16) throw new Error('field art');
  const out = sav.slice();
  const o = MAILBOX_OFFSET;
  if (out[o] !== 0x4c || out[o + 1] !== 0x43 || out[o + 2] !== 0x58 || out[o + 3] !== 0x31 || out[o + 4] !== 1) {
    throw new Error('field art needs an LCX1 mailbox');
  }
  const flags = out[o + 5];
  if (flags & ~7) throw new Error('mailbox flags are not a cage record');
  out[o + 5] = flags | 2;
  for (let i = 0; i < 16; i++) {
    const word = art.palette[i] & 0xffff;
    out[o + 96 + i * 2] = word & 255;
    out[o + 96 + i * 2 + 1] = (word >> 8) & 255;
  }
  out.set(art.tiles, o + 128);
  const sum = crc32(out.subarray(o, o + MAIL_BODY));
  out[o + 640] = sum & 255;
  out[o + 641] = (sum >>> 8) & 255;
  out[o + 642] = (sum >>> 16) & 255;
  out[o + 643] = (sum >>> 24) & 255;
  return out;
}

export function attachGrowth(sav, growth) {
  if (!(sav instanceof Uint8Array) || sav.length !== SRAM_SIZE) throw new Error('save size');
  if (!(growth instanceof Uint8Array) || growth.length !== GROWTH_BYTES) throw new Error('growth size');
  if (GROWTH_OFFSET + GROWTH_BYTES > 25600) throw new Error('growth collides with the reserved LCM1 region');
  const out = sav.slice();
  out.set(growth, GROWTH_OFFSET);
  return out;
}

export function fixtureSave() {
  const profile = livingProfile(FIXTURE);
  return { sav: buildSave(profile), profile };
}

function hex(n) {
  return (n >>> 0).toString(16).padStart(8, '0');
}

async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function read32(buf, offset) {
  return (buf[offset] | (buf[offset + 1] << 8) | (buf[offset + 2] << 16) | (buf[offset + 3] << 24)) >>> 0;
}

/** Inverse of buildMailbox. Rejects a bad magic or checksum. */
export function parseMailbox(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < MAILBOX_BYTES) throw new Error('LCX1 mailbox is short');
  const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
  if (magic !== 'LCX1' || bytes[4] !== 1) throw new Error('Not an LCX1 mailbox');
  const sum = crc32(bytes.subarray(0, MAIL_BODY));
  if (sum !== read32(bytes, 640)) throw new Error('LCX1 crc');
  let callsign = '';
  for (let i = 14; i < 26; i++) if (bytes[i]) callsign += String.fromCharCode(bytes[i]);
  const bcp1 = bytes.slice(32, 96);
  return {
    focus: bytes[6],
    calm: bytes[7],
    spark: bytes[8],
    gameSeed: read32(bytes, 10),
    callsign: callsign.trim(),
    bcp1,
    publicId: read32(bcp1, 24),
    family: bcp1[5],
  };
}

export function parseGrowth(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < GROWTH_BYTES) return null;
  const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
  if (magic !== 'LCG1' || bytes[4] !== 1) return null;
  if (crc32(bytes.subarray(0, 60)) !== read32(bytes, 60)) throw new Error('LCG1 crc');
  return {
    layer: bytes[12] | (bytes[13] << 8),
    points: bytes[14] | (bytes[15] << 8),
    publicId: read32(bytes, 24),
    grown: (bytes[5] & 2) !== 0,
    trade: (bytes[5] & 1) !== 0,
  };
}

export function parseSave(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length !== SRAM_SIZE) throw new Error('save size');
  const mail = parseMailbox(bytes.subarray(MAILBOX_OFFSET, MAILBOX_OFFSET + MAILBOX_BYTES));
  const growth = parseGrowth(bytes.subarray(GROWTH_OFFSET, GROWTH_OFFSET + GROWTH_BYTES));
  return { ...mail, growth };
}

