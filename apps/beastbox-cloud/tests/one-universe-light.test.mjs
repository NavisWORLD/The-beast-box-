import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {oneSunAt, skyAtElevation} from '../lib/universe/one-sun.mjs';
import {lightRigFor} from '../lib/universe/sky-view.mjs';
import {ONE_UNIVERSE_FLAG_KEY} from '../public/universe/one-universe-gate.mjs';
import {
  applyCameraLight,
  armCameraLight,
  beachSunDir,
  oneUniverseLightOn,
  pageLightOn,
  sunBranch,
} from '../public/universe/one-universe-light.mjs';

const empty = {getItem() { return null; }};
const storage = (map) => ({getItem(k) { return map[k] ?? null; }});
const src = (rel) => readFileSync(new URL('../' + rel, import.meta.url), 'utf8');

test('the light flag defaults off and does not turn on with the state flag', () => {
  assert.equal(oneUniverseLightOn({env: '', storage: empty, search: ''}), false);
  assert.equal(oneUniverseLightOn({env: 'state', storage: empty, search: '?oneUniverse=state'}), false);
  assert.equal(pageLightOn({search: '', storage: empty, env: 'light'}), false);
  assert.equal(oneUniverseLightOn({env: 'light', storage: empty, search: ''}), true);
  assert.equal(oneUniverseLightOn({env: '', storage: empty, search: '?oneUniverse=light'}), true);
  assert.equal(oneUniverseLightOn({env: '', storage: storage({[ONE_UNIVERSE_FLAG_KEY]: 'state, light'}), search: ''}), true);
  assert.equal(pageLightOn({search: '?oneUniverse=light', storage: empty}), true);
});

test('flag off does not read the clock and leaves the camera lights untouched', () => {
  let reads = 0;
  const lights = {
    key: {dir: [1, 0, 0], intensity: 2.2},
    fill: {dir: [0, 1, 0], intensity: 0.4},
    rim: {dir: [0, 0, 1], intensity: 0.8},
    sky: {zenith: [0.1, 0.2, 0.3], horizon: [0.4, 0.5, 0.6]},
  };
  const out = applyCameraLight({
    on: false,
    lights,
    up: [0, 1, 0],
    readSec() { reads += 1; return 12; },
  });
  assert.equal(reads, 0);
  assert.equal(out, lights);
  assert.deepEqual(beachSunDir({on: false, noon: [0.2, 0.9, 0.1], sec: 12, up: [0, 1, 0], readSec() { reads += 1; return 12; }}), [0.2, 0.9, 0.1]);
  assert.equal(reads, 0);
});

test('flag on uses oneSunAt, skyAtElevation and lightRigFor for that up, and keeps fill and rim', () => {
  const sec = 40;
  const up = [0, 0.6, 0.8];
  const lights = {
    key: {dir: [1, 0, 0], intensity: 9},
    fill: {dir: [0.2, 0.3, 0.4], intensity: 0.4},
    rim: {dir: [-0.5, 0.1, 0.2], intensity: 1.1},
    sky: {zenith: [1, 1, 1], horizon: [0, 0, 0]},
  };
  const out = applyCameraLight({on: true, lights, sec, up});
  const os = oneSunAt(sec, up);
  const sky = skyAtElevation(os.elevationDeg);
  const rig = lightRigFor(os);
  assert.deepEqual(out.key.dir, os.dir);
  assert.equal(out.key.intensity, rig.sunIntensity);
  assert.deepEqual(out.sky.zenith, sky.zenith);
  assert.deepEqual(out.sky.horizon, sky.horizon);
  assert.deepEqual(out.hemi.color, rig.hemiColor);
  assert.equal(out.hemi.intensity, rig.hemiIntensity);
  assert.deepEqual(out.fill, lights.fill);
  assert.deepEqual(out.rim, lights.rim);
  assert.notDeepEqual(out.key.dir, applyCameraLight({on: true, lights, sec, up: [0, 1, 0]}).key.dir);
  assert.deepEqual(beachSunDir({on: true, noon: [0, 1, 0], sec, up}), os.dir);
});

test('the beach noon branch is skipped only when the light flag is on', () => {
  assert.equal(sunBranch({lightOn: false, beach: true, noon: undefined, hold: false}), 'noon');
  assert.equal(sunBranch({lightOn: false, beach: true, noon: 'night', hold: false}), 'override');
  assert.equal(sunBranch({lightOn: false, beach: false, noon: undefined, hold: false}), 'one-sun');
  assert.equal(sunBranch({lightOn: false, beach: false, noon: undefined, hold: true}), 'hold');
  assert.equal(sunBranch({lightOn: true, beach: true, noon: undefined, hold: false}), 'one-sun');
  assert.equal(sunBranch({lightOn: true, beach: true, noon: 'night', hold: false}), 'one-sun');
  assert.equal(sunBranch({lightOn: true, beach: false, noon: 'day', hold: true}), 'hold');
});

test('a failed light-module load does not change the beach lights when the flag is on', async () => {
  const lights = {key: {intensity: 1.6}, hemi: {intensity: 0.9}};
  let loads = 0;
  const failed = await armCameraLight({
    on: true,
    lights,
    load() { loads += 1; return Promise.reject(new Error('missing')); },
  });
  assert.equal(loads, 1);
  assert.equal(failed.armed, false);
  assert.equal(failed.failed, true);
  assert.equal(failed.lights, lights);
  let skipped = 0;
  const off = await armCameraLight({
    on: false,
    lights,
    load() { skipped += 1; return Promise.reject(new Error('missing')); },
  });
  assert.equal(skipped, 0);
  assert.equal(off.armed, false);
  assert.equal(off.failed, false);
  assert.equal(off.lights, lights);
});

test('each camera reads the shared light behind the flag', () => {
  assert.match(src('components/living-world.tsx'), /sunBranch\(/);
  assert.match(src('components/cage-pocket-dimension.tsx'), /paintKeyAndSky\(/);
  assert.match(src('components/cosmic-companion-3d.tsx'), /paintKeyAndSky\(/);
  assert.match(src('components/ar-creature-stage.ts'), /paintKeyAndSky\(/);
  assert.match(src('components/zeref-glb-3d.tsx'), /paintKeyAndSky\(/);
  assert.match(src('components/universe-3d.tsx'), /paintKeyAndSky\(/);
  assert.match(src('components/tiny-universe-view.tsx'), /applyCameraLight\(/);
  assert.match(src('public/beach-two/toy.js'), /armCameraLight\(/);
  assert.match(src('components/beast-hero-3d.tsx'), /paintKeyAndSky\(/);
});

test('old light constructors stay in source', () => {
  assert.match(src('components/cage-pocket-dimension.tsx'), /createPocketSky\(/);
  assert.match(src('components/cosmic-companion-3d.tsx'), /stageRig\('thick'/);
  assert.match(src('components/creature-glb-beast.ts'), /export function beastStudio/);
  assert.match(src('components/universe-3d.tsx'), /genesis-sun\.mjs/);
  assert.match(src('components/living-world.tsx'), /noon-ish sun standing seaward of the beach/);
  assert.match(src('public/beach-two/toy.js'), /new THREE\.HemisphereLight\(0xcfe8ff,0xd8b880,0\.9\)/);
  assert.match(src('public/beach-two/toy.js'), /new THREE\.DirectionalLight\(0xfff2d8,1\.6\)/);
  assert.equal(src('public/universe/one-universe-light.mjs').includes('Math.random'), false);
  assert.equal(src('lib/universe/one-sun.mjs').includes('Math.random'), false);
});
