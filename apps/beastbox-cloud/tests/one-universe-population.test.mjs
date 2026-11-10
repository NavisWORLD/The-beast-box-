import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {creaturesFromStateFeed, applyPopulation, populationFromBlobs, browserPopulationOn, oneUniversePopulationOn} from '../lib/cosmos/one-population.mjs';
import {pagePopulationOn, armPopulation} from '../public/universe/one-universe-gate.mjs';
import {oneUniverseStateOn} from '../public/universe/one-universe-state.mjs';
import {oneUniverseLightOn} from '../public/universe/one-universe-light.mjs';
import {listCreations} from '../lib/companion/creations.mjs';
import {ARTIST_RESIDENTS, ARTIST_ORIGIN} from '../lib/companion/artist-residents.mjs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const genome = {stage: 1, names: {1: 'x'}, body: 'fox', island: 'Cinder Drift'};
const stateDoc = {
  schema: 'zeref-diary/v1',
  identity: {
    beast_id: 'bb-real01',
    name: 'Moss',
    source_path: 'beasts/bb-real01/provenance.json',
    source_class: 'recorded-quantum-genome',
    recorded_digest: 'abc',
    birth_spark: {source: 'recorded counts from the player\'s own save (birth seed, never re-run)'},
  },
  tick: 4,
  mood: 'content',
  last_entry_hash: 'h1',
  last_tick_at: '2026-11-09T00:00:00.000Z',
};

function session() {
  return {
    beast: {seed: 's1', displayName: 'Zeref-Nightcat-Dragon', genome, id: 'bb-real01', qbeast: {profile: {id: 'bb-real01'}}},
    bestiary: [],
  };
}

test('population flag defaults off and does not turn state or light on', () => {
  assert.equal(browserPopulationOn({env: '', search: '', storage: null}), false);
  assert.equal(oneUniversePopulationOn({env: '', search: '', storage: null}), false);
  assert.equal(pagePopulationOn({search: '', storage: null}), false);
  assert.equal(pagePopulationOn({search: '?oneUniverse=population'}), true);
  assert.equal(pagePopulationOn({search: '', storage: {getItem: () => 'population'}}), true);
  assert.equal(browserPopulationOn({env: 'population'}), true);
  assert.equal(browserPopulationOn({env: 'state'}), false);
  assert.equal(browserPopulationOn({env: 'light'}), false);
  assert.equal(browserPopulationOn({search: '?oneUniverse=state,light'}), false);
  assert.equal(oneUniverseStateOn({env: 'population'}), false);
  assert.equal(oneUniverseLightOn({env: 'population'}), false);
  assert.equal(oneUniversePopulationOn({env: 'state'}), false);
  assert.equal(oneUniversePopulationOn({env: 'light'}), false);
  assert.equal(oneUniversePopulationOn({search: '?oneUniverse=population'}), true);
  assert.equal(oneUniversePopulationOn({storage: {getItem: () => 'state,population'}}), true);
});

test('flag off does not read the feed and sends nothing', () => {
  let calls = 0;
  const out = creaturesFromStateFeed({
    on: false,
    read() {
      calls += 1;
      return [{present: true, path: 'beasts/bb-real01/state.json', state: stateDoc}];
    },
  });
  assert.equal(calls, 0);
  assert.deepEqual(out, []);
});

test('a missing or unreadable state.json sends nothing', () => {
  assert.deepEqual(creaturesFromStateFeed({on: true, documents: null}), []);
  assert.deepEqual(creaturesFromStateFeed({on: true, documents: []}), []);
  assert.deepEqual(creaturesFromStateFeed({on: true, read: () => null}), []);
  assert.deepEqual(creaturesFromStateFeed({on: true, documents: [{present: false, path: 'beasts/bb-gone/state.json', state: stateDoc}]}), []);
  assert.deepEqual(creaturesFromStateFeed({on: true, documents: [{present: true, path: 'beasts/bb-real01/state.json', state: null}]}), []);
  assert.deepEqual(populationFromBlobs({configured: false, blobs: [{path: 'beasts/bb-real01/state.json', text: JSON.stringify(stateDoc)}]}), []);
  assert.deepEqual(populationFromBlobs({configured: true, blobs: null}), []);
  assert.deepEqual(populationFromBlobs({configured: true, blobs: [{path: 'beasts/bb-gone/state.json', missing: true}]}), []);
  assert.deepEqual(populationFromBlobs({configured: true, blobs: [{path: 'beasts/bb-bad/state.json', text: '{'}]}), []);
  assert.deepEqual(populationFromBlobs({configured: true, blobs: [{path: 'beasts/bb-real01/latest.json', text: JSON.stringify(stateDoc)}]}), []);
});

