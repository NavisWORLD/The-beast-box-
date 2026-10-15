import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  seededPrng,
  curlNoise3D,
  createVerletChain,
  stepVerletChain,
  createSoftBody,
  stepSoftBody,
  createElementFluid,
  stepElementFluid,
  createSecondaryMotion,
  stepSecondaryMotion,
  ELEMENT_FLUID_PROFILES,
} from '../lib/companion/fluid-motion.mjs';
import { deriveEmotions } from '../lib/companion/emotion.mjs';

const src = readFileSync(new URL('../lib/companion/fluid-motion.mjs', import.meta.url), 'utf8');

test('fluid-motion is strictly deterministic and uses no Math.random, clock, fetch, or storage', () => {
  assert.doesNotMatch(src, /Math\.random|Date\.now|fetch\(|localStorage/);
  const r1 = seededPrng('seed-alpha');
  const r2 = seededPrng('seed-alpha');
  const r3 = seededPrng('seed-beta');
  assert.equal(r1(), r2());
  assert.notEqual(r1(), r3());
});

test('Verlet chain simulates spring/rope inertia on tails, ears, wings, fur, and wisps', () => {
  const chain = createVerletChain({ segments: 4, segmentLength: 0.2, dir: { x: 0, y: 0, z: -1 } });
  let angles = stepVerletChain(chain, 1 / 60, { rootVelocity: { x: 2.2, y: 0.5, z: 0 }, wind: { x: 0.4, y: 0.1, z: 0 } });
  for (let i = 0; i < 15; i++) {
    angles = stepVerletChain(chain, 1 / 60, { rootVelocity: { x: 2.2, y: 0.5, z: 0 }, wind: { x: 0.4, y: 0.1, z: 0 } });
  }
  assert.equal(angles.length, 4);
  assert.ok(Math.abs(angles[0].yaw) > 0.01, 'tail root responds to lateral impulse');
  assert.ok(Math.abs(angles[3].yaw) > 0.02, 'tail tip trails with overlap');

  const still = stepVerletChain(chain, 1 / 60, { reduced: true });
  assert.equal(still[0].yaw, 0);
  assert.equal(still[0].pitch, 0);
});

test('soft-body squash and stretch preserves volume and triggers landing impact compression', () => {
  const sb = createSoftBody();
  // Simulate hop arc followed by landing
  stepSoftBody(sb, 1 / 60, { lift: 0.35, targetSy: 1.15 });
  stepSoftBody(sb, 1 / 60, { lift: 0.18, targetSy: 1.05 });
  const impact = stepSoftBody(sb, 1 / 60, { lift: 0.0, targetSy: 0.85 });
  assert.equal(impact.landed, true, 'landing impact detected');
  let minSy = impact.sy;
  for (let i = 0; i < 12; i++) {
    const p = stepSoftBody(sb, 1 / 60, { lift: 0, targetSy: 1.0 });
    minSy = Math.min(minSy, p.sy);
    assert.ok(Math.abs(p.sx * p.sy * p.sz - 1) < 0.02, 'volume-preserving squash and stretch');
  }
  assert.ok(minSy < 0.92, 'soft-body squashes below 0.92 on landing');
});

test('elemental fluid solver covers flame, ice, plasma, void, crystal, and verdant with seed + emotion determinism', () => {
  for (const el of ['ember', 'flame', 'frost', 'ice', 'crystal', 'machine', 'plasma', 'radiant', 'umbral', 'void', 'verdant', 'grove']) {
    assert.ok(ELEMENT_FLUID_PROFILES[el], `missing profile for ${el}`);
  }
  const beastJoy = {
    genome: { mouth: 'w', temperament: 'Playful', inputs: { traits: { calm: 10, focus: 50, spark: 95 } }, quantum: { entropy_norm: 0.85, marginals: [0.5] } },
    behavior: { memory: [{ kind: 'care:pet' }, { kind: 'care:spark' }] },
  };
  const beastFear = {
    genome: { mouth: 'open', temperament: 'Dreamy', inputs: { traits: { calm: 10, focus: 20, spark: 10 } }, quantum: { entropy_norm: 0.1, marginals: [0.98] } },
    energy: 15,
  };
  const emJoy = deriveEmotions(beastJoy);
  const emFear = deriveEmotions(beastFear);

  const f1 = createElementFluid({ seed: 'seed-123', element: 'ember', count: 16 });
  const f2 = createElementFluid({ seed: 'seed-123', element: 'ember', count: 16 });
  const fFear = createElementFluid({ seed: 'seed-123', element: 'ember', count: 16 });

  for (let i = 0; i < 30; i++) {
    stepElementFluid(f1, 1 / 60, { emotion: emJoy });
    stepElementFluid(f2, 1 / 60, { emotion: emJoy });
    stepElementFluid(fFear, 1 / 60, { emotion: emFear });
  }
  assert.deepEqual(f1.particles, f2.particles, 'identical seed + emotion yields identical fluid particle trajectories');
  assert.notDeepEqual(f1.particles[0].y, fFear.particles[0].y, 'different emotion state changes fluid trajectory');

  const cn = curlNoise3D(0.3, 0.5, -0.2, 1.2, 0.4);
  assert.ok(Number.isFinite(cn.vx) && Number.isFinite(cn.vy) && Number.isFinite(cn.vz));

  const sec = createSecondaryMotion({ seed: 'sec-seed', element: 'umbral', tailSegments: 4, particleCount: 16 });
  const snap = stepSecondaryMotion(sec, 1 / 60, { position: { x: 0.2, y: 0, z: 0.1 }, lift: 0.1, emotion: emJoy });
  assert.equal(snap.tailAngles.length, 4);
  assert.equal(snap.particles.length, 16);
});
