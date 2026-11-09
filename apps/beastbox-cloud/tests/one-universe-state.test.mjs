import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  ONE_UNIVERSE_FLAG_KEY,
  ONE_WORLD_KEY,
  oneUniverseStateOn,
  browserSources,
  readOneWorld,
  readClockState,
  attachOneWorldRead,
  watchOneWorldRead,
  surfacesForPath,
} from '../public/universe/one-universe-state.mjs';

const read = (p) => readFileSync(new URL('../' + p, import.meta.url), 'utf8');
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

function storage(map) {
  return {getItem: (k) => (Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null)};
}

test('the state flag defaults off and only the named sources turn it on', () => {
  assert.equal(ONE_UNIVERSE_FLAG_KEY, 'beastbox.oneUniverse.flags.v1');
  assert.equal(ONE_WORLD_KEY, 'lw:universe');
  const empty = storage({});
  assert.equal(oneUniverseStateOn({env: '', storage: empty, search: ''}), false);
  assert.equal(oneUniverseStateOn({env: 'light', storage: empty, search: '?oneUniverse=light'}), false);
  assert.equal(oneUniverseStateOn({env: 'state', storage: empty, search: ''}), true);
  assert.equal(oneUniverseStateOn({env: '', storage: empty, search: '?oneUniverse=state'}), true);
  assert.equal(oneUniverseStateOn({env: '', storage: storage({[ONE_UNIVERSE_FLAG_KEY]: 'light, state'}), search: ''}), true);
  assert.equal(oneUniverseStateOn(browserSources()), false);
});

test('flag off does not read the clock and leaves the surface byte-identical', () => {
  const sim = {seed: 'beast-seed', tick: 7, residents: ['Frostmitt']};
  const node = {dataset: {pocketState: 'ready', pocketDimension: '1'}};
  const extra = {dataset: {lookPedestal: '1'}};
  const before = JSON.stringify({sim, node: node.dataset, extra: extra.dataset});
  let calls = 0;
  let subscribed = 0;
  const result = attachOneWorldRead({
    on: false,
    getClock: () => {
      calls += 1;
      return {seed: 'other', tick: 99, schema: 'tiny-universe/v1', planets: [{id: 'p'}], storms: [{id: 's', planet: 'p', intensity: 1}]};
    },
    node,
    nodes: [extra],
    surface: 'pocket',
    sim,
  });
  const stop = watchOneWorldRead({
    on: false,
    getClock: () => { calls += 1; return null; },
    node,
    surface: 'beach',
    subscribe: () => { subscribed += 1; return () => {}; },
  });
  stop();
  assert.equal(calls, 0);
  assert.equal(subscribed, 0);
  assert.equal(result.subscribed, false);
  assert.equal(result.read, null);
  assert.equal(result.sim, sim);
  assert.equal(JSON.stringify({sim, node: node.dataset, extra: extra.dataset}), before);
});

test('flag on reads seed, tick, planets and storms without replacing the simulator', () => {
  const world = {
    schema: 'tiny-universe/v1',
    seed: 'abc',
    tick: 4,
    planets: [{id: 'star-0-p0', water: 0.5}, {id: 'star-0-p1'}],
    storms: [{id: 'storm-4', type: 'storm', planet: 'star-0-p0', intensity: 0.2, lifetime: 3}],
  };
  const sim = {localTick: 1, sky: 'pocket'};
  const beforeSim = JSON.stringify(sim);
  const node = {dataset: {}};
  const pedestal = {dataset: {}};
  const result = attachOneWorldRead({
    on: true,
    getClock: () => world,
    node,
    nodes: [pedestal],
    surface: 'look+pedestal',
    sim,
  });
  world.planets[0].id = 'mutated';
  world.storms[0].intensity = 9;
  assert.equal(result.subscribed, true);
  assert.equal(result.sim, sim);
  assert.equal(JSON.stringify(sim), beforeSim);
  assert.equal(result.read.schema, 'tiny-universe/v1');
  assert.equal(result.read.seed, 'abc');
  assert.equal(result.read.tick, 4);
  assert.deepEqual(result.read.planets, ['star-0-p0', 'star-0-p1']);
  assert.deepEqual(result.read.storms, [{id: 'storm-4', planet: 'star-0-p0', intensity: 0.2}]);
  assert.equal(node.dataset.oneWorldRead, '1');
  assert.equal(node.dataset.oneWorldSurface, 'look+pedestal');
  assert.equal(node.dataset.oneWorldSeed, 'abc');
  assert.equal(node.dataset.oneWorldTick, '4');
  assert.equal(node.dataset.oneWorldPlanets, 'star-0-p0,star-0-p1');
  assert.equal(node.dataset.oneWorldStorms, 'storm-4');
  assert.equal(node.dataset.oneWorldSchema, 'tiny-universe/v1');
  assert.equal(pedestal.dataset.oneWorldSeed, 'abc');
  assert.equal(pedestal.dataset.oneWorldTick, '4');
  const missed = {dataset: {keep: 'yes'}};
  const empty = attachOneWorldRead({on: true, getClock: () => null, node: missed, surface: 'play', sim});
  assert.equal(empty.read, null);
  assert.equal(empty.sim, sim);
  assert.deepEqual(missed.dataset, {keep: 'yes'});
  assert.equal(readOneWorld(() => { throw new Error('clock down'); }), null);
});

