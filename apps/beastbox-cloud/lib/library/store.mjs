/**
 * Zeref's private library (owner only). Storage reuses the Azure Blob account the
 * site already uses for the cosmos folders; nothing new is paid for. Raw passages
 * live ONLY under zeref-library/ and are served only by owner-checked routes.
 * Only titles, counts and hashes ever leave through the manifest views.
 *
 *   zeref-library/manifest.json                  doc metadata (no text)
 *   zeref-library/docs/<id>/chunks-0001.json     {seq, chunks:[{l,t}]}  (raw text, private)
 */
import { createHash, randomBytes } from 'node:crypto';
import { clean } from './text.mjs';
import { buildIndex, search } from './bm25.mjs';
import { ALLOWED_KINDS, CHUNK_MAX, MAX_APPEND_BYTES, MAX_APPEND_CHUNKS, MAX_DOCS, MAX_DOC_CHARS, MAX_LIBRARY_CHARS, MAX_TITLE } from './limits.mjs';

export const LIB_DIR = 'zeref-library';
const MANIFEST = LIB_DIR + '/manifest.json';
const ID = /^[a-f0-9]{24}$/;
const SHA = /^[a-f0-9]{64}$/;
const sha256 = s => createHash('sha256').update(s).digest('hex');
const fail = (status, error) => Object.assign(new Error(error), { status, publicMessage: error });
const chunkName = (id, seq) => `${LIB_DIR}/docs/${id}/chunks-${String(seq).padStart(4, '0')}.json`;

/** Adapter over lib/cosmos/azure-blob.mjs so tests can inject memory. */
export function azureAdapter(cfg, blob) {
  return {
    get: n => blob.getBlob(cfg, n),
    put: (n, t, o) => blob.putBlob(cfg, n, t, o),
    list: p => blob.listBlobs(cfg, p, { max: 4000 }),
    async del(n) { const b = await blob.getBlob(cfg, n); if (b) await blob.deleteBlob(cfg, n, { ifMatch: b.etag }); },
    ensure: () => blob.ensureContainer(cfg),
  };
}

export function memoryAdapter() {
  const m = new Map(); let v = 0;
  return {
    m,
    async get(n) { const b = m.get(n); return b ? { text: b.text, etag: b.etag } : null; },
    async put(n, t, { ifMatch, ifNoneMatch } = {}) {
      const cur = m.get(n);
      if (ifNoneMatch === '*' && cur) throw Object.assign(new Error('exists'), { status: 412 });
      if (ifMatch && (!cur || cur.etag !== ifMatch)) throw Object.assign(new Error('etag'), { status: 412 });
      const etag = '"' + (++v) + '"'; m.set(n, { text: t, etag }); return etag;
    },
    async list(p) { return [...m.keys()].filter(k => k.startsWith(p)).sort(); },
    async del(n) { m.delete(n); },
    async ensure() { return true; },
  };
}

async function readManifest(store) {
  const b = await store.get(MANIFEST);
  if (!b) return { m: { schema: 'zeref-library-manifest-v1', updated_at: null, docs: [] }, etag: null };
  let m; try { m = JSON.parse(b.text); } catch { throw fail(500, 'The library index is unreadable.'); }
  if (!Array.isArray(m.docs)) m.docs = [];
  return { m, etag: b.etag };
}
async function writeManifest(store, m, etag) {
  m.updated_at = new Date().toISOString();
  try { await store.put(MANIFEST, JSON.stringify(m), etag ? { ifMatch: etag } : { ifNoneMatch: '*' }); }
  catch (e) { if (e.status === 409 || e.status === 412) throw fail(409, 'The library changed in another tab. Try again.'); throw e; }
}
/** Optimistic update with a few retries (single owner, but two tabs happen). */
async function mutate(store, fn) {
  for (let i = 0; i < 4; i++) {
    const { m, etag } = await readManifest(store);
    const out = await fn(m);
    try { await writeManifest(store, m, etag); return out; }
    catch (e) { if (e.status !== 409 || i === 3) throw e; }
  }
}

export const publicDoc = d => ({
  id: d.id, title: d.title, kind: d.kind, status: d.status, bytes: d.bytes, chars: d.chars, chunks: d.chunks,
  sha256: d.sha256, content_sha256: d.content_sha256 || null, created_at: d.created_at,
  training_approved: d.training_approved === true, training_approved_at: d.training_approved_at || null,
});
const totals = docs => ({
  docs: docs.length,
  chars: docs.reduce((a, d) => a + (d.chars || 0), 0),
  chunks: docs.reduce((a, d) => a + (d.chunks || 0), 0),
});

export async function listLibrary(store) {
  const { m } = await readManifest(store);
  return { docs: m.docs.map(publicDoc), totals: totals(m.docs.filter(d => d.status === 'ready')), updated_at: m.updated_at };
}

