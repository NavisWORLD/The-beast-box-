import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createGlDebug,glDebugEnabled} from '../lib/three/gl-debug.ts';

test('the flag is off unless the query says gldebug=1', () => {
  assert.equal(glDebugEnabled(''), false);
  assert.equal(glDebugEnabled('?glfail=living-world'), false);
  assert.equal(glDebugEnabled('?gldebug=1'), true);
  assert.equal(glDebugEnabled('?planet=a&gldebug=1'), true);
  assert.equal(glDebugEnabled('?gldebug=0'), false);
});

test('a recorder keeps create, lose and dispose with the clock it is given', () => {
  let n = 0;
  const d = createGlDebug(() => '2026-11-09T00:00:0' + (n++) + 'Z');
  d.owner('home-pocket');
  const id = d.create(undefined, 'Apple GPU');
  assert.equal(d.snapshot().live, 1);
  assert.equal(d.snapshot().views[0].view, 'home-pocket');
  assert.equal(d.snapshot().views[0].renderer, 'Apple GPU');
  d.owner('living-world');
  d.create(undefined, 'Apple GPU');
  d.lose(id);
  d.dispose('living-world');
  const snap = d.snapshot();
  assert.equal(snap.live, 0);
  assert.deepEqual(snap.events.map(e => e.kind), ['create', 'create', 'lose', 'dispose']);
  assert.ok(snap.events.every(e => e.t.startsWith('2026-11-09T')));
});

test('the page patch is behind the flag, and the two home views name themselves', () => {
  const src = readFileSync(new URL('../lib/three/gl-debug.ts', import.meta.url), 'utf8');
  assert.match(src, /if\(!glDebugEnabled\(\)\|\|patched/);
  assert.match(src, /pageGlDebug\(\)\?\.owner/);
  const pocket = readFileSync(new URL('../components/cage-pocket-dimension.tsx', import.meta.url), 'utf8');
  const world = readFileSync(new URL('../components/living-world.tsx', import.meta.url), 'utf8');
  const layout = readFileSync(new URL('../app/layout.tsx', import.meta.url), 'utf8');
  assert.match(pocket, /glDebugOwner\('home-pocket'\)/);
  assert.match(pocket, /glDebugDispose\('home-pocket'\)/);
  assert.match(world, /glDebugOwner\('living-world'\)/);
  assert.match(world, /glDebugDispose\('living-world'\)/);
  assert.match(layout, /<GlDebugOverlay\/>/);
  for (const file of [src, pocket, world]) assert.doesNotMatch(file, /Math\.random\(/);
});
