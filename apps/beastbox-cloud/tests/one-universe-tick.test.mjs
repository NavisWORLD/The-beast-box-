import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {displayTick, nextWorldState, progressionTicks, publishUniverseTick, browserTickOn, oneUniverseTickOn} from '../public/universe/one-universe-tick.mjs';
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