export async function beginDoc(store, input) {
  const title = clean(input?.title).replace(/\n/g, ' ').slice(0, MAX_TITLE);
  if (!title) throw fail(400, 'Give the document a title.');
  if (!ALLOWED_KINDS.includes(input?.kind)) throw fail(400, 'Unsupported file type.');
  if (!SHA.test(String(input?.sha256 || ''))) throw fail(400, 'Missing file hash.');
  const bytes = Number(input?.bytes), chars = Number(input?.chars);
  if (!Number.isSafeInteger(bytes) || bytes < 0 || !Number.isSafeInteger(chars) || chars < 1) throw fail(400, 'Invalid document size.');
  if (chars > MAX_DOC_CHARS) throw fail(413, `Too long: the limit is ${MAX_DOC_CHARS.toLocaleString('en-US')} characters per document.`);
  await store.ensure?.();
  return mutate(store, m => {
    const live = m.docs.filter(d => d.status !== 'deleted');
    if (live.length >= MAX_DOCS) throw fail(409, `The library holds at most ${MAX_DOCS} documents. Remove one first.`);
    if (live.some(d => d.status === 'ready' && d.sha256 === input.sha256)) throw fail(409, 'This exact file is already in the library.');
    if (totals(live).chars + chars > MAX_LIBRARY_CHARS) throw fail(413, `The library is full (${MAX_LIBRARY_CHARS.toLocaleString('en-US')} characters). Remove a document first.`);
    const id = randomBytes(12).toString('hex');
    const doc = { id, title, kind: input.kind, status: 'uploading', bytes, chars_declared: chars, chars: 0, chunks: 0, seqs: [], sha256: input.sha256, created_at: new Date().toISOString(), training_approved: false };
    // A half-finished upload from an earlier try is cleaned up when a new one starts.
    m.docs = m.docs.filter(d => !(d.status === 'uploading' && Date.now() - Date.parse(d.created_at) > 6 * 3600e3));
    m.docs.push(doc);
    return { id };
  });
}

export function validateChunks(chunks) {
  if (!Array.isArray(chunks) || !chunks.length || chunks.length > MAX_APPEND_CHUNKS) throw fail(400, `Send 1 to ${MAX_APPEND_CHUNKS} passages per request.`);
  let bytes = 0; const out = [];
  for (const c of chunks) {
    if (!c || typeof c !== 'object' || Array.isArray(c) || typeof c.t !== 'string') throw fail(400, 'Invalid passage.');
    const t = clean(c.t), l = typeof c.l === 'string' ? clean(c.l).replace(/\n/g, ' ').slice(0, 80) : '';
    if (!t) continue;
    if (t.length > CHUNK_MAX + 200) throw fail(400, 'A passage is too long.');
    bytes += t.length * 2;
    out.push({ l, t });
  }
  if (bytes > MAX_APPEND_BYTES) throw fail(413, 'That batch is too large.');
  if (!out.length) throw fail(400, 'No text in that batch.');
  return out;
}

export async function appendChunks(store, { id, seq, chunks }) {
  if (!ID.test(String(id))) throw fail(400, 'Invalid document id.');
  if (!Number.isSafeInteger(seq) || seq < 1 || seq > 20000) throw fail(400, 'Invalid batch number.');
  const clean_ = validateChunks(chunks);
  const { m } = await readManifest(store);
  const doc = m.docs.find(d => d.id === id);
  if (!doc || doc.status !== 'uploading') throw fail(404, 'That upload is not open.');
  if (doc.seqs.includes(seq)) return { ok: true, already: true, seq };
  const add = clean_.reduce((a, c) => a + c.t.length, 0);
  if (doc.chars + add > Math.min(MAX_DOC_CHARS, Math.ceil(doc.chars_declared * 1.05) + 2000)) throw fail(413, 'More text arrived than the file declared.');
  await store.put(chunkName(id, seq), JSON.stringify({ seq, chunks: clean_ }));
  await mutate(store, mm => {
    const d = mm.docs.find(x => x.id === id);
    if (!d || d.status !== 'uploading') throw fail(404, 'That upload is not open.');
    if (!d.seqs.includes(seq)) { d.seqs.push(seq); d.chars += add; d.chunks += clean_.length; }
  });
  return { ok: true, seq, chunks: clean_.length };
}

