import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pageCamerasOn, armCameras} from '../public/universe/one-universe-gate.mjs';
import {oneUniverseCamerasOn, browserCamerasOn, resolveMenuEntry, publishUniverseCamera, cameraFrame, activeCamera, cameraForPath} from '../public/universe/one-universe-cameras.mjs';
import {oneUniverseStateOn} from '../public/universe/one-universe-state.mjs';
import {oneUniverseLightOn} from '../public/universe/one-universe-light.mjs';
import {oneUniversePopulationOn} from '../lib/cosmos/one-population.mjs';
import {oneUniverseTickOn} from '../public/universe/one-universe-tick.mjs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

/** Every old menu entry. A camera id is the new job. A null camera keeps the old target. */
const EXPECTED = [
  {id: 'living', label: 'Living world', camera: 'living', role: 'camera', file: '../lib/world/world-options.mjs'},
  {id: 'pocket', label: 'Pocket explorer', camera: 'pocket', role: 'camera', file: '../lib/world/world-options.mjs'},
  {id: 'classic', label: 'Classic pixel sprite', camera: null, role: 'overlay', file: '../lib/world/world-options.mjs'},
  {id: 'beach', label: 'Beach view', camera: 'beach', role: 'camera', file: '../components/living-world.tsx'},
  {id: 'spawn', label: 'Spawn in', camera: 'living', role: 'pose', file: '../components/living-world.tsx'},
  {id: 'watch', label: 'Watch your beast', camera: 'orbit', role: 'camera', file: '../components/living-world.tsx'},
  {id: 'orbit-label', label: 'Orbit view', camera: 'orbit', role: 'camera', file: '../components/living-world.tsx'},
  {id: 'fullscreen', label: 'Full screen', camera: null, role: 'viewport', file: '../components/living-world.tsx'},
  {id: 'spawn-fp', label: 'Spawn in · First person', camera: 'living', role: 'pose', file: '../components/living-world.tsx'},
  {id: 'view-fp', label: 'View: First person', camera: 'living', role: 'pose', file: '../components/living-world.tsx'},
  {id: 'view-orbit', label: 'View: Orbit', camera: 'orbit', role: 'camera', file: '../components/living-world.tsx'},
  {id: 'weather', label: 'Weather:', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'time', label: 'Time: live cycle', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'treat', label: 'Drop a treat', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'flower', label: 'Plant a flower', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'poke', label: 'Poke your Beast', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'residents', label: 'Who lives here', camera: null, role: 'control', file: '../components/cage-pocket-dimension.tsx'},
  {id: 'reset', label: 'Reset 3D camera', camera: null, role: 'control', file: '../lib/world/world-options.mjs'},
  {id: 'diary', label: 'Diary', camera: null, role: 'unchanged', file: '../lib/world/world-options.mjs'},
  {id: 'look', label: 'Look Closer', camera: 'look', role: 'camera', file: '../lib/world/world-options.mjs'},
  {id: 'senses', label: 'Senses (camera & mic)', camera: null, role: 'unchanged', file: '../lib/world/world-options.mjs'},
  {id: 'privacy', label: 'Privacy and info', camera: null, role: 'unchanged', file: '../components/world-menu.tsx'},
  {id: 'map', label: 'Where am I in the one world?', camera: null, role: 'unchanged', file: '../components/world-menu.tsx'},
  {id: 'enter-tiny', label: 'Enter the tiny world', camera: 'tiny', role: 'expansion', file: '../components/home-pocket.tsx'},
  {id: 'share', label: 'Share my world', camera: null, role: 'unchanged', file: '../components/home-pocket.tsx'},
  {id: 'sound', label: 'Sound, game & help controls', camera: null, role: 'unchanged', file: '../components/home-pocket.tsx'},
  {id: 'tiny-link', label: 'Tiny World', camera: 'tiny', role: 'expansion', file: '../components/beast-cage-portal.tsx'},
  {id: 'universe', label: 'data-universe-details', camera: 'tiny', role: 'expansion', file: '../components/tiny-universe-view.tsx'},
  {id: 'beach-two', label: 'armStandalonePage', camera: 'beach', role: 'camera', file: '../public/beach-two/toy.js'},
  {id: 'turntable', label: 'Rotate 360°', camera: 'look', role: 'camera', file: '../app/beast-cage/turntable/page.tsx'},
  {id: 'pedestal', label: 'data-look-pedestal', camera: 'look', role: 'framing', file: '../app/beast-cage/turntable/page.tsx'},
];

