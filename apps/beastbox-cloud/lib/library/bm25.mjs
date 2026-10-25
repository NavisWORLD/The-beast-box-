import { tokenize } from './text.mjs';

/**
 * Plain BM25 keyword retrieval over uploaded passages. Deterministic: no model,
 * no embeddings, no network. Ties break by document order so results repeat.
 * `docs` is [{id, title, chunks:[{loc,text}]}]; hits point back at the exact
 * stored passage (RECORDED text, never rewritten).
 */
const K1 = 1.4, B = 0.75;

export function buildIndex(docs) {
  const passages = [];
  for (const d of docs) d.chunks.forEach((c, i) => passages.push({ docId: d.id, title: d.title, index: i, loc: c.loc || '', text: c.text }));
  const df = new Map();
  const rows = passages.map(p => {
    const tf = new Map();
    for (const t of tokenize(p.text)) tf.set(t, (tf.get(t) || 0) + 1);
    for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1);
    let len = 0; for (const v of tf.values()) len += v;
    return { tf, len };
  });
  const avg = rows.length ? rows.reduce((a, r) => a + r.len, 0) / rows.length : 0;
  return { passages, rows, df, avg: avg || 1, n: passages.length };
}

export function search(index, query, { k = 3, docIds = null, minScore = 0.01 } = {}) {
  const terms = [...new Set(tokenize(query))];
  if (!terms.length || !index.n) return [];
  const hits = [];
  for (let i = 0; i < index.n; i++) {
    const p = index.passages[i];
    if (docIds && !docIds.includes(p.docId)) continue;
    const { tf, len } = index.rows[i];
    let score = 0;
    for (const t of terms) {
      const f = tf.get(t); if (!f) continue;
      const n = index.df.get(t) || 0;
      const idf = Math.log(1 + (index.n - n + 0.5) / (n + 0.5));
      score += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * len / index.avg));
    }
    if (score >= minScore) hits.push({ ...p, score: Math.round(score * 1e4) / 1e4, i });
  }
  hits.sort((a, b) => b.score - a.score || a.i - b.i);
  return hits.slice(0, Math.max(1, Math.min(10, k))).map(({ i, ...h }) => h);
}
