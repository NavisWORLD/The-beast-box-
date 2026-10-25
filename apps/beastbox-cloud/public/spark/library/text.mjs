/**
 * Deterministic text helpers: normalising, sentence splitting, tokenising and
 * extraction. No model, no network, no randomness; same input, same output.
 */
const STOP = new Set(('a an and are as at be but by for from has have he her his i in is it its me my of on or our she so that the their them they this to us was we were what when where which who why will with you your do does did not no if then than too very can could would should about into over also just more most other some such only own same up out how all any been being both each few had here there these those while am').split(' '));

export function clean(value) {
  return String(value ?? '')
    .replace(/\r\n?/g, '\n')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\ufffe\uffff]/g, ' ')
    .replace(/[ \t\u00a0]+/g, ' ')
    .replace(/ ?\n ?/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function tokenize(text) {
  const out = [];
  for (const m of String(text ?? '').toLowerCase().normalize('NFKC').matchAll(/[\p{L}\p{N}]+(?:['’][\p{L}]+)?/gu)) {
    const w = m[0].replace(/['’]s$/, '');
    if (w.length < 2 && !/^\p{N}$/u.test(w)) continue;
    if (STOP.has(w)) continue;
    out.push(w.length > 5 ? stem(w) : w);
  }
  return out;
}

/** Tiny suffix stripper; deterministic and good enough for keyword retrieval. */
function stem(w) {
  for (const s of ['ingly', 'edly', 'ing', 'ies', 'ied', 'ed', 'es', 'ly', 's']) {
    if (w.endsWith(s) && w.length - s.length >= 4) return s === 'ies' || s === 'ied' ? w.slice(0, -s.length) + 'y' : w.slice(0, -s.length);
  }
  return w;
}

export function splitSentences(text) {
  const t = clean(text);
  if (!t) return [];
  const out = [];
  for (const para of t.split(/\n{2,}|\n/)) {
    const parts = para.match(/[^.!?。！？]+[.!?。！？]+["'”’)\]]*\s*|[^.!?。！？]+$/gu) || [para];
    for (const p of parts) { const s = p.trim(); if (s) out.push(s); }
  }
  return out;
}

/** Hard-split any piece longer than max at whitespace so no sentence can blow a budget. */
export function splitLong(piece, max) {
  if (piece.length <= max) return [piece];
  const out = [];
  let rest = piece;
  while (rest.length > max) {
    let cut = rest.lastIndexOf(' ', max);
    if (cut < max * 0.5) cut = max;
    out.push(rest.slice(0, cut).trim());
    rest = rest.slice(cut).trim();
  }
  if (rest) out.push(rest);
  return out;
}

/**
 * Fit a long message into `budget` characters by extraction (never rewriting).
 * Keeps the closing question or request (last sentences, up to 45% of budget),
 * then adds the other sentences that share the most keywords with it, in their
 * original order. Returns what was kept and exactly how much was read.
 */
export function fitMessage(text, budget) {
  const full = clean(text);
  const total = full.length;
  const cap = Math.max(40, Math.floor(budget));
  if (total <= cap) return { text: full, readChars: total, totalChars: total, omittedChars: 0, extracted: false };
  const sentences = splitSentences(full).flatMap(s => splitLong(s, Math.max(60, Math.floor(cap / 3))));
  const tailMax = Math.floor(cap * 0.45);
  const keep = new Set();
  let used = 0;
  for (let i = sentences.length - 1; i >= 0; i--) {
    const cost = sentences[i].length + 1;
    if (used + cost > tailMax) break;
    keep.add(i); used += cost;
    if (/[?]$/.test(sentences[i]) && keep.size >= 1) break;
  }
  if (!keep.size && sentences.length) { keep.add(sentences.length - 1); used = Math.min(cap, sentences[sentences.length - 1].length); }
  const queryTerms = new Set(tokenize([...keep].map(i => sentences[i]).join(' ')));
  const scored = sentences.map((s, i) => {
    if (keep.has(i)) return null;
    const toks = tokenize(s);
    let hit = 0; for (const t of toks) if (queryTerms.has(t)) hit++;
    return { i, score: toks.length ? hit / Math.sqrt(toks.length) : 0 };
  }).filter(Boolean).sort((a, b) => b.score - a.score || a.i - b.i);
  for (const { i } of scored) {
    const cost = sentences[i].length + 1;
    if (used + cost > cap - 4) continue;
    keep.add(i); used += cost;
  }
  const ordered = [...keep].sort((a, b) => a - b);
  let out = '', prev = -1;
  for (const i of ordered) { out += (prev >= 0 && i !== prev + 1 ? ' … ' : out ? ' ' : '') + sentences[i]; prev = i; }
  out = out.slice(0, cap);
  return { text: out, readChars: out.length, totalChars: total, omittedChars: total - out.length, extracted: true };
}

/** Best contiguous run of sentences (<= max chars) for a query: a verbatim excerpt, never a rewrite. */
export function bestWindow(text, query, max) {
  const full = clean(text);
  if (full.length <= max) return full;
  const q = new Set(tokenize(query));
  const sents = splitSentences(full).flatMap(s => splitLong(s, max));
  const sc = sents.map(s => { let h = 0; for (const t of tokenize(s)) if (q.has(t)) h++; return h; });
  let best = { score: -1, from: 0, to: 0 };
  for (let a = 0; a < sents.length; a++) {
    let len = 0, score = 0;
    for (let b = a; b < sents.length; b++) {
      len += sents[b].length + (b > a ? 1 : 0);
      if (len > max) break;
      score += sc[b];
      if (score > best.score || (score === best.score && b - a > best.to - best.from && score > 0)) best = { score, from: a, to: b };
    }
  }
  return sents.slice(best.from, best.to + 1).join(' ').slice(0, max);
}
