import { clean } from './text.mjs';
import { listZip, readZipEntry, ZIP_LIMITS } from './zip.mjs';
import { MAX_FILE_BYTES, MAX_DOC_CHARS, MAX_TITLE } from './limits.mjs';

/**
 * File parsing for the Zeref library. Runs in the browser (and in tests); the
 * server never receives the original file, only the extracted passages.
 * PDF parsing lives in pdf-client.ts because it needs pdf.js.
 */
export class LibraryError extends Error { constructor(message) { super(message); this.name = 'LibraryError'; } }

const EXT = { txt: 'txt', text: 'txt', md: 'md', markdown: 'md', pdf: 'pdf', epub: 'epub' };

export function detectKind(name, head = new Uint8Array(0)) {
  const ext = String(name || '').toLowerCase().split('.').pop();
  const kind = EXT[ext];
  if (!kind) throw new LibraryError('Only .txt, .md, .pdf and .epub files can be added.');
  const sig = String.fromCharCode(...head.subarray(0, 5));
  if (kind === 'pdf' && sig !== '%PDF-') throw new LibraryError('This file is named .pdf but is not a PDF.');
  if (kind === 'epub' && !(head[0] === 0x50 && head[1] === 0x4b)) throw new LibraryError('This file is named .epub but is not an EPUB (zip) file.');
  if ((kind === 'txt' || kind === 'md') && head.subarray(0, 4096).includes(0)) throw new LibraryError('This looks like a binary file, not text.');
  return kind;
}

export function checkSize(bytes) {
  if (!bytes) throw new LibraryError('The file is empty.');
  if (bytes > MAX_FILE_BYTES) throw new LibraryError(`That file is ${(bytes / 1048576).toFixed(1)} MB. The limit is ${MAX_FILE_BYTES / 1048576} MB per file.`);
}

export async function sha256Hex(bytes) {
  const d = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(d), b => b.toString(16).padStart(2, '0')).join('');
}

export function titleFromName(name) {
  return clean(String(name || 'Untitled').replace(/\.[a-z0-9]{1,8}$/i, '').replace(/[_]+/g, ' ')).slice(0, MAX_TITLE) || 'Untitled';
}

function decodeText(bytes) {
  let b = bytes;
  if (b[0] === 0xef && b[1] === 0xbb && b[2] === 0xbf) b = b.subarray(3);
  if (b[0] === 0xff && b[1] === 0xfe) return new TextDecoder('utf-16le').decode(b.subarray(2));
  if (b[0] === 0xfe && b[1] === 0xff) return new TextDecoder('utf-16be').decode(b.subarray(2));
  try { return new TextDecoder('utf-8', { fatal: true }).decode(b); }
  catch { return new TextDecoder('windows-1252').decode(b); }
}

/** .txt / .md: sections split on markdown headings so passages keep a place name. */
export function parsePlain(bytes, kind) {
  const text = clean(decodeText(bytes));
  if (!text) throw new LibraryError('No text was found in that file.');
  if (text.length > MAX_DOC_CHARS) throw new LibraryError(`That text is ${text.length.toLocaleString('en-US')} characters. The limit is ${MAX_DOC_CHARS.toLocaleString('en-US')} per file.`);
  if (kind !== 'md') return { sections: [{ loc: '', text }], title: '' };
  const sections = []; let loc = '', buf = [];
  const push = () => { const t = buf.join('\n').trim(); if (t) sections.push({ loc, text: t }); buf = []; };
  for (const line of text.split('\n')) {
    const h = /^#{1,3}\s+(.+?)\s*#*$/.exec(line);
    if (h) { push(); loc = h[1].slice(0, 70); } else buf.push(line);
  }
  push();
  const first = /^#\s+(.+)$/m.exec(text);
  return { sections, title: first ? first[1].slice(0, MAX_TITLE) : '' };
}

const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—', ndash: '–', hellip: '…', lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”' };
export function htmlToText(html) {
  return String(html)
    .replace(/<(script|style|head|nav)\b[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|h[1-6]|li|tr|blockquote|section|article|pre)>/gi, '\n\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
      if (e[0] === '#') { const n = e[1].toLowerCase() === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return n > 0 && n < 0x110000 ? String.fromCodePoint(n) : ' '; }
      return ENT[e.toLowerCase()] ?? ' ';
    });
}

const attr = (tag, name) => new RegExp(`${name}\\s*=\\s*(["'])(.*?)\\1`, 'i').exec(tag)?.[2];
const dirOf = p => p.includes('/') ? p.slice(0, p.lastIndexOf('/') + 1) : '';
function resolvePath(base, href) {
  const parts = (base + decodeURIComponent(href.split('#')[0])).split('/'); const out = [];
  for (const s of parts) { if (s === '..') out.pop(); else if (s && s !== '.') out.push(s); }
  return out.join('/');
}

export async function parseEpub(bytes) {
  const entries = listZip(bytes);
  const total = entries.reduce((a, e) => a + e.usize, 0);
  if (total > ZIP_LIMITS.MAX_TOTAL_BYTES) throw new LibraryError('This EPUB expands to too much data.');
  const byName = new Map(entries.map(e => [e.name, e]));
  const read = async name => { const e = byName.get(name); if (!e) throw new LibraryError('This EPUB is missing a file it lists: ' + name.slice(0, 60)); return new TextDecoder('utf-8').decode(await readZipEntry(bytes, e)); };
  const container = await read('META-INF/container.xml').catch(e => { if (/DRM|too large|damaged|unzip|compression/.test(e.message)) throw e; throw new LibraryError('This does not look like an EPUB (no container.xml).'); });
  const opfPath = attr(/<rootfile\b[^>]*>/i.exec(container)?.[0] || '', 'full-path');
  if (!opfPath) throw new LibraryError('This EPUB has no package file.');
  const opf = await read(opfPath);
  const base = dirOf(opfPath);
  const title = clean(htmlToText(/<dc:title\b[^>]*>([\s\S]*?)<\/dc:title>/i.exec(opf)?.[1] || '')).slice(0, MAX_TITLE);
  const manifest = new Map();
  for (const m of opf.matchAll(/<item\b[^>]*>/gi)) { const id = attr(m[0], 'id'), href = attr(m[0], 'href'); if (id && href) manifest.set(id, { href, type: attr(m[0], 'media-type') || '' }); }
  const spine = [...opf.matchAll(/<itemref\b[^>]*>/gi)].map(m => attr(m[0], 'idref')).filter(Boolean);
  const sections = []; let chars = 0, n = 0;
  for (const id of spine) {
    const item = manifest.get(id);
    if (!item || !/x?html/i.test(item.type)) continue;
    const path = resolvePath(base, item.href);
    if (!byName.has(path)) continue;
    const html = await read(path);
    const text = clean(htmlToText(html));
    if (!text) continue;
    n++;
    const head = /<h[1-3]\b[^>]*>([\s\S]*?)<\/h[1-3]>/i.exec(html)?.[1];
    const loc = (head ? clean(htmlToText(head)) : '').slice(0, 70) || 'Section ' + n;
    chars += text.length;
    if (chars > MAX_DOC_CHARS) throw new LibraryError(`This book has more than ${MAX_DOC_CHARS.toLocaleString('en-US')} characters of text.`);
    sections.push({ loc, text });
  }
  if (!sections.length) throw new LibraryError('No readable text was found in this EPUB.');
  return { sections, title };
}
