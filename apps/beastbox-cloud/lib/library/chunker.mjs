import { clean, splitSentences, splitLong } from './text.mjs';
import { CHUNK_TARGET, CHUNK_MAX } from './limits.mjs';

/**
 * Split text into passages of about `target` characters on paragraph then
 * sentence boundaries. `sections` is [{loc, text}] (a PDF page, an EPUB chapter,
 * or one pasted block); every chunk keeps its `loc`. Deterministic.
 * @returns {{loc:string,text:string}[]}
 */
export function chunkSections(sections, { target = CHUNK_TARGET, max = CHUNK_MAX } = {}) {
  const out = [];
  for (const sec of sections) {
    const loc = String(sec?.loc ?? '').slice(0, 80);
    const text = clean(sec?.text);
    if (!text) continue;
    let cur = '';
    const flush = () => { const t = cur.trim(); if (t) out.push({ loc, text: t }); cur = ''; };
    for (const para of text.split(/\n{2,}/)) {
      const units = para.length <= max ? [para] : splitSentences(para).flatMap(s => splitLong(s, max));
      for (const u of units) {
        const sep = cur ? (units.length === 1 ? '\n\n' : ' ') : '';
        if (cur && cur.length + sep.length + u.length > target) flush();
        cur += (cur ? (units.length === 1 ? '\n\n' : ' ') : '') + u;
        if (cur.length >= max) flush();
      }
    }
    flush();
  }
  return out;
}

export function chunkText(text, loc = '') { return chunkSections([{ loc, text }]); }
