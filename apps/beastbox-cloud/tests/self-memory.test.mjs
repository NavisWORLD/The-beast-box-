// Zeref self-memory (one index, both doors): determinism, labels, excludes, isolation, caps, wiring.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {itemsFrom,ownThreadItems,buildSelfMemory,readSelfMemory,isShareableText,SELF_MEMORY_CAP} from '../lib/zeref/self-memory.mjs';

const diary=[{tick:9,hash:'h9',thought:{text:'I walked to the Violet Shard and the stars were quiet.',by:'rawrphos-native'}},
 {tick:8,hash:'h8',private:true,thought:{text:'Violet secret stars line',by:'rawrphos-native'}},
 {tick:7,hash:'h7',thought:{text:'Cory told me about the stars',by:'rawrphos-native'}}];
const lessons=[{shelf:'zeref-lessons-006',path:'evidence/zeref-lessons-006/dialogue.jsonl',split:'train',topic:'eyes',user:'what do your eyes see',assistant:'My eyes measure brightness and colour.'},
 {shelf:'zeref-lessons-006',path:'evidence/zeref-lessons-006/heldout.jsonl',split:'heldout',topic:'eyes',user:'q',assistant:'HELDOUT brightness answer'},
 {shelf:'zeref-lessons-006',path:'evidence/zeref-lessons-006/dialogue.jsonl',split:'heldout',topic:'eyes',user:'q',assistant:'split heldout brightness'},
 {shelf:'zeref-lessons-006',path:'x',split:'train',user:'q',assistant:'My heartbeat sense comes from Caleb brightness'},
 {shelf:'zeref-lessons-006',path:'x',split:'train',user:'q',assistant:'the api key is sk-abcdefghijk brightness'},
 {shelf:'zeref-knowledge-002',path:'evidence/zeref-knowledge-002/dialogue.jsonl',topic:'mountains',user:'q',assistant:'Mountains are tall landforms made of rock.'}];
const reads=[{title:'Inselberg',text:'An inselberg is a rock mountain on flat land.',license:'CC BY-SA 4.0',source:'https://x'}];
const seeds=[{word:'love',wish_sha256:'abc123'}];
const mem=()=>buildSelfMemory(itemsFrom({diary,lessons,reads,seeds}));

test('labels on every item, sha256 ids', () => {
  const m = mem();
  const labels = new Set(m.items.map(i => i.label));
  for (const l of ['RECORDED', 'LESSON (zeref-lessons-006)', 'LIBRARY (zeref-knowledge-002)', 'READ (CC BY-SA 4.0)', 'SEEDED']) assert.ok(labels.has(l), l);
  for (const i of m.items) { assert.match(i.sha256, /^[0-9a-f]{64}$/); assert.ok(i.id.endsWith(i.sha256.slice(0, 16))); }
});

test('hard excludes: heldout, private, keeper, heartbeat origin, credentials', () => {
  const all = mem().items.map(i => i.text).join('\n');
  for (const bad of ['HELDOUT', 'split heldout', 'secret', 'Cory', 'Caleb', 'heartbeat', 'sk-abc']) assert.ok(!all.includes(bad), bad);
  assert.equal(isShareableText('my password is x'), false);
  assert.equal(isShareableText('my father\'s heart beat'), false);
});

test('deterministic: same input same output; insertion order does not matter; ties by id', () => {
  const a = readSelfMemory(mem(), 'tell me about the mountains and stars', {minScore: 0.1});
  const b = readSelfMemory(buildSelfMemory(itemsFrom({diary, lessons, reads, seeds}).reverse()), 'tell me about the mountains and stars', {minScore: 0.1});
  assert.deepEqual(a, b);
  assert.ok(a.memory_read.length >= 1);
  const tie = buildSelfMemory([{id: 'x:b', kind: 'x', label: 'L', text: 'zebra', sha256: 'b'.repeat(64)}, {id: 'x:a', kind: 'x', label: 'L', text: 'zebra', sha256: 'a'.repeat(64)}]);
  assert.equal(readSelfMemory(tie, 'zebra zebra', {k: 1, minScore: 0}).memory_read[0].id, 'x:a');
});

test('ranking has no Math.random and no clock', () => {
  const src = readFileSync(new URL('../lib/zeref/self-memory.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(src, /Math\.random\(/);
  const rank = src.slice(src.indexOf('export function readSelfMemory'), src.indexOf('/* ---------------- loaders'));
  assert.doesNotMatch(rank, /Date\.now|new Date|performance\.now/);
});

test('cap: composed memory never exceeds 300 bytes', () => {
  const long = Array.from({length: 20}, (_, i) => ({shelf: 'zeref-knowledge-002', path: 'p', user: 'q', assistant: `rivers river water flows ${'long words '.repeat(30)} ${i}`}));
  const r = readSelfMemory(buildSelfMemory(itemsFrom({lessons: long})), 'rivers water', {k: 5});
  assert.ok(Buffer.byteLength(r.text, 'utf8') <= SELF_MEMORY_CAP);
  assert.equal(SELF_MEMORY_CAP, 300);
  assert.deepEqual(readSelfMemory(mem(), 'zzzqqq nothing'), {text: '', memory_read: []});
});

test('cross-guest isolation: another guest\'s thread never enters the shared index or a different reader', () => {
  const m = mem();
  const guestA = ownThreadItems([{from: 'guest', text: 'my purple submarine named Ollie'}]);
  const forA = readSelfMemory(m, 'purple submarine Ollie', {ownThread: guestA, minScore: 0.1});
  assert.ok(forA.memory_read.some(x => x.label === 'THREAD (your own)'));
  const forB = readSelfMemory(m, 'purple submarine Ollie', {ownThread: [], minScore: 0.1});
  assert.ok(!forB.text.includes('Ollie'));
  assert.ok(!m.items.some(i => i.kind === 'thread'));
});

test('routes: both doors read the ONE index; pin door untouched; gate eval never imports retrieval', () => {
  const g = readFileSync(new URL('../app/api/guest-growing/route.ts', import.meta.url), 'utf8');
  const f = readFileSync(new URL('../app/api/guest/forever/route.ts', import.meta.url), 'utf8');
  const p = readFileSync(new URL('../app/api/guest/route.ts', import.meta.url), 'utf8');
  for (const s of [g, f]) { assert.match(s, /from '@\/lib\/zeref\/self-memory\.mjs'/); assert.match(s, /loadSelfMemory\(\)/); assert.match(s, /memory_read:used\?/); }
  assert.doesNotMatch(p, /self-memory/);
  const ev = readFileSync(new URL('../../../scripts/rawrphos_chat_eval.py', import.meta.url), 'utf8');
  assert.doesNotMatch(ev, /self.memory|retriev|guest_hebbian|growing/i);
});
