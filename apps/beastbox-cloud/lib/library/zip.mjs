/**
 * Minimal, bounded ZIP reader (stored + deflate) for EPUB. Uses the platform's
 * DecompressionStream, so no dependency and no server compute. Refuses zip
 * bombs: entry count, per-entry and total uncompressed size are capped.
 */
const MAX_ENTRIES = 6000, MAX_ENTRY_BYTES = 40 * 1024 * 1024, MAX_TOTAL_BYTES = 150 * 1024 * 1024;

const u16 = (b, o) => b[o] | (b[o + 1] << 8);
const u32 = (b, o) => (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0;

export function listZip(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 22) throw new Error('This is not a valid EPUB (zip) file.');
  let eocd = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 22 - 65535); i--) {
    if (u32(bytes, i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('This is not a valid EPUB (zip) file.');
  const count = u16(bytes, eocd + 10), dirSize = u32(bytes, eocd + 12), dirOff = u32(bytes, eocd + 16);
  if (count > MAX_ENTRIES) throw new Error('This EPUB has too many files.');
  if (dirOff + dirSize > bytes.length) throw new Error('This EPUB is damaged (bad zip directory).');
  const entries = [];
  let p = dirOff;
  for (let n = 0; n < count; n++) {
    if (u32(bytes, p) !== 0x02014b50) throw new Error('This EPUB is damaged (bad zip entry).');
    const flags = u16(bytes, p + 8), method = u16(bytes, p + 10);
    const csize = u32(bytes, p + 20), usize = u32(bytes, p + 24);
    const nlen = u16(bytes, p + 28), xlen = u16(bytes, p + 30), clen = u16(bytes, p + 32), off = u32(bytes, p + 42);
    const name = new TextDecoder('utf-8').decode(bytes.subarray(p + 46, p + 46 + nlen));
    entries.push({ name, method, csize, usize, off, encrypted: (flags & 1) === 1 });
    p += 46 + nlen + xlen + clen;
  }
  return entries;
}

export async function readZipEntry(bytes, entry) {
  if (entry.encrypted) throw new Error('This EPUB is encrypted (DRM). Only DRM-free books can be added.');
  if (entry.usize > MAX_ENTRY_BYTES) throw new Error('An entry in this EPUB is too large.');
  const o = entry.off;
  if (u32(bytes, o) !== 0x04034b50) throw new Error('This EPUB is damaged (bad local header).');
  const start = o + 30 + u16(bytes, o + 26) + u16(bytes, o + 28);
  const raw = bytes.subarray(start, start + entry.csize);
  if (entry.method === 0) return raw;
  if (entry.method !== 8) throw new Error('This EPUB uses an unsupported zip compression.');
  if (typeof DecompressionStream === 'undefined') throw new Error('This browser cannot unzip EPUB files. Try Chrome, Safari 16.4+ or Firefox.');
  const stream = new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  const reader = stream.getReader();
  const parts = []; let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > MAX_ENTRY_BYTES) { await reader.cancel(); throw new Error('An entry in this EPUB expands too much.'); }
    parts.push(value);
  }
  const out = new Uint8Array(total); let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
}

export const ZIP_LIMITS = Object.freeze({ MAX_ENTRIES, MAX_ENTRY_BYTES, MAX_TOTAL_BYTES });
