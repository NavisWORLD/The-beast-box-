import { chunkSections } from './chunker.mjs';
import { LibraryError, checkSize, detectKind, parseEpub, parsePlain, sha256Hex, titleFromName } from './parse.mjs';
import { MAX_APPEND_BYTES, MAX_APPEND_CHUNKS, MAX_TITLE } from './limits.mjs';
import { clean } from './text.mjs';

/**
 * Browser-side half of the library: parse -> chunk -> upload in small batches.
 * Pure functions plus an injected fetch, so the same code runs in unit tests.
 * parsePdf is injected (pdf.js is browser-only and lazy-loaded).
 */

/**
 * @param {{name:string,bytes:Uint8Array}} file
 * @param {{parsePdf?:(b:Uint8Array)=>Promise<{sections:{loc:string,text:string}[],title:string}>,onStage?:(s:string)=>void}} [opts]

 * Turn a File-like {name, bytes} into {kind, title, sections, sha256}.
 */
export async function prepareFile({ name, bytes }, { parsePdf, onStage } = {}) {
  checkSize(bytes.byteLength);
  const kind = detectKind(name, bytes);
  onStage?.('reading');
  let parsed;
  if (kind === 'epub') parsed = await parseEpub(bytes);
  else if (kind === 'pdf') {
    if (!parsePdf) throw new LibraryError('PDF reading is not available here.');
    const r = await parsePdf(bytes); parsed = { sections: r.sections, title: r.title };
  } else parsed = parsePlain(bytes, kind);
  const sha = await sha256Hex(bytes);
  return { kind, title: clean(parsed.title).slice(0, MAX_TITLE) || titleFromName(name), sections: parsed.sections, sha256: sha, bytes: bytes.byteLength };
}

export function preparePaste(text, title) {
  const body = clean(text);
  if (!body) throw new LibraryError('Paste some text first.');
  return { kind: 'paste', title: clean(title).replace(/\n/g, ' ').slice(0, MAX_TITLE) || 'Pasted text', sections: [{ loc: '', text: body }], bytes: new TextEncoder().encode(body).byteLength };
}

/** Split chunks into batches that respect the API's count and byte caps. */
export function batches(chunks) {
  const out = []; let cur = [], bytes = 0;
  for (const c of chunks) {
    const b = (c.text.length + (c.loc || '').length) * 2 + 40;
    if (cur.length && (cur.length >= MAX_APPEND_CHUNKS || bytes + b > MAX_APPEND_BYTES * 0.8)) { out.push(cur); cur = []; bytes = 0; }
    cur.push({ l: c.loc || '', t: c.text }); bytes += b;
  }
  if (cur.length) out.push(cur);
  return out;
}

async function call(fetchImpl, body, signal) {
  const res = await fetchImpl('/api/zeref/library', { method: 'POST', credentials: 'same-origin', cache: 'no-store', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let j = null; try { j = await res.json(); } catch { /* not json */ }
  if (!res.ok) throw new LibraryError(typeof j?.error === 'string' ? j.error : `The library did not accept that (${res.status}).`);
  return j;
}

/**
 * Upload prepared sections. Returns the saved document summary.
 * @param {{kind:string,title:string,sections:{loc:string,text:string}[],sha256?:string,bytes:number}} prepared
 * @param {{fetchImpl?:typeof fetch,onProgress?:(p:{stage:string,done:number,total:number,chunks:number})=>void,signal?:AbortSignal}} [opts]
 */
export async function uploadPrepared(prepared, { fetchImpl = globalThis.fetch, onProgress, signal } = {}) {
  const chunks = chunkSections(prepared.sections);
  if (!chunks.length) throw new LibraryError('No text was found to add.');
  const chars = chunks.reduce((a, c) => a + c.text.length, 0);
  const sha = prepared.sha256 || await sha256Hex(new TextEncoder().encode(prepared.sections.map(s => s.text).join('\n')));
  const { id } = await call(fetchImpl, { action: 'begin', title: prepared.title, kind: prepared.kind, sha256: sha, bytes: prepared.bytes, chars }, signal);
  const parts = batches(chunks);
  try {
    for (let i = 0; i < parts.length; i++) {
      onProgress?.({ stage: 'uploading', done: i, total: parts.length, chunks: chunks.length });
      await call(fetchImpl, { action: 'append', id, seq: i + 1, chunks: parts[i] }, signal);
    }
    const done = await call(fetchImpl, { action: 'finish', id }, signal);
    onProgress?.({ stage: 'saved', done: parts.length, total: parts.length, chunks: chunks.length });
    return { ...done.doc, chunkCount: chunks.length, chars };
  } catch (e) {
    // Do not leave a half-finished document behind.
    await call(fetchImpl, { action: 'delete', id }).catch(() => undefined);
    throw e;
  }
}
