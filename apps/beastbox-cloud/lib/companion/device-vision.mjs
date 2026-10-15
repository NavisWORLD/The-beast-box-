/**
 * ON-DEVICE BROWSER VISION FOR OPEN FIELD (/beast-cage/field and /beast-cage/go)
 *
 * The user's camera is the creature's eyes onto reality.
 * Uses free, on-device browser vision only:
 * 1. Downsampled 64x48 luminance & temporal frame-differencing for motion & light detection.
 * 2. Browser Shape Detection API (window.FaceDetector) when available + deterministic on-device
 *    YCbCr skin-chrominance & bilateral upper-frame head-region detector.
 * 3. Deterministic emotion-driven behavioural reaction (look, approach, flee, curious lean,
 *    happy zoomies, scared scoot) driven by deriveEmotions(beast).
 *
 * Privacy guarantee: frames are processed in a tiny offscreen memory buffer and discarded
 * immediately. Nothing is ever recorded, encoded, or uploaded. Labeled "not AR".
 */

export const VISION_WIDTH = 64;
export const VISION_HEIGHT = 48;

export function createVisionState({ width = VISION_WIDTH, height = VISION_HEIGHT } = {}) {
  return {
    width,
    height,
    prevLuma: new Float32Array(width * height),
    hasPrev: false,
    prevMeanLuma: 0.5,
    faceDetector: null,
    faceDetectorChecked: false,
    cachedHwFace: null,
    lastResult: {
      light: 0.5,
      lightDelta: 0,
      lighting: 'normal',
      motion: 0,
      motionX: 0,
      motionY: 0,
      face: { detected: false, x: 0, y: 0, size: 0, confidence: 0, method: 'none' },
      mode: 'not-ar-on-device',
    },
  };
}

/**
 * Analyze an RGBA pixel buffer (Uint8ClampedArray or Array of length width * height * 4)
 * completely on-device and deterministically.
 */
export function analyzeRgbaFrame(rgba, state = createVisionState(), { hwFace = null } = {}) {
  const w = state.width || VISION_WIDTH;
  const h = state.height || VISION_HEIGHT;
  const total = w * h;
  if (!rgba || rgba.length < total * 4) {
    return state.lastResult;
  }

  const prev = state.prevLuma;
  const hasPrev = state.hasPrev;

  let lumaSum = 0;
  let motionSum = 0;
  let motionWeightX = 0;
  let motionWeightY = 0;
  let activeMotionPixels = 0;

  // Skin-tone / face candidate accumulator (YCbCr chrominance bounds)
  let skinCount = 0;
  let skinX = 0;
  let skinY = 0;
  let skinMinX = w, skinMaxX = 0, skinMinY = h, skinMaxY = 0;

  for (let y = 0; y < h; y++) {
    const ny = (y / (h - 1)) * 2 - 1; // -1 (top) .. +1 (bottom)
    for (let x = 0; x < w; x++) {
      const idx = y * w + x;
      const p = idx * 4;
      const r = rgba[p];
      const g = rgba[p + 1];
      const b = rgba[p + 2];

      // Rec. 601 luminance (0..1)
      const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      lumaSum += luma;

      const nx = (x / (w - 1)) * 2 - 1; // -1 (left) .. +1 (right)

      if (hasPrev) {
        const diff = Math.abs(luma - prev[idx]);
        if (diff > 0.065) {
          motionSum += diff;
          motionWeightX += nx * diff;
          motionWeightY += ny * diff;
          activeMotionPixels++;
        }
      }
      prev[idx] = luma;

      // On-device YCbCr skin/face region heuristic (focused on upper/middle view where faces appear)
      if (y > h * 0.08 && y < h * 0.85 && luma > 0.16 && luma < 0.92) {
        const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
        const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;
        if (cb >= 77 && cb <= 127 && cr >= 133 && cr <= 173 && r > g && r > b) {
          skinCount++;
          skinX += nx;
          skinY += ny;
          if (x < skinMinX) skinMinX = x;
          if (x > skinMaxX) skinMaxX = x;
          if (y < skinMinY) skinMinY = y;
          if (y > skinMaxY) skinMaxY = y;
        }
      }
    }
  }

  state.hasPrev = true;
  const light = Math.round((lumaSum / total) * 1000) / 1000;
  const lightDelta = Math.round((light - state.prevMeanLuma) * 1000) / 1000;
  state.prevMeanLuma = light;
  const lighting = light < 0.22 ? 'dark' : light > 0.78 ? 'bright' : 'normal';

  const motionNorm = hasPrev
    ? Math.min(1, Math.round(((activeMotionPixels / total) * 3.2 + (motionSum / total) * 4.5) * 1000) / 1000)
    : 0;
  const motionX = motionSum > 0.001 ? Math.max(-1, Math.min(1, Math.round((motionWeightX / motionSum) * 1000) / 1000)) : 0;
  const motionY = motionSum > 0.001 ? Math.max(-1, Math.min(1, Math.round((motionWeightY / motionSum) * 1000) / 1000)) : 0;

  let face = { detected: false, x: 0, y: 0, size: 0, confidence: 0, method: 'none' };
  const effectiveHwFace = hwFace || state.cachedHwFace;
  if (effectiveHwFace && effectiveHwFace.detected) {
    face = {
      detected: true,
      x: Math.max(-1, Math.min(1, Number(effectiveHwFace.x) || 0)),
      y: Math.max(-1, Math.min(1, Number(effectiveHwFace.y) || 0)),
      size: Math.max(0.05, Math.min(1, Number(effectiveHwFace.size) || 0.25)),
      confidence: Math.max(0.5, Math.min(1, Number(effectiveHwFace.confidence) || 0.9)),
      method: 'shape-detection-facedetector',
    };
  } else {
    const skinFrac = skinCount / total;
    const bw = Math.max(1, skinMaxX - skinMinX + 1) / w;
    const bh = Math.max(1, skinMaxY - skinMinY + 1) / h;
    const aspect = bh / bw;
    // Compact face-proportioned cluster (3% to 48% of frame, reasonable aspect ratio)
    if (skinFrac >= 0.03 && skinFrac <= 0.48 && aspect >= 0.45 && aspect <= 2.4) {
      face = {
        detected: true,
        x: Math.round((skinX / skinCount) * 1000) / 1000,
        y: Math.round((skinY / skinCount) * 1000) / 1000,
        size: Math.round(Math.min(1, Math.sqrt(skinFrac) * 1.45) * 1000) / 1000,
        confidence: Math.round(Math.min(0.92, 0.45 + skinFrac * 1.8) * 1000) / 1000,
        method: 'on-device-ycbcr-cluster',
      };
    }
  }

  const res = {
    light,
    lightDelta,
    lighting,
    motion: motionNorm,
    motionX,
    motionY,
    face,
    mode: 'not-ar-on-device',
  };
  state.lastResult = res;
  return res;
}

