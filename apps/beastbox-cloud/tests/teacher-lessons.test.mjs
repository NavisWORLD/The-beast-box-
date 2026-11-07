import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {screenTeacherLessons,readTeacherRecords,TEACHER_LABEL} from '../lib/zeref/teacher-lessons.mjs';
import {isShareableText,buildSelfMemory,readSelfMemory,teacherJoin,KIND_OF} from '../lib/zeref/self-memory.mjs';

const heldout = JSON.parse(readFileSync(new URL('../lib/zeref/heldout-screen.json', import.meta.url), 'utf8'));
const L = (id, prompt, teacher_reply, extra = {}) => ({id, kind: TEACHER_LABEL, role: 'TEACHER_NOT_BEAST_VOICE', prompt, teacher_reply, ...extra});
const ids = n => `0000000${n}-aaaa-bbbb-cccc-dddddddddddd`;

test('held-out screen file is in sync with the gate sets (read only) and holds no held-out text', () => {
  execFileSync('python3', ['../../scripts/build_heldout_screen.py', '--check']);
  const raw = readFileSync(new URL('../lib/zeref/heldout-screen.json', import.meta.url), 'utf8');
  assert.ok(heldout.items >= 200);
  assert.doesNotMatch(raw, /What animal says|Say good morning|Who are you/i);
});

test('screen: held-out exact, normalised and near-duplicate prompts are excluded; answers of 3+ words too', () => {
  const recs = [
    L(ids(1), 'Say good morning.', 'Good morning to you, friend!'),          // exact held-out prompt
    L(ids(2), 'say   GOOD morning', 'Morning!'),                              // normalised
    L(ids(3), 'Can you please say good morning?', 'Good morning!'),           // containment of held-out bigrams
    L(ids(4), 'How do volcanoes form under the sea?', 'Magma rises through cracks in the ocean floor and cools.'),
  ];
  const {items, report} = screenTeacherLessons(recs, {heldout, existingTexts: [], isShareable: isShareableText});
  assert.deepEqual(items.map(i => i.id), [ids(4)]);
  assert.equal(report.excluded.heldout, 3); assert.equal(report.total, 4); assert.equal(report.in, 1);
});

test('screen: duplicates of sources already in, and the excludes (private, origin, credentials, wrong shape)', () => {
  const recs = [
    L(ids(1), 'What is a comet?', 'A comet is a ball of ice and dust that orbits the sun.'),
    L(ids(2), 'Tell me about comets', 'A comet is a ball of ice and dust that orbits the sun.'),
    L(ids(3), 'What is my password?', 'I cannot know that.'),
    L(ids(4), 'Tell me about Caleb heart beats', 'That is private.'),
    {id: ids(5), kind: 'GUEST_THREAD', prompt: 'hi', teacher_reply: 'hello'},
    L(ids(6), 'Why is the sky blue?', 'Sunlight scatters off air, and blue light scatters most.'),
  ];
  const {items, report} = screenTeacherLessons(recs, {heldout, existingTexts: ['library: Sunlight scatters off air, and blue light scatters most.', 'Sunlight scatters off air, and blue light scatters most.'], isShareable: isShareableText});
  assert.deepEqual(items.map(i => i.id), [ids(1)]);
  assert.equal(report.excluded.duplicate, 2); assert.equal(report.excluded.exclude, 3);
  assert.ok(report.examples.exclude.includes(ids(5)));
});

test('fail closed: no held-out screen or unreadable Azure means NONE go in', async () => {
  const recs = [L(ids(1), 'What is a comet?', 'A ball of ice and dust.')];
  assert.equal(screenTeacherLessons(recs, {heldout: null, isShareable: isShareableText}).items.length, 0);
  assert.equal(screenTeacherLessons(recs, {heldout: {...heldout, rows: []}, isShareable: isShareableText}).items.length, 0);
  const io = {storageConfig: () => ({}), listBlobs: async () => ['beasts/bb-deada969/lessons/d/a.json', 'beasts/bb-deada969/lessons/d/b.json'],
    getBlob: async n => { if (n.endsWith('b.json')) throw new Error('403'); return {text: JSON.stringify(recs[0])}; }};
  assert.equal(await readTeacherRecords(io), null);
  const base = buildSelfMemory([]); base.origins = {};
  const m = await teacherJoin(base, io);
  assert.equal(m.items.length, 0); assert.equal(m.screens.teacher.in, 0); assert.equal(m.screens.teacher.screen_ran, false);
});

test('teacher lessons join as TAUGHT with their own label and rank under LIVED', async () => {
  const rec = L(ids(7), 'What do volcanoes do?', 'Volcanoes push hot magma up through the crust of the earth.');
  const io = {storageConfig: () => ({}), listBlobs: async () => ['beasts/bb-deada969/lessons/d/x.json'], getBlob: async () => ({text: JSON.stringify(rec)})};
  const lived = {id: 'diary:z', kind: 'LIVED', source: 'diary', label: 'RECORDED', text: 'I dreamed of a volcano glowing in my sky', sha256: 'z'.repeat(64)};
  const base = buildSelfMemory([lived]); base.origins = {diary: 'azure'};
  const m = await teacherJoin(base, io);
  const t = m.items.find(i => i.source === 'teacher');
  assert.equal(t.label, 'APPROVED_TEACHER_LESSON'); assert.equal(t.kind, 'TAUGHT'); assert.equal(KIND_OF.teacher, 'TAUGHT');
  assert.equal(m.origins.teacher, 'azure'); assert.equal(m.screens.teacher.in, 1);
  const r = readSelfMemory(m, 'volcano magma', {minScore: 0});
  assert.deepEqual(r.memory_read.map(x => x.label), ['RECORDED', 'APPROVED_TEACHER_LESSON']);
});
