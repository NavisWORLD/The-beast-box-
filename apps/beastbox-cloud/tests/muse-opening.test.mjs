import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryStore } from '../lib/muse/store.mjs';
import { callTool, TOOL_NAMES } from '../lib/muse/tools.mjs';
import { OPENING_NAMES, markPresence, presence, readWeb, xWindow, CLASS_CAP } from '../lib/muse/opening.mjs';

async function setup(scope = 'beast.read beast.care') {
  const store = createMemoryStore();
  await store.set('acct:a1', { id: 'a1', snapshot: null, tokens: [] });
  return { store, auth: { accountId: 'a1', scope, kind: 'pat', tokenId: 't' } };
}
const body = (r) => r.structuredContent;

test('opening tools are listed', () => { for (const n of OPENING_NAMES) assert.ok(TOOL_NAMES.includes(n)); });

test('class log falls back to the recorded last class', async () => {
  const { store } = await setup();
  const { classLog } = await import('../lib/muse/opening.mjs');
  const r = await classLog(store, 5);
  assert.equal(r.turns.length, 5);
});

test('presence blocks teaching; lines are capped at 8 words and 19 per class; every turn is a step', async () => {
  const store = createMemoryStore();
  let t = Date.parse('2026-11-01T06:00:00Z');
  const ctx = { store, now: t, talk: async (l) => ({ reply: ' Mael: the world is so big!', tag: 'zeref-growing-003', step: 36464, checkpoint_sha256: 'c'.repeat(64) }) };
  const ok = (d) => ({ structuredContent: d }); const err = (code, m, x) => ({ isError: true, structuredContent: { error: { code } } });
  const { callOpeningTool } = await import('../lib/muse/opening.mjs');
  await markPresence(store, 'human', t);
  assert.equal(body(await callOpeningTool('zeref_teach', { line: 'Earth spins.' }, ctx, ok, err)).error.code, 'someone_is_with_him');
  t += 21 * 60 * 1000;
  assert.equal(body(await callOpeningTool('zeref_teach', { line: 'one two three four five six seven eight nine' }, { ...ctx, now: t }, ok, err)).error.code, 'too_long');
  for (let i = 0; i < CLASS_CAP; i++) {
    const r = body(await callOpeningTool('zeref_teach', { line: 'Red, orange, green!' }, { ...ctx, now: t + i * 1000 }, ok, err));
    assert.equal(r.step.kind, 'step'); assert.equal(r.zeref, ' Mael: the world is so big!');
  }
  assert.equal(body(await callOpeningTool('zeref_teach', { line: 'Hi' }, { ...ctx, now: t + 30000 }, ok, err)).error.code, 'class_full');
  assert.equal((await presence(store, t + 31000)).muse_may_teach, true);
});

test('web reader refuses hosts outside the allowlist', async () => {
  assert.equal((await readWeb('https://example.com/')).error, 'not_allowed');
  assert.equal((await readWeb('http://en.wikipedia.org/')).error, 'not_allowed');
});

test('X window has no handles or DMs', () => {
  const w = xWindow(10);
  for (const p of w.posts) { assert.ok(!/@\w/.test(p.text + p.narration)); assert.match(p.post, /^https:\/\/x\.com\/i\/status\/\d+$/); }
});

test('teach needs care scope through callTool', async () => {
  const { store, auth } = await setup('beast.read');
  const r = await callTool('zeref_teach', { line: 'Hi' }, { store, auth });
  assert.equal(body(r).error.code, 'insufficient_scope');
});
