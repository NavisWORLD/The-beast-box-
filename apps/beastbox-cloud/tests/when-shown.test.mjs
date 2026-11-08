import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {whenShown} from '../lib/three/when-shown.mjs';

const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('an on-screen canvas starts immediately and an offscreen one waits for intersection', async () => {
  const observed = [];
  class IO {
    constructor(cb) { this.cb = cb; observed.push(this); }
    observe() {}
    disconnect() { this.dead = true; }
  }
  globalThis.IntersectionObserver = IO;
  globalThis.window = {innerHeight: 900};
  const onScreen = {getBoundingClientRect: () => ({width: 300, height: 300, top: 100, bottom: 400})};
  assert.equal(await whenShown(onScreen).promise, true);
  assert.equal(observed.length, 0);
  const below = {getBoundingClientRect: () => ({width: 385, height: 372, top: 941, bottom: 1313})};
  const hidden = whenShown(below);
  let settled = false;
  hidden.promise.then(value => { settled = value; });
  await new Promise(r => setTimeout(r, 0));
  assert.equal(settled, false);
  assert.equal(observed.length, 1);
  observed[0].cb([{isIntersecting: true}]);
  assert.equal(await hidden.promise, true);
  assert.equal(observed[0].dead, true);
  const parked = whenShown(below);
  parked.cancel();
  assert.equal(await parked.promise, false);
  delete globalThis.IntersectionObserver;
  delete globalThis.window;
});

test('living world waits to be shown before it imports three', () => {
  const src = read('components/living-world.tsx');
  const wait = src.indexOf('await shown.promise');
  const three = src.indexOf("await import('three')");
  assert.ok(wait > 0 && three > wait);
  assert.ok(!/Math\.random/.test(read('lib/three/when-shown.mjs')));
});

test('an offscreen pocket waits out the OPEN GAME tap, then still boots, and does not keep painting below the fold', () => {
  const src = read('components/cage-pocket-dimension.tsx');
  const wait = src.indexOf('await Promise.race([shown.promise,later])');
  const three = src.indexOf("await import('three')");
  const bridge = src.indexOf("data-bridge-settled");
  assert.ok(wait > 0 && bridge > wait && three > bridge);
  assert.match(src, /setTimeout\(\(\)=>resolve\(true\),5000\)/);
  assert.match(src, /let visible=inView\(\)/);
  assert.match(src, /visible=inView\(\)/);
  assert.match(src, /!visible&&rendered/);
  assert.match(src, /if\(!inView\(\)\)\{rendered=true;setReady\(true\);\}/);
  assert.ok(!/Math\.random/.test(src));
});
