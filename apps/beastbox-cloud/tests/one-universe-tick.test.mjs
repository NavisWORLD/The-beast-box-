import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {displayTick, nextWorldState, progressionTicks, publishUniverseTick, browserTickOn, oneUniverseTickOn, followUniverseTick, storedUniverseClock} from '../public/universe/one-universe-tick.mjs';
import {pageTickOn, armTick} from '../public/universe/one-universe-gate.mjs';
import {oneUniverseStateOn} from '../public/universe/one-universe-state.mjs';
import {oneUniverseLightOn} from '../public/universe/one-universe-light.mjs';
import {oneUniversePopulationOn} from '../lib/cosmos/one-population.mjs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const world = {schema: 'tiny-universe/v1', seed: 'abc', tick: 17, planets: [{id: 'p'}]};
const clock = {get: () => world, step() { throw new Error('surface stepped the clock'); }};

test('tick flag defaults off and does not turn the other flags on', () => {
  assert.equal(browserTickOn({env: '', search: '', storage: null}), false);
  assert.equal(oneUniverseTickOn({env: '', search: '', storage: null}), false);
  assert.equal(pageTickOn({search: '', storage: null}), false);
  assert.equal(pageTickOn({search: '?oneUniverse=tick'}), true);
  assert.equal(pageTickOn({search: '', storage: {getItem: () => 'tick'}}), true);
  assert.equal(browserTickOn({env: 'tick'}), true);
  assert.equal(browserTickOn({env: 'state'}), false);
  assert.equal(browserTickOn({env: 'light'}), false);
  assert.equal(browserTickOn({env: 'population'}), false);
  assert.equal(oneUniverseStateOn({env: 'tick'}), false);
  assert.equal(oneUniverseLightOn({env: 'tick'}), false);
  assert.equal(oneUniversePopulationOn({env: 'tick'}), false);
  assert.equal(oneUniverseTickOn({env: 'state'}), false);
  assert.equal(oneUniverseTickOn({search: '?oneUniverse=tick'}), true);
});

test('flag off does not read the clock, the diary, or grow', () => {
  let reads = 0;
  let grows = 0;
  const held = {tick: 4};
  const out = nextWorldState({
    on: false,
    state: held,
    clock: {get() { reads += 1; return world; }},
    grow() { grows += 1; return {tick: 5}; },
  });
  assert.equal(reads, 0);
  assert.equal(grows, 0);
  assert.equal(out.read, false);
  assert.equal(out.grew, false);
  assert.equal(out.state, held);
});

