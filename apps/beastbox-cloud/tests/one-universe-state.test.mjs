import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, statSync} from 'node:fs';
import {join} from 'node:path';
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
  beginSurfaceRead,
  publishStandalone,
} from '../public/universe/one-universe-state.mjs';
import {pageStateOn, armStandalonePage} from '../public/universe/one-universe-gate.mjs';

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

test('Living and Tiny keep the clock they already have', () => {
  for (const file of ['components/living-world.tsx', 'components/tiny-universe-view.tsx', 'components/use-one-world.ts', 'components/pocket-life.ts', 'lib/look/attach.ts']) {
    assert.doesNotMatch(read(file), /one-universe-state/);
    assert.match(read(file), /currentWorldClock|useOneWorld/);
  }
  assert.doesNotMatch(read('public/universe/one-universe-state.mjs'), /Math\.random/);
  assert.doesNotMatch(strip(read('public/universe/one-universe-gate.mjs')), /Math\.random/);
  assert.doesNotMatch(strip(read('public/universe/one-universe-gate.mjs')), /process\.env/);
});

test('flag off in the provider, Beach Two and Spark does not read, subscribe or write', async () => {
  const world = {schema: 'tiny-universe/v1', seed: 'abc', tick: 3, planets: [{id: 'p'}], storms: []};
  const node = {dataset: {pocketState: 'ready'}};
  const before = JSON.stringify(node.dataset);
  let clocks = 0;
  let gets = 0;
  let subs = 0;
  let observes = 0;
  const stop = beginSurfaceRead({
    on: false,
    whenClock: () => { clocks += 1; return {get() { gets += 1; return world; }, subscribe() { subs += 1; return () => {}; }}; },
    readNode: () => { throw new Error('node'); },
    nodesFor: () => { throw new Error('nodes'); },
    surfaceFor: () => { throw new Error('surface'); },
    subscribe: () => { subs += 1; return () => {}; },
    observe: () => { observes += 1; return () => {}; },
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  stop();
  assert.equal(clocks, 0);
  assert.equal(gets, 0);
  assert.equal(subs, 0);
  assert.equal(observes, 0);
  assert.equal(JSON.stringify(node.dataset), before);

  let loads = 0;
  let fetches = 0;
  let armed = 0;
  const standalone = {dataset: {keep: 'yes'}};
  const off = await armStandalonePage({
    on: pageStateOn({search: '', storage: storage({})}),
    surface: 'spark',
    load: () => { loads += 1; return Promise.reject(new Error('should not load')); },
    win: {__bbOneWorld: {get() { gets += 1; return world; }, subscribe() { subs += 1; return () => {}; }}},
    storage: storage({[ONE_WORLD_KEY]: JSON.stringify(world)}),
    node: standalone,
    fetchGenesis: () => { fetches += 1; return Promise.resolve(world); },
    subscribe: () => { subs += 1; return () => {}; },
  });
  assert.equal(off.loaded, false);
  assert.equal(off.failed, false);
  assert.equal(loads, 0);
  assert.equal(fetches, 0);
  assert.equal(armed, 0);
  assert.equal(gets, 0);
  assert.equal(subs, 0);
  assert.deepEqual(standalone.dataset, {keep: 'yes'});
  assert.equal(pageStateOn({search: '', storage: storage({}), env: 'state'}), false);
  assert.equal(oneUniverseStateOn({env: 'state', storage: storage({}), search: ''}), true);
});

test('a failed reader load does not throw or write when Beach Two or Spark would import it', async () => {
  const node = {dataset: {keep: 'yes'}};
  let subs = 0;
  const failed = await armStandalonePage({
    on: true,
    surface: 'beach',
    load: () => Promise.reject(new Error('module missing')),
    win: {},
    storage: storage({}),
    node,
    fetchGenesis: () => { throw new Error('fetched'); },
    subscribe: () => { subs += 1; return () => {}; },
  });
  assert.equal(failed.loaded, false);
  assert.equal(failed.armed, false);
  assert.equal(failed.failed, true);
  assert.equal(subs, 0);
  assert.deepEqual(node.dataset, {keep: 'yes'});
  for (const file of ['public/beach-two/toy.js', 'public/spark/app.mjs']) {
    const src = read(file);
    assert.match(src, /armStandalonePage\(/);
    assert.match(src, /import\(\s*'\.\.\/universe\/one-universe-state\.mjs'\s*\)/);
    assert.doesNotMatch(src, /from '\.\.\/universe\/one-universe-state\.mjs'/);
  }
});

test('Spark and Beach Two publish the recorded genesis on their own when nothing is stored', async () => {
  const genesis = JSON.parse(read('public/universe/tiny-universe-genesis.json'));
  const node = {dataset: {}};
  let fetches = 0;
  let subs = 0;
  const result = await armStandalonePage({
    on: true,
    surface: 'spark',
    load: () => import('../public/universe/one-universe-state.mjs'),
    win: {},
    storage: storage({}),
    node,
    fetchGenesis: () => { fetches += 1; return Promise.resolve(genesis); },
    subscribe: () => { subs += 1; return () => {}; },
  });
  assert.equal(result.armed, true);
  assert.equal(fetches, 1);
  assert.equal(subs, 0);
  assert.equal(node.dataset.oneWorldRead, '1');
  assert.equal(node.dataset.oneWorldSurface, 'spark');
  assert.equal(node.dataset.oneWorldSeed, genesis.seed);
  assert.equal(node.dataset.oneWorldSchema, genesis.schema);
  assert.equal(node.dataset.oneWorldPlanets, genesis.planets.map((planet) => planet.id).join(','));
  const direct = await publishStandalone({
    surface: 'beach',
    win: {},
    storage: storage({}),
    node: {dataset: {}},
    fetchGenesis: () => Promise.resolve(genesis),
  });
  assert.equal(direct.source, 'genesis');
});

function nextPages(dir, prefix) {
  const out = [];
  for (const name of readdirSync(dir)) {
    if (name === 'api' || name.startsWith('_') || name.startsWith('.')) continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      const next = name.startsWith('(') && name.endsWith(')') ? prefix : prefix + '/' + name;
      out.push(...nextPages(full, next));
    } else if (name === 'page.tsx' || name === 'page.ts' || name === 'page.jsx') {
      out.push(prefix || '/');
    }
  }
  return out;
}

test('flag on: every Next route publishes the same seed, schema and planet ids', async () => {
  const genesis = JSON.parse(read('public/universe/tiny-universe-genesis.json'));
  const routes = nextPages(new URL('../app', import.meta.url).pathname, '');
  assert.ok(routes.length >= 29, String(routes.length));
  assert.equal(routes.includes('/spark/index.html'), false);
  assert.equal(routes.includes('/beach-two/toy.html'), false);
  const on = oneUniverseStateOn({env: '', storage: storage({}), search: '?oneUniverse=state'});
  assert.equal(on, true);
  const planetIds = genesis.planets.map((planet) => planet.id).join(',');
  const seen = [];
  for (const route of routes) {
    const node = {dataset: {}};
    let gets = 0;
    beginSurfaceRead({
      on,
      whenClock: () => ({get() { gets += 1; return genesis; }, subscribe() { return () => {}; }}),
      readNode: () => node,
      surfaceFor: () => surfacesForPath(route).join('+'),
      subscribe: (clock, apply) => clock.subscribe(apply),
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(gets > 0, true, route);
    assert.equal(node.dataset.oneWorldSeed, genesis.seed, route);
    assert.equal(node.dataset.oneWorldSchema, genesis.schema, route);
    assert.equal(node.dataset.oneWorldPlanets, planetIds, route);
    seen.push(node.dataset.oneWorldSeed + '|' + node.dataset.oneWorldSchema + '|' + node.dataset.oneWorldPlanets);
  }
  assert.equal(new Set(seen).size, 1);
  assert.equal(routes.length >= 29, true);
});
