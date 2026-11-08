import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {whenLaidOut} from '../lib/three/gl-size.mjs';

const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('a canvas that already has a box is ready, and a zero box waits for layout', async () => {
  const ready = await whenLaidOut({getBoundingClientRect: () => ({width: 320, height: 180})}, 20);
  assert.equal(ready.ok, true);
  assert.equal(ready.width, 320);
  let box = {width: 0, height: 0};
  let notify = () => {};
  let watched = 0;
  globalThis.ResizeObserver = class {
    constructor(cb) { notify = cb; }
    observe() { watched += 1; }
    disconnect() { this.dead = true; }
  };
  const el = {getBoundingClientRect: () => box};
  const pending = whenLaidOut(el, 400);
  let settled = false;
  pending.then(value => { settled = value; });
  await new Promise(r => setTimeout(r, 20));
  assert.equal(settled, false);
  assert.equal(watched, 1);
  box = {width: 48, height: 36};
  notify();
  const laid = await pending;
  assert.equal(laid.ok, true);
  assert.equal(laid.width, 48);
  assert.equal(laid.height, 36);
  const missed = await whenLaidOut({getBoundingClientRect: () => ({width: 0, height: 1})}, 30);
  assert.equal(missed.ok, false);
  delete globalThis.ResizeObserver;
});

test('the world and the pocket refuse a zero-size renderer, and the world does not join the pocket painter', () => {
  const world = read('components/living-world.tsx');
  const pocket = read('components/cage-pocket-dimension.tsx');
  const wait = world.indexOf('await shown.promise');
  const three = world.indexOf("await import('three')");
  const laid = world.indexOf('await whenLaidOut(');
  const gl = world.indexOf('new THREE.WebGLRenderer');
  assert.ok(wait > 0 && three > wait && laid > three && gl > laid);
  assert.match(world, /whenShown\([^)]*timeoutMs:\s*1500/);
  assert.match(world, /if\(r\.width<2\|\|r\.height<2\)return/);
  assert.match(world, /if\(!laid\.ok\)\{setLand2d\(/);
  assert.equal(world.includes('beastbox-pocket-paint'), false);
  assert.equal(world.includes('BroadcastChannel'), false);
  const pocketLaid = pocket.indexOf('await whenLaidOut(');
  const pocketThree = pocket.indexOf("await import('three')");
  const pocketGl = pocket.indexOf('new THREE.WebGLRenderer');
  assert.ok(pocketLaid > pocketThree && pocketGl > pocketLaid);
  assert.match(pocket, /if\(rect\.width<2\|\|rect\.height<2\)return/);
  assert.ok(!/Math\.random/.test(read('lib/three/gl-size.mjs')));
});