test('cameras flag defaults off and does not turn the other flags on', () => {
  assert.equal(pageCamerasOn({search: '', storage: null}), false);
  assert.equal(oneUniverseCamerasOn({env: '', search: '', storage: null}), false);
  assert.equal(browserCamerasOn({env: '', search: '', storage: null}), false);
  assert.equal(pageCamerasOn({search: '?oneUniverse=cameras'}), true);
  assert.equal(pageCamerasOn({search: '', storage: {getItem: () => 'cameras'}}), true);
  assert.equal(browserCamerasOn({env: 'cameras'}), true);
  assert.equal(browserCamerasOn({env: 'state'}), false);
  assert.equal(browserCamerasOn({env: 'light'}), false);
  assert.equal(browserCamerasOn({env: 'population'}), false);
  assert.equal(browserCamerasOn({env: 'tick'}), false);
  assert.equal(oneUniverseStateOn({env: 'cameras'}), false);
  assert.equal(oneUniverseLightOn({env: 'cameras'}), false);
  assert.equal(oneUniversePopulationOn({env: 'cameras'}), false);
  assert.equal(oneUniverseTickOn({env: 'cameras'}), false);
});

test('flag off does not read the clock or write a camera', () => {
  let reads = 0;
  const node = {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
  const out = publishUniverseCamera({
    on: false,
    camera: 'living',
    node,
    path: '/universe',
    clock: {get() { reads += 1; return {seed: 's', tick: 3}; }},
  });
  assert.equal(reads, 0);
  assert.equal(out.written, false);
  assert.equal(node.attrs['data-universe-camera'], undefined);
  const frame = cameraFrame({on: false, camera: 'tiny', world: {seed: 's', tick: 3}});
  assert.equal(frame.read, false);
  assert.equal(frame.grew, false);
});

test('every old menu entry still resolves', () => {
  const doc = read('../../../docs/reports/2026-11-10-one-universe-camera-map.md');
  for (const row of EXPECTED) {
    const got = resolveMenuEntry(row.id);
    assert.equal(got.camera, row.camera, row.id);
    assert.equal(got.role, row.role, row.id);
    assert.equal(got.id, row.id);
    assert.match(read(row.file), new RegExp(row.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.ok(doc.includes(row.label), row.label);
  }
  assert.equal(resolveMenuEntry('missing'), null);
  assert.equal(cameraForPath('/universe'), 'tiny');
  assert.equal(cameraForPath('/beast-cage/world'), 'tiny');
  assert.equal(cameraForPath('/beast-cage/look'), 'look');
  assert.equal(cameraForPath('/beast-cage/turntable'), 'look');
  assert.equal(cameraForPath('/beach-two'), 'beach');
  assert.equal(cameraForPath('/beach-two/toy.html'), 'beach');
  assert.equal(cameraForPath('/sol-game'), null);
  assert.equal(activeCamera({path: '/universe', stored: 'pocket'}), 'tiny');
  assert.equal(activeCamera({path: '/beast-cage', stored: 'orbit'}), 'orbit');
  assert.equal(activeCamera({path: '/beast-cage/world', stored: 'beach'}), 'beach');
  const turn = read('../app/beast-cage/turntable/page.tsx');
  assert.match(turn, /ANGLES=\[0,90,180,270\]/);
  assert.match(turn, /\{a\}°/);
  assert.match(turn, /Rotate 360°/);
  assert.match(turn, /data-look-pedestal/);
});

test('a camera reads the one world and does not grow or invent a tick', () => {
  const world = {schema: 'tiny-universe/v1', seed: 'same', tick: 8, planets: [{id: 'p'}]};
  let grows = 0;
  const node = {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
  const out = publishUniverseCamera({
    on: true,
    camera: 'tiny',
    path: '/universe',
    node,
    clock: {get: () => world, step() { grows += 1; }},
    grow() { grows += 1; },
  });
  assert.equal(grows, 0);
  assert.equal(out.grew, false);
  assert.equal(out.camera, 'tiny');
  assert.equal(out.expansion, true);
  assert.equal(out.seed, 'same');
  assert.equal(out.tick, 8);
  assert.equal(out.sky, 'one-sun');
  assert.equal(out.population, 'one');
  assert.equal(node.attrs['data-universe-camera'], 'tiny');
  assert.equal(node.attrs['data-universe-expansion'], 'tiny');
  assert.equal(node.attrs['data-universe-camera-tick'], '8');
  const missing = publishUniverseCamera({on: true, camera: 'living', node, clock: null});
  assert.equal(missing.tick, null);
  assert.equal(missing.grew, false);
  assert.equal(node.attrs['data-universe-camera-tick'], undefined);
  const look = cameraFrame({on: true, camera: 'look', world: {seed: 'same', tick: 0}});
  assert.equal(look.camera, 'look');
  assert.equal(look.pedestal, 'framing');
  assert.equal(look.tick, 0);
  assert.equal(look.expansion, false);
  const blank = cameraFrame({on: true, camera: 'pocket', world: null});
  assert.equal(blank.tick, null);
  assert.equal(blank.seed, null);
});

test('a failed camera load does not write a camera', async () => {
  const node = {attrs: {kept: '1'}, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; }};
  const off = await armCameras({on: false, node, load: () => { throw new Error('should not load'); }});
  assert.equal(off.armed, false);
  assert.equal(off.failed, false);
  assert.deepEqual(node.attrs, {kept: '1'});
  const missing = await armCameras({on: true, node, load: () => Promise.reject(new Error('module missing'))});
  assert.equal(missing.failed, true);
  assert.equal(node.attrs['data-universe-camera'], undefined);
});

test('both menus stay, and the flag-off paths stay in source', () => {
  const menu = read('../components/world-menu.tsx');
  const options = read('../lib/world/world-options.mjs');
  const home = read('../components/home-pocket.tsx');
  const cage = read('../components/beast-cage-portal.tsx');
  const living = read('../components/living-world.tsx');
  const provider = read('../components/one-world-provider.tsx');
  const cameras = read('../public/universe/one-universe-cameras.mjs');
  const gate = read('../public/universe/one-universe-gate.mjs').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  assert.match(menu, /data-world-menu/);
  assert.match(menu, /data-menu-look/);
  assert.match(menu, /data-menu-reset/);
  assert.match(menu, /data-menu-diary/);
  assert.match(menu, /Living world|data-world-view/);
  assert.match(options, /Living world/);
  assert.match(options, /Pocket explorer/);
  assert.match(home, /data-world-menu|WorldMenu/);
  assert.match(cage, /WorldMenu/);
  assert.match(home, /Enter the tiny world/);
  assert.match(cage, /Tiny World/);
  assert.match(living, /setBeachCam/);
  assert.match(living, /data-lw-beachcam/);
  assert.match(living, /grow\(u,1\)/);
  assert.match(menu, /one-universe-cameras\.mjs/);
  assert.match(provider, /pageCamerasOn/);
  assert.doesNotMatch(cameras, /Math\.random/);
  assert.doesNotMatch(cameras, /grow\(/);
  assert.doesNotMatch(gate, /process\.env/);
  assert.doesNotMatch(gate, /Math\.random/);
  assert.match(read('../app/beast-cage/look/page.tsx'), /beast-cage\/turntable|Turntable|turntable/);
});