test('a present state.json is copied with the source written on it', () => {
  const rows = creaturesFromStateFeed({on: true, documents: [{present: true, path: 'beasts/bb-real01/state.json', state: stateDoc}]});
  assert.equal(rows.length, 1);
  assert.equal(rows[0].id, 'bb-real01');
  assert.equal(rows[0].name, 'Moss');
  assert.equal(rows[0].source, 'beasts/bb-real01/provenance.json');
  assert.equal(rows[0].mood, 'content');
  assert.equal(rows[0].tick, 4);
  assert.equal(rows[0].lastEntryHash, 'h1');
  assert.equal(rows[0].lastTickAt, '2026-11-09T00:00:00.000Z');
  const classical = JSON.parse(JSON.stringify(stateDoc));
  classical.identity.beast_id = 'bb-class';
  classical.identity.name = 'Pebble';
  classical.identity.source_path = null;
  const fromSpark = creaturesFromStateFeed({on: true, documents: [{present: true, path: 'beasts/bb-class/state.json', state: classical}]});
  assert.equal(fromSpark.length, 1);
  assert.equal(fromSpark[0].source, classical.identity.birth_spark.source);
  const bare = {identity: {beast_id: 'bb-bare', name: 'Bare'}};
  const fromPath = creaturesFromStateFeed({on: true, documents: [{present: true, path: 'beasts/bb-bare/state.json', state: bare}]});
  assert.equal(fromPath.length, 1);
  assert.equal(fromPath[0].source, 'beasts/bb-bare/state.json');
  assert.equal(fromPath[0].mood, null);
  assert.equal(fromPath[0].tick, null);
  assert.equal(fromPath[0].name, 'Bare');
  const unnamed = creaturesFromStateFeed({on: true, documents: [{present: true, path: 'beasts/bb-noname/state.json', state: {identity: {beast_id: 'bb-noname'}}}]});
  assert.equal(unnamed[0].name, 'bb-noname');
  const noSource = creaturesFromStateFeed({on: true, documents: [{present: true, state: {identity: {beast_id: 'bb-x', name: 'X'}}}]});
  assert.deepEqual(noSource, []);
});

test('one missing document beside a real one does not invent a stand-in', () => {
  const blobs = populationFromBlobs({configured: true, blobs: [
    {path: 'beasts/bb-gone/state.json', missing: true},
    {path: 'beasts/bb-real01/state.json', text: JSON.stringify(stateDoc)},
  ]});
  assert.deepEqual(blobs.map((r) => r.id), ['bb-real01']);
  assert.equal(blobs[0].source, 'beasts/bb-real01/provenance.json');
});