/**
 * Sample a live HTMLVideoElement using an offscreen 64x48 canvas.
 * Never encodes or uploads frames.
 */
export function sampleVideoFrame(video, canvas, state = createVisionState()) {
  if (!video || !canvas || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
    return state.lastResult;
  }
  const w = state.width || VISION_WIDTH;
  const h = state.height || VISION_HEIGHT;
  if (canvas.width !== w) canvas.width = w;
  if (canvas.height !== h) canvas.height = h;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return state.lastResult;

  try {
    ctx.drawImage(video, 0, 0, w, h);
    const img = ctx.getImageData(0, 0, w, h);

    // Opportunistically kick off hardware FaceDetector in browser if supported
    if (!state.faceDetectorChecked && typeof window !== 'undefined') {
      state.faceDetectorChecked = true;
      const FD = window.FaceDetector;
      if (typeof FD === 'function') {
        try { state.faceDetector = new FD({ fastMode: true, maxDetectedFaces: 1 }); } catch {}
      }
    }
    if (state.faceDetector && typeof state.faceDetector.detect === 'function') {
      state.faceDetector.detect(canvas).then(faces => {
        if (Array.isArray(faces) && faces.length > 0) {
          const b = faces[0].boundingBox;
          const cx = ((b.x + b.width / 2) / w) * 2 - 1;
          const cy = ((b.y + b.height / 2) / h) * 2 - 1;
          state.cachedHwFace = {
            detected: true,
            x: cx,
            y: cy,
            size: Math.min(1, Math.hypot(b.width / w, b.height / h)),
            confidence: 0.95,
          };
        } else {
          state.cachedHwFace = null;
        }
      }).catch(() => {});
    }

    return analyzeRgbaFrame(img.data, state);
  } catch {
    return state.lastResult;
  }
}

/**
 * Deterministically decide how the creature reacts (looks, approaches, or flees)
 * to what its camera eyes see, weighted by its emotion state (lib/companion/emotion.mjs).
 */