test('a missing clock or diary sends no tick', () => {
  assert.equal(displayTick(undefined), null);
  assert.equal(displayTick(null), null);
  assert.equal(displayTick('17'), null);
  assert.equal(displayTick(1.5), null);
  assert.equal(displayTick(0), 0);
  const missing = nextWorldState({on: true, state: {tick: 4}, clock: null, grow() { throw new Error('grew'); }});
  assert.equal(missing.read, true);
  assert.equal(missing.grew, false);
  assert.equal(missing.tick, null);
  assert.equal(missing.state.tick, 4);
  const blank = progressionTicks({worldTick: 17, diary: null, heartbeat: null});
  assert.equal(blank.diary, null);
  assert.equal(blank.heartbeat, null);
  const node = {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
  const pub = publishUniverseTick({on: true, node, tick: null});
  assert.equal(pub.written, false);
  assert.equal(node.attrs['data-universe-tick'], undefined);
});

test('flag on reads the one universe tick and leaves the diary tick alone', () => {
  let grows = 0;
  const local = {tick: 4};
  const out = nextWorldState({on: true, state: local, clock, grow() { grows += 1; }});
  assert.equal(grows, 0);
  assert.equal(out.grew, false);
  assert.equal(out.tick, 17);
  assert.equal(out.state, world);
  const prog = progressionTicks({worldTick: 17, diary: {ok: true, tick: 124}, heartbeat: {recorded_tick: 90}});
  assert.equal(prog.diary, 124);
  assert.equal(prog.heartbeat, 90);
  assert.notEqual(prog.diary, out.tick);
  const diaryOnly = progressionTicks({worldTick: 17, diary: {tick: 3}, heartbeat: {}});
  assert.equal(diaryOnly.diary, 3);
  assert.equal(diaryOnly.heartbeat, null);
});

test('a failed tick load does not write a tick', async () => {
  const node = {attrs: {kept: '1'}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
  const off = await armTick({on: false, node, load: () => { throw new Error('should not load'); }});
  assert.equal(off.armed, false);
  assert.equal(off.failed, false);
  assert.deepEqual(node.attrs, {kept: '1'});
  const missing = await armTick({on: true, node, load: () => Promise.reject(new Error('module missing'))});
  assert.equal(missing.failed, true);
  assert.equal(node.attrs['data-universe-tick'], undefined);
  const down = await armTick({on: true, node, load: async () => ({publishUniverseTick() { throw new Error('down'); }})});
  assert.equal(down.failed, true);
  assert.equal(node.attrs['data-universe-tick'], undefined);
});

function tickNode() {
  return {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
}

test('a clock that arrives later is followed, and a missing clock writes no tick', () => {
  const node = tickNode();
  let clock = null;
  let heard = null;
  const stop = followUniverseTick({
    on: true,
    node,
    readClock: () => clock,
    listen(bind) { heard = bind; return () => { heard = null; }; },
  });
  assert.equal(node.attrs['data-universe-tick'], undefined);
  assert.equal(typeof heard, 'function');
  let live = 0;
  clock = {
    tick: 0,
    get() { return {tick: this.tick}; },
    subscribe(fn) { live += 1; this.fn = fn; return () => { live -= 1; this.fn = null; }; },
  };
  heard();
  assert.equal(node.attrs['data-universe-tick'], '0');
  assert.equal(live, 1);
  clock.tick = 2;
  clock.fn();
  assert.equal(node.attrs['data-universe-tick'], '2');
  const quiet = followUniverseTick({on: false, node, readClock() { throw new Error('read'); }, listen() { throw new Error('listened'); }});
  quiet();
  stop();
  assert.equal(live, 0);
  assert.equal(heard, null);
});

test('a stored universe record is a tick only when that tick is an integer', () => {
  assert.equal(storedUniverseClock(null), null);
  assert.equal(storedUniverseClock({getItem() { return null; }}), null);
  assert.equal(storedUniverseClock({getItem() { return '{"tick":"4"}'; }}), null);
  const clock = storedUniverseClock({getItem() { return '{"tick":4,"seed":"s"}'; }});
  assert.equal(clock.get().tick, 4);
  assert.equal(storedUniverseClock({getItem() { return '{"tick":0}'; }}).get().tick, 0);
  assert.equal(storedUniverseClock({getItem() { return '{'; }}), null);
});

test('every surface follows the one tick and does not start its own', () => {
  const provider = read('../components/one-world-provider.tsx');
  const spark = read('../public/spark/app.mjs');
  const beach = read('../public/beach-two/toy.js');
  assert.match(provider, /followUniverseTick/);
  assert.match(spark, /pageTickOn/);
  assert.match(spark, /import\(\s*'\.\.\/universe\/one-universe-tick\.mjs'\s*\)/);
  assert.doesNotMatch(spark, /from '\.\.\/universe\/one-universe-tick\.mjs'/);
  assert.match(beach, /pageTickOn/);
  assert.match(beach, /import\(\s*'\.\.\/universe\/one-universe-tick\.mjs'\s*\)/);
  assert.doesNotMatch(beach, /from '\.\.\/universe\/one-universe-tick\.mjs'/);
  assert.doesNotMatch(read('../public/universe/one-universe-tick.mjs'), /grow\(/);
  const living = read('../components/living-world.tsx');
  assert.match(living, /clock:currentWorldClock\(\)\|\|oneClock/);
  assert.match(living, /displayTick\(\(currentWorldClock\(\)\|\|oneClock\)\?\.get\?\.\(\)\?\.tick\)/);
});

test('private grow stays for the flag-off path, and the diary chain is not folded into the clock', () => {
  const living = read('../components/living-world.tsx');
  const tiny = read('../components/tiny-universe-view.tsx');
  const pocket = read('../components/pocket-life.ts');
  const clockSrc = read('../lib/world/one-world-clock.mjs');
  const tickSrc = read('../public/universe/one-universe-tick.mjs');
  const menu = read('../components/world-menu.tsx');
  const options = read('../lib/world/world-options.mjs');
  assert.match(living, /browserTickOn\(\)/);
  assert.match(living, /nextWorldState/);
  assert.match(living, /grow\(u,1\)/);
  assert.match(tiny, /browserTickOn\(\)/);
  assert.match(pocket, /displayTick/);
  assert.match(pocket, /\?\?0/);
  assert.match(clockSrc, /u=grow\(u,1\)/);
  assert.doesNotMatch(clockSrc, /diary/);
  assert.doesNotMatch(tickSrc, /Math\.random/);
  assert.doesNotMatch(tickSrc, /grow\(/);
  assert.match(menu, /data-world-menu/);
  assert.match(options, /Living world/);
  assert.match(options, /Pocket explorer/);
});
