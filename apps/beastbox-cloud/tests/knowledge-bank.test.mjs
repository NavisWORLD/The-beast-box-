import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { buildBank, searchBank, bankContext, provenanceLine, isStillLearningReply, stillLearningNote, BANK_CONSENT_KEY } from '../lib/knowledge/bank.mjs';

const raw = readFileSync(new URL('../public/knowledge-bank/bank.json', import.meta.url), 'utf8');
const bank = buildBank(JSON.parse(raw));
const KB = new URL('../knowledge-bank/', import.meta.url);

test('bank has the promised domains, every entry has source + license + version, and no entry calls Zeref an AI or LLM', () => {
  const b = JSON.parse(raw);
  assert.ok(b.count >= 800 && b.entries.length === b.count);
  for (const d of ['english', 'math', 'world', 'zeref', 'songs']) assert.ok(b.entries.some(e => e.domain === d), d);
  const ids = new Set();
  for (const e of b.entries) {
    assert.ok(e.id && e.title && e.text && e.source && e.license && Number.isInteger(e.version), e.id);
    assert.ok(!ids.has(e.id)); ids.add(e.id);
    assert.ok(!/\bAI\b|\bLLM\b/.test(e.text), e.id);
  }
});

test('manifest hashes match the files (versioned library)', () => {
  const m = JSON.parse(readFileSync(new URL('manifest.json', KB), 'utf8'));
  for (const [name, info] of Object.entries(m.files)) assert.equal(createHash('sha256').update(readFileSync(new URL(name, KB))).digest('hex'), info.sha256, name);
  assert.equal(createHash('sha256').update(raw).digest('hex'), m.bank_json_sha256);
  assert.equal(m.corpus_export.in_training_mix, false);
});

test('retrieval finds the right passage and shows source, license and version', () => {
  const cases = [
    ['What is the capital of France?', /Paris/], ['apostrophe for ownership', /ownership/i], ['what is the pythagorean theorem', /hypotenuse/],
    ['how many rounds did the IBM bio run play', /8,000 rounds/], ['what is the first prime number', /2, 3, 5, 7/], ['what does RECORDED mean', /real IBM quantum computer/],
  ];
  for (const [q, re] of cases) {
    const hits = searchBank(bank, q);
    assert.ok(hits.length >= 1, q);
    assert.match(hits.map(h => h.excerpt).join(' '), re, q);
    const h = hits[0];
    assert.ok(h.source && h.license && h.version === 1 && provenanceLine(h).includes(h.id));
  }
});

test('same query gives the same hits, different query different hits, nonsense gives nothing', () => {
  const a = searchBank(bank, 'area of a rectangle'), b = searchBank(bank, 'area of a rectangle'), c = searchBank(bank, 'capital of Japan');
  assert.deepEqual(a, b); assert.notDeepEqual(a.map(x => x.id), c.map(x => x.id));
  assert.deepEqual(searchBank(bank, 'zzzqx blorptangle'), []);
  assert.deepEqual(searchBank(bank, ''), []);
});

test('context text is verbatim and bounded', () => {
  const c = bankContext(searchBank(bank, 'percent of a number'));
  assert.ok(c.text.length > 20 && c.text.length < 900 && c.used.length >= 1);
});

test('the still-learning detector flags name lists and one-word replies, never real sentences or Rawr', () => {
  for (const r of ['', 'Zeref', 'Zeref, Cory, Luna, Mira', 'Zeref Cory Luna Mira', 'Luna, Mira, Cory.', 'Banana', 'Sol\nMira\nCory']) assert.equal(isStillLearningReply(r), true, JSON.stringify(r));
  for (const r of ["I'm Zeref. Rawr.", 'Paris is the capital of France.', 'Hehe, good question! Hydrogen and oxygen.', 'Rawr.', 'It is a small dragon that likes the moon', 'Yes, I can be your friend.']) assert.equal(isStillLearningReply(r), false, r);
});

test('note wording is honest and the bank is opt-in by key (default off is the caller\'s job)', () => {
  assert.match(stillLearningNote([{}]), /still learning/);
  assert.match(stillLearningNote([]), /nothing on this question/);
  assert.equal(typeof BANK_CONSENT_KEY, 'string');
});

test('chat wiring: the bank is ON by default (Cory 2026-10-31, keeper can turn it off), and the old library path is untouched', () => {
  const src = readFileSync(new URL('../components/beast-talk-panel.tsx', import.meta.url), 'utf8');
  assert.match(src, /useState\(true\),bankRef/);
  assert.match(src, /persona\.source==='zeref'&&bankOn/);
  assert.match(src, /data-knowledge-bank-notes/);
  assert.match(src, /\/api\/zeref\/library\/search/);
});