test('the session beast and artist residents stay, and only a real Azure row is added', () => {
  const base = listCreations(session());
  assert.equal(base[0].cosmosId, 'bb-real01');
  for (const artist of ARTIST_RESIDENTS) {
    const row = base.find((c) => c.id === artist.id);
    assert.equal(row.origin, ARTIST_ORIGIN);
    assert.equal(artist.quantumSeed, null);
  }
  const extra = {id: 'bb-other', name: 'Other', source: 'beasts/bb-other/state.json', mood: 'curious', tick: 2, lastEntryHash: 'h2', lastTickAt: '2026-11-09T01:00:00.000Z'};
  const off = applyPopulation({on: false, creations: base, feed: [extra]});
  assert.equal(off, base);
  assert.equal(applyPopulation({on: true, creations: base, feed: null}), base);
  assert.equal(applyPopulation({on: true, creations: base, feed: []}), base);
  const feed = creaturesFromStateFeed({on: true, documents: [
    {present: true, path: 'beasts/bb-real01/state.json', state: stateDoc},
    {present: true, path: 'beasts/bb-other/state.json', state: {...stateDoc, identity: {...stateDoc.identity, beast_id: 'bb-other', name: 'Other', source_path: 'beasts/bb-other/state.json'}, mood: 'curious', tick: 2, last_entry_hash: 'h2'}},
  ]});
  const next = applyPopulation({on: true, creations: base, feed});
  assert.notEqual(next, base);
  assert.equal(next.length, base.length + 1);
  const artists = next.filter((c) => ARTIST_RESIDENTS.some((r) => r.id === c.id));
  assert.equal(artists.length, ARTIST_RESIDENTS.length);
  for (const artist of artists) assert.equal(artist.origin, ARTIST_ORIGIN);
  const yours = next.find((c) => c.id === 'seed:s1');
  assert.equal(yours.source, 'beasts/bb-real01/provenance.json');
  assert.equal(yours.origin, 'beasts/bb-real01/provenance.json');
  assert.equal(yours.mood, 'content');
  assert.equal(yours.diaryTick, 4);
  assert.equal(yours.kind, 'active');
  const other = next.find((c) => c.id === 'bb-other');
  assert.equal(other.name, 'Other');
  assert.equal(other.genome, null);
  assert.equal(other.seed, null);
  assert.equal(other.kind, 'beast');
  assert.equal(other.source, 'beasts/bb-other/state.json');
  const forgedArtist = applyPopulation({on: true, creations: base, feed: [{id: ARTIST_RESIDENTS[0].id, name: 'Not an artist', source: 'beasts/forged/state.json', mood: 'charged up', tick: 9}]});
  assert.equal(forgedArtist.find((c) => c.id === ARTIST_RESIDENTS[0].id).origin, ARTIST_ORIGIN);
  assert.equal(forgedArtist.length, base.length);
});

test('a failed load adds nothing', async () => {
  const off = await armPopulation({on: false, load: () => { throw new Error('should not load'); }});
  assert.deepEqual(off.creatures, []);
  assert.equal(off.armed, false);
  assert.equal(off.failed, false);
  const missing = await armPopulation({on: true, load: () => Promise.reject(new Error('module missing'))});
  assert.equal(missing.failed, true);
  assert.deepEqual(missing.creatures, []);
  const down = await armPopulation({on: true, load: async () => ({readPopulation() { throw new Error('azure down'); }})});
  assert.deepEqual(down.creatures, []);
  assert.equal(down.failed, true);
});

test('the shared list asks for the feed only when the flag is on, and the old population stays', () => {
  const hook = read('../components/use-creations.ts');
  const pocket = read('../components/cage-pocket-dimension.tsx');
  const route = read('../app/api/cosmos/population/route.ts');
  const pop = read('../lib/cosmos/one-population.mjs');
  const menu = read('../components/world-menu.tsx');
  const options = read('../lib/world/world-options.mjs');
  const grow = read('../components/grow-in-cosmos.tsx');
  const residents = read('../components/pocket-residents.ts');
  assert.match(hook, /browserPopulationOn\(\)/);
  assert.match(hook, /applyPopulation/);
  assert.match(hook, /\/api\/cosmos\/population/);
  assert.match(pocket, /addPocketResidents/);
  assert.match(pocket, /ARTIST_RESIDENTS/);
  assert.match(pocket, /r\.source/);
  assert.match(residents, /ARTIST_RESIDENTS\.map/);
  assert.match(route, /state\.json/);
  assert.match(route, /populationFromBlobs/);
  assert.doesNotMatch(route, /loadBeast|genesisForBeast/);
  assert.doesNotMatch(pop, /Math\.random/);
  assert.match(menu, /data-world-menu/);
  assert.match(options, /Living world/);
  assert.match(options, /Pocket explorer/);
  assert.match(grow, /data-cosmos-join/);
  assert.match(grow, /Grow in the cosmos/);
});
