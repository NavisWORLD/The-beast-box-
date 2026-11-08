import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createPocketPaintClaim} from '../lib/three/pocket-paint-claim.mjs';

const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const wait = ms => new Promise(r => setTimeout(r, ms));

function memory() {
  const map = new Map();
  return {getItem: key => (map.has(key) ? map.get(key) : null), setItem: (key, value) => map.set(key, String(value))};
}

test('a newer pocket tab parks the older one, a release gives the claim back, and a world message never parks', async () => {
  let clock = 1_000;
  const changes = [];
  const older = createPocketPaintClaim({storage: memory(), now: () => clock, onChange: lead => changes.push(lead)});
  await wait(40);
  assert.equal(older.leads(), true);
  clock = 2_000;
  const newer = createPocketPaintClaim({storage: memory(), now: () => clock});
  await wait(80);
  assert.equal(older.leads(), false);
  assert.equal(newer.leads(), true);
  assert.ok(changes.includes(false));
  const channel = new BroadcastChannel('beastbox-pocket-paint');
  channel.postMessage({role: 'world', id: 'living-world', stamp: 9_999_999, kind: 'claim'});
  await wait(40);
  assert.equal(newer.leads(), true);
  channel.close();
  newer.close();
  await wait(80);
  assert.equal(older.leads(), true);
  older.claim();
  await wait(40);
  assert.equal(older.leads(), true);
  older.close();
});

test('the pocket shows a parked message and the world page never waits on the bridge', () => {
  const pocket = read('components/cage-pocket-dimension.tsx');
  const world = read('components/living-world.tsx');
  assert.match(pocket, /createPocketPaintClaim/);
  assert.match(pocket, /data-pocket-parked="yes"/);
  assert.match(pocket, /painter\.leads\(\)/);
  assert.match(pocket, /isSoftwareGL\(\)/);
  assert.match(pocket, /const genesisLook=soft\?null:\(await import\('\.\.\/lib\/look\/attach'\)\)\.attachGenesisLook/);
  assert.ok(pocket.indexOf('isSoftwareGL()') < pocket.indexOf("await import('three')"));
  assert.equal(world.includes('data-bridge-settled'), false);
  assert.equal(world.includes('createPocketPaintClaim'), false);
  assert.ok(!/Math\.random/.test(read('lib/three/pocket-paint-claim.mjs')));
  assert.ok(!/Math\.random/.test(pocket));
});
