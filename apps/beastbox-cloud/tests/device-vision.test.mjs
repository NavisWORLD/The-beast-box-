import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  VISION_WIDTH,
  VISION_HEIGHT,
  createVisionState,
  analyzeRgbaFrame,
  visionReaction,
} from '../lib/companion/device-vision.mjs';
import { deriveEmotions } from '../lib/companion/emotion.mjs';

const visionSrc = readFileSync(new URL('../lib/companion/device-vision.mjs', import.meta.url), 'utf8');
const fieldSrc = readFileSync(new URL('../components/camera-field.tsx', import.meta.url), 'utf8');

test('on-device vision never uploads, records, or uses random/network APIs, and stays labeled not AR', () => {
  assert.doesNotMatch(visionSrc, /MediaRecorder|toDataURL|fetch\(|XMLHttpRequest|WebSocket|localStorage|Math\.random/);
  assert.doesNotMatch(fieldSrc, /MediaRecorder|toDataURL|fetch\(/);
  assert.match(fieldSrc, /not AR/);
  assert.match(fieldSrc, /NOT RECORDED/);
});

test('analyzeRgbaFrame detects room light, temporal motion, and on-device face clusters deterministically', () => {
  const st = createVisionState({ width: VISION_WIDTH, height: VISION_HEIGHT });
  const total = VISION_WIDTH * VISION_HEIGHT;

  // Frame 1: dark room (luma ~ 0.1)
  const dark = new Uint8ClampedArray(total * 4);
  for (let i = 0; i < total; i++) {
    dark[i * 4] = 24;
    dark[i * 4 + 1] = 24;
    dark[i * 4 + 2] = 28;
    dark[i * 4 + 3] = 255;
  }
  const r1 = analyzeRgbaFrame(dark, st);
  assert.equal(r1.lighting, 'dark');
  assert.equal(r1.motion, 0);
  assert.equal(r1.face.detected, false);

  // Frame 2: bright warm skin-toned face region in upper-right quadrant + motion
  const faceFrame = new Uint8ClampedArray(dark);
  for (let y = 10; y < 30; y++) {
    for (let x = 36; x < 54; x++) {
      const p = (y * VISION_WIDTH + x) * 4;
      faceFrame[p] = 215;     // R
      faceFrame[p + 1] = 162; // G
      faceFrame[p + 2] = 132; // B
      faceFrame[p + 3] = 255;
    }
  }
  const r2 = analyzeRgbaFrame(faceFrame, st);
  assert.ok(r2.motion > 0.15, `detected temporal motion (${r2.motion})`);
  assert.ok(r2.motionX > 0.1, `motion localized on right (${r2.motionX})`);
  assert.equal(r2.face.detected, true, 'detected face cluster');
  assert.ok(r2.face.x > 0.1, `face localized on right (${r2.face.x})`);
});

test('visionReaction maps motion, faces, and light + creature emotions to look, approach, or flee', () => {
  const curiousBeast = {
    genome: { mouth: 'smile', temperament: 'Curious', inputs: { traits: { calm: 30, focus: 80, spark: 70 } }, quantum: { entropy_norm: 0.9, marginals: [0.5] } },
  };
  const shyBeast = {
    genome: { mouth: 'open', temperament: 'Dreamy', inputs: { traits: { calm: 10, focus: 10, spark: 10 } }, quantum: { entropy_norm: 0.05, marginals: [0.99] } },
    energy: 15,
    behavior: { memory: [{ kind: 'training', reward: 0.1 }, { kind: 'training', reward: 0.1 }] },
  };
  const emCurious = deriveEmotions(curiousBeast);
  const emShy = deriveEmotions(shyBeast);

  const faceObs = {
    light: 0.52,
    lightDelta: 0.01,
    lighting: 'normal',
    motion: 0.14,
    motionX: 0.4,
    motionY: -0.1,
    face: { detected: true, x: 0.4, y: -0.1, size: 0.25, confidence: 0.85, method: 'on-device-ycbcr-cluster' },
    mode: 'not-ar-on-device',
  };

  const rxApproach = visionReaction(faceObs, emCurious, { name: 'Fernkit' });
  assert.equal(rxApproach.action, 'approach');
  assert.ok(rxApproach.cue === 'curious' || rxApproach.cue === 'hop');

  const fastMotionObs = {
    ...faceObs,
    face: { detected: false, x: 0, y: 0, size: 0, confidence: 0, method: 'none' },
    motion: 0.65,
    motionX: -0.5,
    motionY: 0.2,
  };
  const rxFlee = visionReaction(fastMotionObs, emShy, { name: 'Shadebit' });
  assert.equal(rxFlee.action, 'flee');
  assert.equal(rxFlee.cue, 'scared');

  const gentleObs = {
    ...fastMotionObs,
    motion: 0.02,
    lightDelta: 0,
  };
  const rxLook = visionReaction(gentleObs, emCurious, { name: 'Fernkit' });
  assert.equal(rxLook.action, 'look');
});