test('a standalone document prefers the live clock and otherwise the lw:universe record', () => {
  const stored = {schema: 'tiny-universe/v1', seed: 'stored', tick: 2, planets: [{id: 'p'}], storms: []};
  const bag = storage({[ONE_WORLD_KEY]: JSON.stringify(stored)});
  assert.equal(readClockState({}, bag).seed, 'stored');
  const live = {get: () => ({schema: 'tiny-universe/v1', seed: 'live', tick: 9, planets: [], storms: []})};
  assert.equal(readClockState({__bbOneWorld: live}, bag).seed, 'live');
  assert.equal(readClockState({__bbOneWorld: {get: () => { throw new Error('no'); }}}, bag).seed, 'stored');
});

test('every audited surface has a name, and look carries the pedestal', () => {
  const names = {
    '/': 'home',
    '/beast-cage': 'cage',
    '/beast-cage/world': 'tiny',
    '/universe': 'universe',
    '/beast-cage/look': 'look+pedestal',
    '/beast-cage/turntable': 'look+pedestal',
    '/beach-two': 'beach',
    '/beach-two/toy.html': 'beach',
    '/beast-cage/field': 'field',
    '/beast-cage/go': 'field',
    '/beast-cage/play': 'play',
    '/beast-cage/talk': 'talk',
    '/beast-cage/guest': 'guest',
    '/sol-game': 'game',
    '/workspace': 'workshop',
    '/spark/index.html': 'spark',
    '/settings': 'settings',
    '/try': 'try',
    '/research': 'research',
    '/research/stage015': 'stage015',
    '/brain-bay': 'brain-bay',
    '/growing': 'growing',
    '/loop': 'loop',
    '/messages': 'messages',
    '/account': 'account',
    '/classroom': 'classroom',
    '/mind-room': 'mind-room',
    '/next': 'next',
    '/privacy': 'privacy',
    '/connect/meta-muse': 'meta-muse',
    '/connect/meta-muse/pair': 'meta-muse-pair',
  };
  for (const [path, name] of Object.entries(names)) assert.equal(surfacesForPath(path).join('+'), name, path);
});

test('the flag gates the new read, and Living and Tiny keep the clock they already have', () => {
  const provider = strip(read('components/one-world-provider.tsx'));
  const effects = provider.split('useEffect(');
  assert.equal(effects.length, 3);
  assert.match(effects[1], /oneWorldClock\(\{genesis:g,grow,storage:st\}\)/);
  assert.doesNotMatch(effects[1], /oneUniverseStateOn/);
  assert.match(effects[2], /if\(!oneUniverseStateOn\(browserSources\(\)\)\)return;/);
  assert.match(effects[2], /whenWorldClock\(\)/);
  assert.match(effects[2], /clock\.get\(\)/);
  assert.match(effects[2], /data-look-pedestal/);
  assert.match(effects[2], /data-pocket-dimension/);
  assert.match(effects[2], /data-ar-canvas/);
  const toy = strip(read('public/beach-two/toy.js'));
  const spark = strip(read('public/spark/app.mjs'));
  for (const src of [toy, spark]) {
    assert.match(src, /one-universe-state\.mjs/);
    assert.match(src, /oneUniverseStateOn\(browserSources\(\)\)/);
    assert.match(src, /readClockState/);
    assert.match(src, /watchOneWorldRead/);
  }
  assert.match(toy, /surface:'beach'/);
  assert.match(spark, /surface:'spark'/);
  for (const file of ['components/living-world.tsx', 'components/tiny-universe-view.tsx', 'components/use-one-world.ts', 'components/pocket-life.ts', 'lib/look/attach.ts']) {
    assert.doesNotMatch(read(file), /one-universe-state/);
    assert.match(read(file), /currentWorldClock|useOneWorld/);
  }
  assert.doesNotMatch(read('public/universe/one-universe-state.mjs'), /Math\.random/);
});
