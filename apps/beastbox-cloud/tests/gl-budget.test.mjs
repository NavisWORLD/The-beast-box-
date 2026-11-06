// P0 (ONE UNIVERSE round two): GL budget counter + fail-soft + per-view fallback.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createGlBudget,safeGlBudget,tryCreateGl} from '../lib/three/gl-budget.ts';

test('counts live contexts, lost ones and releases', () => {
  const b = createGlBudget();
  const a = b.acquire('living-world'), c = b.acquire('pocket', {soft: true});
  assert.equal(b.live(), 2);
  a.lost(true); assert.equal(b.live(), 1); assert.equal(b.snapshot().lost, 1);
  a.lost(false); a.release(); assert.equal(b.live(), 1);
  assert.deepEqual(b.snapshot().views.map(v => v.view), ['pocket']);
});

test('budget module throws: views get a no-op handle and keep working', () => {
  const s = safeGlBudget(() => { throw new Error('boom'); });
  const h = s.acquire('living-world');
  assert.doesNotThrow(() => { h.lost(true); h.release(); });
  assert.equal(s.live(), null);
  const broken = safeGlBudget(() => ({acquire() { throw new Error('x'); }, live() { throw new Error('y'); }, snapshot() { return {}; }}));
  assert.doesNotThrow(() => broken.acquire('v').release());
  assert.equal(broken.live(), null);
});

test('budget module missing (loader returns nothing): no-op, no throw', () => {
  for (const load of [() => undefined, () => null]) {
    const s = safeGlBudget(load);
    assert.doesNotThrow(() => s.acquire('v').release());
    assert.equal(s.live(), null);
  }
});

test('one view failing does not take its neighbour down', () => {
  const b = createGlBudget();
  const views = {
    'living-world': () => { throw new Error('Error creating WebGL context.'); },
    pocket: () => ({renderer: true}),
  };
  const state = {};
  for (const [name, make] of Object.entries(views)) {
    const r = tryCreateGl(make);
    if (r.ok) { b.acquire(name); state[name] = '3d'; } else state[name] = 'land2d';
  }
  assert.deepEqual(state, {'living-world': 'land2d', pocket: '3d'});
  assert.equal(b.live(), 1);
  assert.equal(tryCreateGl(() => null).ok, false);
});

test('living-world wires the guard, per-view 2D land, lost/restored, lean options; no Math.random', () => {
  const src = readFileSync(new URL('../components/living-world.tsx', import.meta.url), 'utf8');
  assert.match(src, /tryCreateGl\(\(\)=>/);
  assert.match(src, /powerPreference:lean\?'default':'high-performance'/);
  assert.match(src, /antialias:!lean/);
  assert.match(src, /webglcontextlost',onLost/);
  assert.match(src, /webglcontextrestored',onRestored/);
  assert.match(src, /<SeededLand2D seed=\{land2d\} fill\/>/);
  assert.match(src, /safeGlBudget\(pageGlBudget\)/);
  for (const f of ['../components/living-world.tsx', '../lib/three/gl-budget.ts', '../components/seeded-land-2d.tsx'])
    assert.doesNotMatch(readFileSync(new URL(f, import.meta.url), 'utf8'), /Math\.random\(/);
});
