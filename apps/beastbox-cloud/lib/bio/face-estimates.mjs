// Face bio ESTIMATES: the labelled sibling of the sealed fingertip packet.
// The bio packet (bio-packet.mjs) is strictly validated and hash-sealed, so
// estimates never go inside it. They travel as this separate record with
// heartbeat_label ESTIMATE, next to the packet, through the same numeric
// channels. Raw video, audio and frames never appear here either.
export const FACE_BIO_SCHEMA = 'beastbox-face-bio-estimates-v1';
export const FACE_BIO_SOURCE = 'browser_face_front_camera';
export const FACE_BIO_HONESTY = 'Face-channel ESTIMATES from the front camera, computed on this device from frame statistics (skin-region proxies and a green-channel pulse estimate). Not face recognition, not a medical device, never MEASURED. Raw video never leaves the device.';
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const r4 = x => Math.round(x * 1e4) / 1e4;
const num = (x, d = 0) => Number.isFinite(x) ? x : d;
/** Build the estimates record from face proxies and an optional pulse estimate ({bpm,sqi} or null). */
export function buildFaceEstimates({ face, pulse = null } = {}) {
  const f = face || {};
  return {
    schema: FACE_BIO_SCHEMA,
    source: FACE_BIO_SOURCE,
    heartbeat_label: 'ESTIMATE',
    honesty: FACE_BIO_HONESTY,
    face: {
      present: num(f.facePresent) >= 1,
      scale: r4(clamp(num(f.faceScale), 0, 1)),
      x: r4(clamp(num(f.faceX), -1, 1)),
      y: r4(clamp(num(f.faceY), -1, 1)),
      blink: r4(clamp(num(f.faceBlink), 0, 1)),
    },
    pulse: pulse && Number.isFinite(pulse.bpm) ? { bpm: Math.round(clamp(pulse.bpm, 30, 220)), sqi: r4(clamp(num(pulse.sqi), 0, 1)) } : null,
    raw_audio_published: false,
    raw_video_published: false,
    raw_frames_in_packet: false,
  };
}
/** Strict-enough validation for the estimates record. Returns {ok, errors}. */
export function validateFaceEstimates(o) {
  const errors = []; const e = m => errors.push(m);
  if (!o || typeof o !== 'object' || Array.isArray(o)) return { ok: false, errors: ['not an object'] };
  if (o.schema !== FACE_BIO_SCHEMA) e('schema');
  if (o.source !== FACE_BIO_SOURCE) e('source');
  if (o.heartbeat_label !== 'ESTIMATE') e('heartbeat_label must be ESTIMATE');
  if (o.honesty !== FACE_BIO_HONESTY) e('honesty');
  if (o.raw_audio_published !== false || o.raw_video_published !== false || o.raw_frames_in_packet !== false) e('raw flags must be false');
  const f = o.face;
  if (!f || typeof f !== 'object' || typeof f.present !== 'boolean'
    || !(f.scale >= 0 && f.scale <= 1) || !(f.x >= -1 && f.x <= 1) || !(f.y >= -1 && f.y <= 1) || !(f.blink >= 0 && f.blink <= 1)) e('face');
  if (o.pulse !== null && (!o.pulse || !(o.pulse.bpm >= 30 && o.pulse.bpm <= 220) || !(o.pulse.sqi >= 0 && o.pulse.sqi <= 1))) e('pulse');
  return { ok: errors.length === 0, errors };
}
