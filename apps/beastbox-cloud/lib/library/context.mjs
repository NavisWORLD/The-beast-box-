import { bestWindow, clean } from './text.mjs';
import { LIBRARY_PASSAGES, PASSAGE_CHARS } from './limits.mjs';

/**
 * Turn search hits into the verbatim notes the brain gets for one turn.
 * Excerpts are cut from the stored passage (best keyword window), never reworded.
 * `used` is what the UI shows as RECORDED; text stays in memory, never in saved chat logs.
 */
export function libraryContext(hits, query, { passages = LIBRARY_PASSAGES, chars = PASSAGE_CHARS } = {}) {
  const used = [];
  for (const h of (Array.isArray(hits) ? hits : []).slice(0, passages)) {
    const excerpt = bestWindow(h.text, query, chars);
    if (!excerpt) continue;
    used.push({ docId: h.doc_id ?? h.docId, title: clean(h.title).slice(0, 80), loc: clean(h.loc).slice(0, 70), excerpt, sha256: h.sha256 || '' });
  }
  const text = used.map(u => `[${u.title}${u.loc ? ', ' + u.loc : ''}] ${u.excerpt}`).join(' | ');
  return { text, used };
}
