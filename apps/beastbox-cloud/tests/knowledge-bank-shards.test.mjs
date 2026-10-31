import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { buildBank, searchBank, shardsFor, addShards, loadShardsFor, provenanceLine } from '../lib/knowledge/bank.mjs';

const PUB = new URL('../public/knowledge-bank/', import.meta.url);
const raw = readFileSync(new URL('bank.json', PUB), 'utf8');
const core = JSON.parse(raw);
const readShard = p => JSON.parse(readFileSync(new URL(p, PUB), 'utf8'));
const getJson = async u => readShard(u.replace(/^\/knowledge-bank\//, ''));

test('bank.json stays small: world-001 lives in shards fetched on demand, and the hashes match the manifest', () => {
  assert.ok(statSync(new URL('bank.json', PUB)).size < 1_000_000);
  assert.ok(core.shards.length >= 10 && core.shard_entries >= 2400 && core.routes.length === core.shard_entries);
  const m = JSON.parse(readFileSync(new URL('../knowledge-bank/manifest.json', import.meta.url), 'utf8'));
  assert.equal(m.shards.in_training_mix, false);
  let n = 0;
  for (const s of core.shards) {
    const t = readFileSync(new URL(s.path, PUB));
    assert.ok(t.length < 200_000, s.path);
    assert.equal(createHash('sha256').update(t).digest('hex'), s.sha256);
    assert.equal(m.shards.files[s.path].sha256, s.sha256);
    n += s.count;
  }
  assert.equal(n, core.shard_entries);
});

test('every shard entry has an https source and the right licence (CC BY-SA 4.0 for Wikipedia, MIT for GSM8K), never the repo default', () => {
  for (const s of core.shards) for (const e of readShard(s.path).entries) {
    assert.ok(e.source.startsWith('https://'), e.id);
    if (e.id.startsWith('wiki-')) { assert.equal(e.license, 'CC BY-SA 4.0'); assert.match(e.source, /simple\.wikipedia\.org\/w\/index\.php\?title=.+&oldid=\d+$/); }
    else { assert.ok(e.id.startsWith('gsm-')); assert.equal(e.license, 'MIT'); assert.match(e.source, /github\.com\/openai\/grade-school-math\/blob\/[0-9a-f]{40}\//); }
    assert.ok(!/\bAI\b|\bLLM\b/.test(e.text), e.id);
  }
});

test('passages are word for word from evidence/zeref-world-001/qa.jsonl', () => {
  const qa = readFileSync(new URL('../../../evidence/zeref-world-001/qa.jsonl', import.meta.url), 'utf8').trim().split('\n').map(JSON.parse);
  const bySrc = new Map(qa.map(r => [r.source, r]));
  for (const s of core.shards) for (const e of readShard(s.path).entries) {
    const r = bySrc.get(e.source); assert.ok(r, e.id);
    assert.equal(e.text, e.id.startsWith('wiki-') ? r.assistant : r.user + ' ' + r.assistant);
  }
});

test('a question loads only the shards it names, and searchBank then finds the passage with its source', async () => {
  let bank = buildBank(core);
  assert.ok(!searchBank(bank, 'What is photosynthesis?').some(h => h.id.startsWith('wiki-'))); // not loaded yet
  const need = shardsFor(bank, 'What is photosynthesis?');
  assert.ok(need.length >= 1 && need.length <= 4);
  bank = await loadShardsFor(bank, 'What is photosynthesis?', getJson);
  assert.ok(bank.loaded.size === need.length && bank.loaded.size < core.shards.length);
  const hits = searchBank(bank, 'What is photosynthesis?');
  const w = hits.find(h => h.id.startsWith('wiki-'));
  assert.ok(w, JSON.stringify(hits));
  assert.match(w.excerpt, /[Pp]hotosynthesis/);
  assert.equal(w.license, 'CC BY-SA 4.0');
  assert.ok(provenanceLine(w).includes('simple.wikipedia.org'));
  // core entries still work after shards are added
  assert.match(searchBank(bank, 'What is the capital of France?').map(h => h.excerpt).join(' '), /Paris/);
});

test('shard loading is deterministic and idempotent', async () => {
  const a = await loadShardsFor(buildBank(core), 'Who was Aristotle?', getJson);
  const b = await loadShardsFor(buildBank(core), 'Who was Aristotle?', getJson);
  assert.deepEqual(searchBank(a, 'Who was Aristotle?'), searchBank(b, 'Who was Aristotle?'));
  assert.equal(addShards(a, []), a);
  assert.deepEqual(shardsFor(a, 'Who was Aristotle?'), []);
  assert.deepEqual(shardsFor(a, 'zzzqx blorptangle'), []);
});
