// Face channel: PROXIES from front-camera frame statistics, computed on-device
// from the same tiny frames the field-perception sampler already reduces to
// numbers. This is NOT face recognition and not a face detector model: a
// skin-tone region heuristic gives presence, scale and centroid estimates,
// plus an eye-band flicker proxy for blinks. Every value is an ESTIMATE and
// is labelled as one wherever it travels. Raw frames never leave the device.
export const FACE_KEYS = Object.freeze(['facePresent', 'faceScale', 'faceX', 'faceY', 'faceBlink']);
export const FACE_HONESTY = 'Face values are on-device frame-statistic ESTIMATES (skin-region proxies), not face recognition and not medical readings.';
const r2 = x => Math.round(x * 100) / 100;
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
// Cheap skin-like test: red-dominant ordered channels with real saturation.
const skin = (r, g, b) => r > 60 && g > 35 && b > 20 && r > g && g >= b && (r - b) > 18 && (r - g) > 8;
/**
 * Proxies for one RGBA frame (the field-perception sampler's 32x24 shape).
 * `prevEye` is the previous frame's eye-band level (from a prior call's `eye`)
 * so blink energy is a change measure, never an absolute claim.
 * Returns the five FACE_KEYS (rounded, experience-ready) plus the raw helpers
 * the caller needs: `eye` (feed back as prevEye) and `faceGreen` (mean green
 * of the skin region, the face pulse collector's input; 0 when no face).
 */
export function faceProxies(px, w, h, prevEye = null) {
  const n = w * h;
  let cnt = 0, sx = 0, sy = 0, green = 0;
  let eyeSum = 0, eyeN = 0;
  const ey0 = Math.floor(h * 0.25), ey1 = Math.ceil(h * 0.45);
  for (let i = 0; i < n; i++) {
    const r = px[i * 4], g = px[i * 4 + 1], b = px[i * 4 + 2];
    const x = i % w, y = (i / w) | 0;
    if (skin(r, g, b)) { cnt++; sx += x / w; sy += y / h; green += g; }
    if (y >= ey0 && y < ey1) { eyeSum += (r + g + b) / 3; eyeN++; }
  }
  const scale = cnt / n;
  const present = scale >= 0.04 ? 1 : 0;
  const eye = eyeN ? eyeSum / eyeN / 255 : 0;
  const blink = present && prevEye !== null && Number.isFinite(prevEye) ? clamp(Math.abs(eye - prevEye) * 6, 0, 1) : 0;
  return {
    facePresent: present,
    faceScale: r2(scale),
    faceX: present ? r2(clamp((sx / Math.max(1, cnt)) * 2 - 1, -1, 1)) : 0,
    faceY: present ? r2(clamp((sy / Math.max(1, cnt)) * 2 - 1, -1, 1)) : 0,
    faceBlink: r2(blink),
    eye,
    faceGreen: present ? green / Math.max(1, cnt) : 0,
  };
}
