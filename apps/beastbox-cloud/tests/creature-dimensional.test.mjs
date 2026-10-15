import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from 'three';
import {
  MOONWRAITH_DISPLAY_ID, SAVED_ZEREF_ID, buildDimensionalRig, dimensionalAttribution,
  dimensionalKind, measureSilhouette, poseDimensional,
} from '../lib/creature-dimensional.mjs';

function names(rig) {
  const found = [];
  rig.root.traverse(object => {if (object.name) found.push(object.name);});
  return found;
}

test('identity binding follows canonical ids, never the display name', () => {
  assert.equal(dimensionalKind({id: MOONWRAITH_DISPLAY_ID, name: 'Renamed guide'}), 'moonwraith-artistic');
  assert.equal(dimensionalKind({id: SAVED_ZEREF_ID, name: 'Zeref'}), 'dragonling-artistic');
  assert.equal(dimensionalKind({id: SAVED_ZEREF_ID, name: 'Moonwraith'}), 'dragonling-artistic');
  assert.equal(dimensionalKind({id: MOONWRAITH_DISPLAY_ID, name: 'Zeref'}), 'moonwraith-artistic');
  assert.equal(dimensionalKind({name: 'Zeref'}), null);
  assert.equal(dimensionalKind({id: 'art-frostmitt', name: 'Zeref'}), null);
  assert.equal(dimensionalKind({id: 'bb-idle-a', name: 'Zeref'}), null);
  const moon = dimensionalAttribution('moonwraith-artistic');
  const dragon = dimensionalAttribution('dragonling-artistic');
  assert.equal(moon.identityId, MOONWRAITH_DISPLAY_ID);
  assert.equal(dragon.identityId, SAVED_ZEREF_ID);
  assert.match(moon.label, /Not saved Zeref/);
  assert.match(dragon.label, /Not the Moonwraith/);
  assert.equal(moon.phenotype, 'artistic-representation');
  assert.equal(dragon.phenotype, 'artistic-representation');
});

test('moon-cat and dragonling are different articulated volumes, grounded, and not a flat plane', () => {
  const moon = buildDimensionalRig(THREE, 'moonwraith-artistic');
  const dragon = buildDimensionalRig(THREE, 'dragonling-artistic');
  try {
    const moonNames = names(moon);
    const dragonNames = names(dragon);
    for (const part of ['Body', 'Head', 'Nose', 'Eye_L', 'Eye_R', 'Lid_L', 'Wing_L', 'Wing_R', 'Leg_FL', 'Tail_1', 'Jaw']) {
      assert.ok(moonNames.includes(part), 'moon missing ' + part);
      assert.ok(dragonNames.includes(part), 'dragon missing ' + part);
    }
    assert.ok(moonNames.includes('Ear_L') && moonNames.includes('Crescent_L') && moonNames.includes('Star_L'));
    assert.ok(!moonNames.includes('TailSpade') && !moonNames.includes('Horn_L'));
    assert.ok(dragonNames.includes('Horn_L') && dragonNames.includes('TailSpade') && dragonNames.includes('Slit_L'));
    assert.ok(!dragonNames.includes('Ear_L') && !dragonNames.includes('Crescent_L') && !dragonNames.includes('Star_L'));
    assert.ok(moon.root.userData.triangles > 400, 'moon geometry is more than a billboard');
    assert.ok(dragon.root.userData.triangles > 400);
    const moonView = measureSilhouette(THREE, moon);
    const dragonView = measureSilhouette(THREE, dragon);
    assert.ok(moonView.front.noseZ > 0.2, 'nose is in front at yaw 0');
    assert.ok(moonView.back.noseZ < -0.2, 'nose is behind after a half turn');
    assert.ok(Math.abs(moonView.front.width - moonView.side.width) > 0.25, 'front and side widths differ');
    assert.ok(moonView.front.height > 0.8 && moonView.front.depth > 0.4);
    assert.ok(Math.abs(moonView.front.minY) < 0.02, 'feet meet the floor');
    assert.ok(Math.abs(dragonView.front.minY) < 0.02);
    assert.ok(dragonView.side.width > dragonView.front.width, 'dragonling is longer than it is wide');
    assert.ok(moonView.front.width > moonView.side.width, 'moon-cat reads wider from the front');
    assert.notEqual(moonView.front.width, dragonView.front.width);
  } finally {
    moon.dispose();
    dragon.dispose();
    moon.dispose();
  }
});

test('the existing renderer disposes the dimensional rig and does not start a second loop', () => {
  const source = readFileSync(new URL('../components/cosmic-companion-3d.tsx', import.meta.url), 'utf8');
  assert.match(source, /buildDimensionalRig/);
  assert.match(source, /poseDimensional/);
  assert.match(source, /cancelAnimationFrame\(animation\)/);
  assert.match(source, /rig\.dispose\(\)/);
  assert.match(source, /renderer\.dispose\(\)/);
  assert.match(source, /webglcontextlost/);
  assert.equal(source.match(/new THREE\.WebGLRenderer/g).length, 1);
});

test('poses cover breathe, blink, look, walk, sleep, react, and reduced motion', () => {
  const rig = buildDimensionalRig(THREE, 'moonwraith-artistic', {quality: 'low'});
  try {
    const open = poseDimensional(rig, {state: 'idle', time: 0, reduced: false});
    const blink = poseDimensional(rig, {state: 'idle', time: 0.62, reduced: false});
    assert.equal(open.blink, 0);
    assert.equal(blink.blink, 1);
    assert.notEqual(open.breathe, blink.breathe);
    const look = poseDimensional(rig, {state: 'thinking', time: 1.2, reduced: false});
    assert.notEqual(look.jaw, poseDimensional(rig, {state: 'listening', time: 0.4, speaking: true}).jaw);
    const speaking = poseDimensional(rig, {state: 'listening', time: 0.45, speaking: true});
    assert.ok(speaking.speaking && speaking.jaw > 0.2);
    const walk = poseDimensional(rig, {state: 'observing', time: 0.4, reduced: false});
    assert.equal(walk.walking, true);
    assert.ok(Math.abs(walk.leg) > 0.1);
    const asleep = poseDimensional(rig, {state: 'sleeping', time: 3, reduced: false});
    assert.equal(asleep.asleep, true);
    assert.equal(asleep.blink, 1);
    assert.equal(asleep.walking, false);
    const still = poseDimensional(rig, {state: 'observing', time: 4, reduced: true, speaking: true});
    assert.equal(still.walking, false);
    assert.equal(still.speaking, false);
    assert.equal(still.leg, 0);
    assert.equal(still.blink, 0);
    const react = poseDimensional(rig, {state: 'celebrating', time: 0.5, reduced: false});
    assert.ok(react.wing > 0);
  } finally {
    rig.dispose();
  }
});
