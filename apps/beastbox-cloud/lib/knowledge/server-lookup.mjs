// Server-side knowledge-bank LOOKUP for the class chat (2026-10-31, Cory: "on by default").
// Same deterministic keyword search as the browser (bank.mjs). It is a lookup, not memory and
// not training: passages are copied word for word and every one carries its source and licence.
import { BANK_URL, BANK_LABEL, buildBank, loadShardsFor, searchBank, bankContext, provenanceLine } from './bank.mjs';

let cached = null; // { origin, bank } — the index only; shards are added as questions need them

/** -> {text, used:[{id,title,source,license,provenance}], label, error?}. Never throws; a failed lookup returns no passages. */
export async function bankLookup(origin, query, fetchImpl = globalThis.fetch) {
  const empty = (error) => ({ text: '', used: [], label: BANK_LABEL, ...(error ? { error } : {}) });
  const q = String(query ?? '').slice(-300);
  if (!q.trim()) return empty();
  try {
    const getJson = async (path) => {
      const r = await fetchImpl(new URL(path, origin), { cache: 'force-cache', signal: AbortSignal.timeout(5000) });
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    };
    if (!cached || cached.origin !== origin) cached = { origin, bank: buildBank(await getJson(BANK_URL)) };
    cached.bank = await loadShardsFor(cached.bank, q, getJson);
    const c = bankContext(searchBank(cached.bank, q));
    return { text: c.text || '', label: BANK_LABEL,
      used: (c.used || []).map((u) => ({ id: u.id, title: u.title, source: u.source, license: u.license, provenance: provenanceLine({ ...u, score: 0, domain: '' }) })) };
  } catch { return empty('lookup unavailable'); }
}
export function _resetBankLookupCache() { cached = null; }
