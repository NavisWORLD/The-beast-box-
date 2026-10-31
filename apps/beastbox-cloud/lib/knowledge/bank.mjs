/**
 * Zeref knowledge bank: deterministic keyword (BM25) retrieval over a small, versioned, open-license library
 * (public/knowledge-bank/bank.json, built by scripts/build_knowledge_bank.py). No model, no embeddings, no network, no random.
 * Passages are copied word for word and every one carries its source, license and version, so the chat can show where it came from.
 * Opt-in: nothing here runs unless the visitor switches the bank on (default OFF).
 */
import { buildIndex, search } from '../library/bm25.mjs';
import { clean, tokenize } from '../library/text.mjs';

export const BANK_URL = '/knowledge-bank/bank.json';
export const BANK_CONSENT_KEY = 'beastbox-zeref-knowledge-bank-v1';
export const BANK_PASSAGES = 2;
export const BANK_PASSAGE_CHARS = 300;
/** Below this BM25 score a match is treated as "nothing relevant" (no weak guesses shown as knowledge). */
export const BANK_MIN_SCORE = 2.2;
export const BANK_LABEL = 'Knowledge bank (open-license, copied word for word, nothing invented)';

/** Routing: a question word that names more than this many shard titles is too common to pick shards by. */
export const SHARD_ROUTE_MAX_TITLES = 40;
/** At most this many shards are fetched for one question (each is ~60 KB). */
export const SHARD_FETCH_MAX = 4;

/** @param {{entries:{id:string,domain:string,title:string,text:string,source:string,license:string,version:number}[]}} bank */
export function buildBank(bank) {
  const core = Array.isArray(bank?.entries) ? bank.entries : [];
  const shards = Array.isArray(bank?.shards) ? bank.shards : [];
  const routes = new Map();
  for (const [title, shard] of Array.isArray(bank?.routes) ? bank.routes : []) {
    for (const t of new Set(tokenize(title))) { if (!routes.has(t)) routes.set(t, new Map()); const m = routes.get(t); m.set(shard, (m.get(shard) || 0) + 1); }
  }
  return indexed({ core, shards, routes, loaded: new Map(), version: bank?.version ?? null, raw: bank });
}

function indexed(b) {
  const entries = [...b.core, ...[...b.loaded.keys()].sort((x, y) => x - y).flatMap(k => b.loaded.get(k))];
  const byId = new Map(entries.map(e => [e.id, e]));
  const index = buildIndex(entries.map(e => ({ id: e.id, title: e.title, chunks: [{ loc: e.domain, text: e.title + '. ' + e.text }] })));
  return { ...b, index, byId, count: entries.length };
}

/** Which shard numbers a question needs (by the titles it names), best first; already-loaded shards are skipped. */
export function shardsFor(bank, query, { max = SHARD_FETCH_MAX } = {}) {
  if (!bank?.routes?.size) return [];
  const score = new Map();
  for (const t of new Set(tokenize(query))) {
    const m = bank.routes.get(t);
    if (!m) continue;
    let titles = 0; for (const v of m.values()) titles += v;
    if (titles > SHARD_ROUTE_MAX_TITLES) continue;
    for (const [s, v] of m) score.set(s, (score.get(s) || 0) + v / titles);
  }
  return [...score].filter(([s]) => !bank.loaded.has(s)).sort((a, b) => b[1] - a[1] || a[0] - b[0]).slice(0, max).map(([s]) => s);
}

/** Returns a new bank with these shard files added (each {shard, entries}). Pure: same inputs, same bank. */
export function addShards(bank, shardFiles) {
  const loaded = new Map(bank.loaded);
  for (const f of shardFiles) if (f && Number.isInteger(f.shard) && Array.isArray(f.entries)) loaded.set(f.shard, f.entries);
  return loaded.size === bank.loaded.size ? bank : indexed({ ...bank, loaded });
}