export function visionReaction(vision, emotion = {}, { worldWidth = 2.2, name = 'Your creature' } = {}) {
  if (!vision) {
    return {
      action: 'idle',
      cue: null,
      lookAt: null,
      target: null,
      summary: 'sensing room light',
      noticeLine: '',
    };
  }

  const dom = emotion?.dominant || 'curiosity';
  const fear = Number(emotion?.fear ?? 20);
  const joy = Number(emotion?.joy ?? 50);
  const curiosity = Number(emotion?.curiosity ?? 50);
  const mischief = Number(emotion?.mischief ?? 30);

  const hasFace = Boolean(vision.face?.detected);
  const bigMotion = vision.motion >= 0.36;
  const gentleMotion = vision.motion >= 0.08 && vision.motion < 0.36;
  const suddenLightChange = Math.abs(vision.lightDelta || 0) >= 0.22;

  // Map normalized screen coordinates (-1..1) into Open Field ground coordinates (-worldWidth..worldWidth)
  const stimX = hasFace ? vision.face.x : vision.motionX || 0;
  const stimY = hasFace ? vision.face.y : vision.motionY || 0;
  const worldX = Math.max(-worldWidth, Math.min(worldWidth, stimX * worldWidth * 0.85));
  const worldZ = Math.max(-worldWidth, Math.min(worldWidth, stimY * worldWidth * 0.75));

  // 1. Sudden bright flash or startle motion or fearful creature seeing fast motion -> FLEE / SCARED SCOOT
  if (suddenLightChange || (bigMotion && (dom === 'fear' || fear >= 30))) {
    return {
      action: 'flee',
      cue: 'scared',
      lookAt: { x: worldX, z: worldZ },
      target: { x: Math.max(-worldWidth, Math.min(worldWidth, -worldX * 0.75)), z: -worldWidth * 0.55 },
      summary: suddenLightChange ? `light shift (${vision.lighting}) · ${name} scoots back` : `fast motion · ${name} flees shyly`,
      noticeLine: suddenLightChange ? `${name} notices a sudden light change and scoots back.` : `${name} startles at fast motion and flees to a safe corner.`,
    };
  }

  // 2. Face detected -> creature notices you!
  if (hasFace) {
    if (dom === 'fear' || fear >= 32) {
      return {
        action: 'flee',
        cue: 'scared',
        lookAt: { x: worldX, z: worldZ },
        target: { x: -worldX * 0.5, z: -worldWidth * 0.45 },
        summary: `face noticed · shy ${name} peeks from afar`,
        noticeLine: `${name} sees your face and shyly scoots back while peeking at you.`,
      };
    }
    if (dom === 'joy' || dom === 'mischief' || joy + mischief >= 95) {
      return {
        action: 'approach',
        cue: vision.face.size > 0.32 ? 'zoomies' : 'hop',
        lookAt: { x: worldX, z: worldZ },
        target: { x: worldX * 0.65, z: Math.min(worldWidth * 0.75, Math.max(0.25, worldZ + 0.55)) },
        summary: `face noticed · ${name} approaches happily`,
        noticeLine: `${name} spots your face and hops closer to say hi!`,
      };
    }
    return {
      action: 'approach',
      cue: 'curious',
      lookAt: { x: worldX, z: worldZ },
      target: { x: worldX * 0.55, z: Math.min(worldWidth * 0.65, Math.max(0.15, worldZ + 0.4)) },
      summary: `face noticed · ${name} leans in curiously`,
      noticeLine: `${name} notices your face and leans in for a curious look.`,
    };
  }

  // 3. Motion detected without a face
  if (bigMotion || gentleMotion) {
    if (bigMotion && (dom === 'joy' || dom === 'mischief')) {
      return {
        action: 'approach',
        cue: 'zoomies',
        lookAt: { x: worldX, z: worldZ },
        target: { x: worldX * 0.8, z: worldZ * 0.7 },
        summary: `motion noticed · ${name} chases with zoomies`,
        noticeLine: `${name} sees movement and breaks into happy zoomies!`,
      };
    }
    if (curiosity >= 45 || dom === 'curiosity') {
      return {
        action: 'approach',
        cue: 'curious',
        lookAt: { x: worldX, z: worldZ },
        target: { x: worldX * 0.6, z: worldZ * 0.5 },
        summary: `motion noticed · ${name} approaches to inspect`,
        noticeLine: `${name} notices motion and walks over to investigate.`,
      };
    }
    return {
      action: 'look',
      cue: 'idle',
      lookAt: { x: worldX, z: worldZ },
      target: null,
      summary: `motion noticed · ${name} watches`,
      noticeLine: `${name} turns its head toward the movement.`,
    };
  }

  // 4. Ambient light response (dark room -> calm/dozy look; bright light -> warm look)
  return {
    action: 'look',
    cue: null,
    lookAt: { x: 0, z: worldWidth * 0.5 },
    target: null,
    summary: `light: ${vision.lighting} (${Math.round(vision.light * 100)}%) · calm watch`,
    noticeLine: '',
  };
}
