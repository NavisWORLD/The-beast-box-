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

test('pocket and living world wait to be shown before they import three', () => {
  for (const path of ['components/cage-pocket-dimension.tsx', 'components/living-world.tsx']) {
    const src = read(path);
    const wait = src.indexOf('await shown.promise');
    const three = src.indexOf("await import('three')");
    assert.ok(wait > 0 && three > wait, path);
    assert.ok(!/Math\.random/.test(read('lib/three/when-shown.mjs')));
  }
});