export async function finishDoc(store, id) {
  if (!ID.test(String(id))) throw fail(400, 'Invalid document id.');
  const { m } = await readManifest(store);
  const doc = m.docs.find(d => d.id === id);
  if (!doc || doc.status !== 'uploading') throw fail(404, 'That upload is not open.');
  const seqs = [...doc.seqs].sort((a, b) => a - b);
  if (!seqs.length || seqs.some((s, i) => s !== i + 1)) throw fail(409, 'Some batches are missing. Upload the file again.');
  const hash = createHash('sha256');
  for (const s of seqs) {
    const b = await store.get(chunkName(id, s));
    if (!b) throw fail(409, 'A stored batch is missing. Upload the file again.');
    for (const c of JSON.parse(b.text).chunks) hash.update(c.t + '\n');
  }
  const content = hash.digest('hex');
  return mutate(store, mm => {
    const d = mm.docs.find(x => x.id === id);
    if (!d || d.status !== 'uploading') throw fail(404, 'That upload is not open.');
    d.status = 'ready'; d.content_sha256 = content; delete d.chars_declared;
    return publicDoc(d);
  });
}

export async function deleteDoc(store, id) {
  if (!ID.test(String(id))) throw fail(400, 'Invalid document id.');
  const names = await store.list(`${LIB_DIR}/docs/${id}/`);
  for (const n of names) await store.del(n);
  await mutate(store, m => { m.docs = m.docs.filter(d => d.id !== id); });
  cache.clear();
  return { ok: true };
}

export async function setTraining(store, id, approved) {
  if (!ID.test(String(id))) throw fail(400, 'Invalid document id.');
  if (typeof approved !== 'boolean') throw fail(400, 'approved must be true or false.');
  return mutate(store, m => {
    const d = m.docs.find(x => x.id === id && x.status === 'ready');
    if (!d) throw fail(404, 'No such document.');
    d.training_approved = approved; d.training_approved_at = approved ? new Date().toISOString() : null;
    return publicDoc(d);
  });
}

async function loadDocChunks(store, d) {
  const out = [];
  for (const s of [...d.seqs].sort((a, b) => a - b)) {
    const b = await store.get(chunkName(d.id, s));
    if (!b) continue;
    for (const c of JSON.parse(b.text).chunks) out.push({ loc: c.l || '', text: c.t });
  }
  return out;
}

const cache = new Map();
async function indexFor(store, m) {
  const ready = m.docs.filter(d => d.status === 'ready');
  const key = ready.map(d => d.id + ':' + d.chunks).join(',') + '|' + (m.updated_at || '');
  const hit = cache.get('idx');
  if (hit && hit.key === key) return hit.index;
  const docs = [];
  for (const d of ready) docs.push({ id: d.id, title: d.title, chunks: await loadDocChunks(store, d) });
  const index = buildIndex(docs);
  cache.clear(); cache.set('idx', { key, index });
  return index;
}

/** @param {any} store @param {string} query @param {{k?:number,docIds?:string[]|null}} [opts] */
export async function searchLibrary(store, query, { k = 3, docIds = null } = {}) {
  const q = clean(query).slice(0, 1000);
  if (!q) throw fail(400, 'Type something to look up.');
  const { m } = await readManifest(store);
  if (!m.docs.some(d => d.status === 'ready')) return { hits: [], searched: 0, chunks: 0 };
  const index = await indexFor(store, m);
  const ids = Array.isArray(docIds) ? docIds.filter(x => ID.test(String(x))) : null;
  const hits = search(index, q, { k, docIds: ids }).map(h => ({
    doc_id: h.docId, title: h.title, index: h.index, loc: h.loc, text: h.text, score: h.score, sha256: sha256(h.text),
  }));
  return { hits, searched: new Set(index.passages.map(p => p.docId)).size, chunks: index.n };
}

/** Public-safe view: titles, counts and hashes only. Never any text. */
export async function trainingManifest(store) {
  const { m } = await readManifest(store);
  const docs = m.docs.filter(d => d.status === 'ready' && d.training_approved === true).map(d => ({
    id: d.id, title: d.title, kind: d.kind, chunks: d.chunks, chars: d.chars, sha256: d.sha256, content_sha256: d.content_sha256, approved_at: d.training_approved_at,
  }));
  return {
    schema: 'zeref-library-training-queue-v1', default: 'off', scope: 'owner-only', redistribution: 'none',
    note: 'Opt-in per document. Approval only makes a document ELIGIBLE; it still has to pass the fair promotion gate (Gate v2) like any other training data.',
    docs, totals: { docs: docs.length, chunks: docs.reduce((a, d) => a + d.chunks, 0), chars: docs.reduce((a, d) => a + d.chars, 0) },
  };
}

/** Raw rows for an approved document; CI/private runner use only, behind ZEREF_LIBRARY_TRAINING=on. */
export async function approvedTrainingChunks(store) {
  const { m } = await readManifest(store);
  const rows = [];
  for (const d of m.docs.filter(x => x.status === 'ready' && x.training_approved === true)) {
    const chunks = await loadDocChunks(store, d);
    chunks.forEach((c, i) => rows.push({ doc_id: d.id, title: d.title, index: i, loc: c.loc, text: c.text, sha256: sha256(c.text) }));
  }
  return rows;
}