/** Fetches only the shards this question needs (getJson(url) -> parsed JSON), then returns the bank ready for searchBank. */
export async function loadShardsFor(bank, query, getJson) {
  const need = shardsFor(bank, query);
  if (!need.length) return bank;
  const byNum = new Map(bank.shards.map((s, i) => [Number(s.path.match(/(\d+)\.json$/)?.[1] ?? i), s]));
  const files = await Promise.all(need.map(n => byNum.get(n)).filter(Boolean).map(s => getJson(BANK_URL.replace(/bank\.json$/, s.path)).catch(() => null)));
  return addShards(bank, files);
}

function cut(text, chars) {
  const t = clean(text);
  if (t.length <= chars) return t;
  const head = t.slice(0, chars);
  const stop = Math.max(head.lastIndexOf('. '), head.lastIndexOf('! '), head.lastIndexOf('? '));
  return (stop > chars * 0.4 ? head.slice(0, stop + 1) : head.replace(/\s+\S*$/, '')).trim();
}

/** -> [{id,domain,title,excerpt,source,license,version,score}] best first; [] when nothing is relevant. */
export function searchBank(bank, query, { k = BANK_PASSAGES, chars = BANK_PASSAGE_CHARS, minScore = BANK_MIN_SCORE } = {}) {
  if (!bank?.count) return [];
  const terms = [...new Set(tokenize(query))];
  if (!terms.length) return [];
  // A one-word question must hinge on a rare word, otherwise common words ("use", "first") pull in unrelated passages.
  if (terms.length === 1 && (bank.index.df.get(terms[0]) || 0) > 6) return [];
  const hits = search(bank.index, String(query ?? ''), { k: 10, minScore });
  const out = [];
  for (const h of hits) {
    const e = bank.byId.get(h.docId);
    const have = new Set(tokenize(e.title + ' ' + e.text));
    // The passage must cover at least half of the question's content words, rare words counting more (idf-weighted).
    const idf = t => { const n = bank.index.df.get(t) || 0; return Math.log(1 + (bank.index.n - n + 0.5) / (n + 0.5)); };
    const covers = t => have.has(t) || (t.length >= 4 && [...have].some(w => w.length >= 4 && (w.startsWith(t) || t.startsWith(w))));
    const total = terms.reduce((a, t) => a + idf(t), 0), got = terms.filter(covers).reduce((a, t) => a + idf(t), 0);
    if (got / total < 0.5) continue;
    out.push({ id: e.id, domain: e.domain, title: e.title, excerpt: cut(e.text, chars), source: e.source, license: e.license, version: e.version, score: h.score });
    if (out.length >= k) break;
  }
  return out;
}

/** The verbatim notes block for the prompt, plus the provenance rows the UI shows. */
export function bankContext(hits) {
  const used = Array.isArray(hits) ? hits : [];
  return { text: used.map(u => `[${u.title}, ${u.id}] ${u.excerpt}`).join(' | '), used };
}

export function provenanceLine(u) {
  return `${u.title} · ${u.id} · ${u.source} · ${u.license} · bank v${u.version}`;
}

const RAWR = /^rawr[.!?]*$/i;
/**
 * True when the model's reply is not a usable sentence yet: empty, a single word, or a list of names.
 * Zeref's own catchphrase "Rawr." is a legitimate reply and is never flagged.
 */
export function isStillLearningReply(reply) {
  const text = clean(reply);
  if (!text || RAWR.test(text)) return !text;
  const words = text.match(/[\p{L}][\p{L}'’-]*/gu) || [];
  if (words.length <= 1) return true;
  const caps = words.filter(w => /^\p{Lu}/u.test(w)).length / words.length;
  const ends = /[.!?]["')\]]?\s*$/.test(text);
  const parts = text.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
  const shortParts = parts.length >= 3 && parts.every(p => (p.match(/[\p{L}][\p{L}'’-]*/gu) || []).length <= 3);
  if (shortParts && caps >= 0.7) return true;
  if (!ends && words.length >= 3 && caps >= 0.7) return true;
  return false;
}

/** What the chat says under a reply that was not a real sentence. Never presented as Zeref's own words. */
export function stillLearningNote(used) {
  const base = "Zeref's model is still learning: this reply was not a full sentence.";
  return used?.length ? base + ' Here is what the knowledge bank has on it, copied word for word:' : base + ' The knowledge bank had nothing on this question.';
}
