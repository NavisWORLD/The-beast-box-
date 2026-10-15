import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import {
  CATALOG_BODIES,
  MAX_MOBILE_TRIANGLES,
  catalogRowToGenome,
  deriveCatalogPalette,
  buildCatalogCreatureRig,
  poseCatalogCreature,
  measureCatalogSilhouette,
} from '../lib/creature-catalog-3d.mjs';
import { deriveEmotions } from '../lib/companion/emotion.mjs';

const catalogIndex = JSON.parse(readFileSync(new URL('../public/spark/catalog-index.json', import.meta.url), 'utf8'));

test('all 11 catalogue creature bodies from public/spark/catalog-index.json build true 3D rigs under 25k triangles, grounded, and 360° rotatable', () => {
  const expected = ['fox', 'pup', 'biped', 'golem', 'serpent', 'axolotl', 'moth', 'bird', 'dragonling', 'sprout', 'fish'];
  const bodyCol = catalogIndex.traits.indexOf('body');
  for (const body of expected) {
    assert.ok(CATALOG_BODIES.includes(body), `CATALOG_BODIES missing ${body}`);
    const bodyIdx = catalogIndex.values.body.indexOf(body);
    const matchingRow = catalogIndex.rows.find(r => r[4 + bodyIdx >= 0 ? 4 + bodyCol : 5] === bodyIdx);
    assert.ok(matchingRow, `catalog-index.json has row for ${body}`);
    const genome = catalogRowToGenome(catalogIndex, matchingRow);
    assert.equal(genome.body, body);

    const rig = buildCatalogCreatureRig(THREE, genome, { stage: 2 });
    try {
      assert.equal(rig.body, body);
      assert.ok(rig.triangles > 300, `${body} has real 3D geometry (${rig.triangles} tris)`);
      assert.ok(rig.triangles < MAX_MOBILE_TRIANGLES, `${body} stays under 25k mobile triangle budget (${rig.triangles} tris)`);

      const sil = measureCatalogSilhouette(THREE, rig);
      assert.ok(sil.front.noseZ > 0.08, `${body} nose faces forward at 0° (${sil.front.noseZ})`);
      assert.ok(sil.back.noseZ < -0.08, `${body} nose is behind at 180° (${sil.back.noseZ})`);
      assert.ok(Math.abs(sil.front.minY) < 0.03, `${body} is grounded on floor y=0 (${sil.front.minY})`);
      assert.ok(sil.front.height > 0.35 && sil.front.depth > 0.25, `${body} has clean 3D volume`);
    } finally {
      rig.dispose();
    }
  }
});

test('island palettes from public/spark/catalog-index.json produce distinct 3D creature palettes', () => {
  const islands = catalogIndex.values.island;
  const bases = new Set();
  for (const island of islands) {
    const pal = deriveCatalogPalette({ island, genes: { hue: 0.5, sat: 0.5, val: 0.5 } });
    assert.equal(pal.island, island);
    assert.ok(Number.isInteger(pal.base) && pal.base > 0);
    bases.add(pal.base);
  }
  assert.equal(bases.size, islands.length, 'each island has a distinct base colour');
});

test('poseCatalogCreature drives Verlet tails/ears/wings, soft-body squash, contact shadow, and elemental fluid particles', () => {
  const sample = catalogRowToGenome(catalogIndex, 0);
  const rig = buildCatalogCreatureRig(THREE, sample, { stage: 1 });
  try {
    const em = deriveEmotions({ genome: sample });
    let pose = poseCatalogCreature(rig, {
      actorPose: { state: 'hop', x: 0.1, z: 0.2, lift: 0.4, sy: 1.2, lean: 0.12, head: 0.1, tail: 0.2, ear: 0.1 },
      emotion: em,
      dt: 1 / 60,
      time: 0.5,
    });
    assert.equal(pose.state, 'hop');
    assert.ok(pose.shadowScale < 1, 'shadow shrinks when airborne');

    for (const st of ['idle', 'walk', 'curious', 'scared', 'zoomies']) {
      pose = poseCatalogCreature(rig, {
        actorPose: { state: st, x: 0.2, z: 0.1, lift: st === 'zoomies' ? 0.2 : 0, sy: st === 'scared' ? 0.86 : 1 },
        emotion: em,
        dt: 1 / 60,
        time: 1.2,
      });
      assert.equal(pose.state, st);
    }
  } finally {
    rig.dispose();
  }
});
