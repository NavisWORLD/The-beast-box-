// SensorSampleV1 and the app-shell session. Numbers only. No media, no model,
// no clock hidden inside the reducer: the caller injects time.
import {buildFaceEstimates, FACE_BIO_SCHEMA, FACE_BIO_SOURCE, FACE_BIO_HONESTY} from '../bio/face-estimates.mjs';
import {feelingsFromFace} from '../companion/emotion.mjs';

export const CADENCE_MS = 500;
export const FRESH_MS = 2000;
export const MAX_PENDING = 120;
export const SAMPLE_SCHEMA = 'sensor-sample-v1';
export const BATCH_SCHEMA = 'sensor-batch-v1';
export const FEED_OFF_SCHEMA = 'sensor-feed-off-v1';
export const RETENTION_SCHEMA = 'sensorium-retention-v1';
export const RETENTION_KEY = 'beastbox-sensorium-retention-v1';
export const feelingsLink = feelingsFromFace;

const SCALAR = ['brightness', 'hue', 'frame_motion', 'device_motion', 'sound', 'pulse_bpm'];
const CHANNEL_KEYS = ['label', 'value', 'status', 'source', 'quality'];
const SOURCES = {
  brightness: new Set(['camera', 'none']),
  hue: new Set(['camera', 'none']),
  frame_motion: new Set(['camera', 'none']),
  device_motion: new Set(['device_motion', 'none']),
  sound: new Set(['microphone', 'none']),
  pulse_bpm: new Set(['fingertip_ppg', 'wearable_ppg', 'none']),
};
const PULSE_SOURCES = new Set(['fingertip_ppg', 'wearable_ppg']);
const ABSENT_STATUS = new Set(['absent', 'off', 'denied', 'unavailable', 'stale']);
const ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const SAMPLE_KEYS = ['schema', 'surface_id', 'session_id', 'consent_epoch', 'source_seq', 'captured_at_ms', 'channels', 'face'];
const BATCH_KEYS = new Set(['schema', 'retention_consent', 'nonce', 'samples']);
const FEED_KEYS = new Set(['schema', 'retention_consent', 'session_id', 'consent_epoch']);
const FORBIDDEN = new Set(['subject_id', 'beast_id', 'scope', 'image', 'images', 'transcript', 'audio', 'video', 'frames', 'pixels', 'waveform', 'url', 'origin', 'heartbeat', 'feelings']);

const finite = (value) => typeof value === 'number' && Number.isFinite(value);
const fail = (code) => ({ok: false, code});

export function absentChannel(source = 'none', status = 'absent') {
  return {label: 'ABSENT', value: null, status, source, quality: null};
}

export function measuredChannel(name, value, source, quality = 1) {
  let number = value;
  if (name === 'hue') number = ((number % 360) + 360) % 360;
  else if (name !== 'pulse_bpm') number = Math.min(1, Math.max(0, number));
  return {label: 'MEASURED', value: number, status: 'present', source, quality};
}

/** A microphone that is off is absent. A live mic may measure real silence as 0. */
export function soundChannel(micOn, level) {
  if (!micOn) return absentChannel('none', 'denied');
  if (!finite(level)) return absentChannel('microphone', 'unavailable');
  return measuredChannel('sound', level, 'microphone', 1);
}

/** MEASURED pulse is fingertip or wearable only. A camera estimate stays absent here. */
export function pulseChannel(reading) {
  if (!reading || reading.valid !== true || !PULSE_SOURCES.has(reading.source) || !finite(reading.bpm) || !finite(reading.quality)) {
    return absentChannel('none', 'absent');
  }
  const bpm = reading.bpm;
  const quality = reading.quality;
  if (bpm < 30 || bpm > 220 || quality < 0 || quality > 1) return absentChannel('none', 'absent');
  return measuredChannel('pulse_bpm', bpm, reading.source, quality);
}

/** Camera off is null. Camera on keeps the record, including present false. */
export function faceForSample(cameraOn, proxies, pulse) {
  if (!cameraOn || !proxies) return null;
  return buildFaceEstimates({face: proxies, pulse: pulse || null});
}

export function readRetention(store) {
  try {
    const parsed = JSON.parse(store?.getItem(RETENTION_KEY) || 'null');
    if (!parsed || parsed.schema !== RETENTION_SCHEMA || parsed.accepted !== true) return {accepted: false, epoch: Number.isInteger(parsed?.epoch) ? parsed.epoch : 0};
    return {accepted: true, epoch: parsed.epoch, at: parsed.at};
  } catch {
    return {accepted: false, epoch: 0};
  }
}

export function writeRetention(store, {accepted, epoch, at}) {
  store.setItem(RETENTION_KEY, JSON.stringify({
    schema: RETENTION_SCHEMA,
    accepted: accepted === true,
    epoch: Number.isInteger(epoch) ? epoch : 0,
    at: Number.isInteger(at) ? at : 0,
  }));
}

function sameKeys(value, keys) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const got = Object.keys(value);
  return got.length === keys.length && keys.every((key) => got.includes(key));
}

function validateChannel(name, raw) {
  if (!sameKeys(raw, CHANNEL_KEYS) || !SOURCES[name].has(raw.source)) return fail('invalid');
  if (raw.status === 'present') {
    if (name === 'pulse_bpm' && !PULSE_SOURCES.has(raw.source)) return fail('camera_pulse');
    if (raw.label !== 'MEASURED' || raw.source === 'none' || !finite(raw.value) || !finite(raw.quality)) return fail('invalid');
    if (raw.quality < 0 || raw.quality > 1) return fail('invalid');
    if (name === 'hue' && (raw.value < 0 || raw.value >= 360)) return fail('invalid');
    if (name === 'pulse_bpm' && (raw.value < 30 || raw.value > 220)) return fail('invalid');
    if (name !== 'hue' && name !== 'pulse_bpm' && (raw.value < 0 || raw.value > 1)) return fail('invalid');
    return {ok: true, channel: {label: 'MEASURED', value: raw.value, status: 'present', source: raw.source, quality: raw.quality}};
  }
  if (!ABSENT_STATUS.has(raw.status) || raw.label !== 'ABSENT' || raw.value !== null || raw.quality !== null) return fail('invalid');
  return {ok: true, channel: absentChannel(raw.source, raw.status)};
}

function validateFace(raw) {
  if (raw === null) return {ok: true, face: null};
  if (!raw || typeof raw !== 'object' || raw.schema !== FACE_BIO_SCHEMA || raw.source !== FACE_BIO_SOURCE) return fail('invalid');
  if (raw.heartbeat_label !== 'ESTIMATE' || raw.honesty !== FACE_BIO_HONESTY) return fail('invalid');
  if (raw.raw_audio_published !== false || raw.raw_video_published !== false || raw.raw_frames_in_packet !== false) return fail('raw');
  const face = raw.face;
  if (!face || typeof face.present !== 'boolean' || !finite(face.scale) || !finite(face.x) || !finite(face.y) || !finite(face.blink)) return fail('invalid');
  if (face.scale < 0 || face.scale > 1 || face.x < -1 || face.x > 1 || face.y < -1 || face.y > 1 || face.blink < 0 || face.blink > 1) return fail('invalid');
  let pulse = null;
  if (raw.pulse !== null) {
    if (!raw.pulse || !finite(raw.pulse.bpm) || !finite(raw.pulse.sqi)) return fail('invalid');
    if (raw.pulse.bpm < 30 || raw.pulse.bpm > 220 || raw.pulse.sqi < 0 || raw.pulse.sqi > 1) return fail('invalid');
    pulse = {bpm: raw.pulse.bpm, sqi: raw.pulse.sqi};
  }
  return {ok: true, face: {...raw, pulse, heartbeat_label: 'ESTIMATE'}};
}

export function validateSample(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return fail('invalid');
  if (Object.keys(raw).some((key) => FORBIDDEN.has(key) || !SAMPLE_KEYS.includes(key))) return fail('invalid');
  if (SAMPLE_KEYS.filter((key) => key !== 'face').some((key) => !Object.prototype.hasOwnProperty.call(raw, key))) return fail('invalid');
  if (raw.schema !== SAMPLE_SCHEMA || !ID.test(raw.surface_id) || !ID.test(raw.session_id)) return fail('invalid');
  for (const key of ['consent_epoch', 'source_seq', 'captured_at_ms']) {
    if (!Number.isInteger(raw[key]) || raw[key] < 0) return fail('invalid');
  }
  if (!raw.channels || typeof raw.channels !== 'object' || Array.isArray(raw.channels)) return fail('invalid');
  if (Object.keys(raw.channels).some((key) => !SCALAR.includes(key))) return fail('invalid');
  const channels = {};
  for (const name of SCALAR) {
    const checked = raw.channels[name] ? validateChannel(name, raw.channels[name]) : {ok: true, channel: absentChannel()};
    if (!checked.ok) return checked;
    channels[name] = checked.channel;
  }
  const face = validateFace(Object.prototype.hasOwnProperty.call(raw, 'face') ? raw.face : null);
  if (!face.ok) return face;
  return {ok: true, sample: {
    schema: SAMPLE_SCHEMA,
    surface_id: raw.surface_id,
    session_id: raw.session_id,
    consent_epoch: raw.consent_epoch,
    source_seq: raw.source_seq,
    captured_at_ms: raw.captured_at_ms,
    channels,
    face: face.face,
  }};
}

function validateFeed(body) {
  if (Object.keys(body).some((key) => FORBIDDEN.has(key) || !FEED_KEYS.has(key))) return fail('rejected');
  if (body.retention_consent !== true) return fail('consent');
  if (!ID.test(body.session_id || '') || !Number.isInteger(body.consent_epoch) || body.consent_epoch < 0) return fail('invalid');
  return {ok: true, body: {schema: FEED_OFF_SCHEMA, retention_consent: true, session_id: body.session_id, consent_epoch: body.consent_epoch}};
}

export function validateBatch(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return fail('invalid');
  if (body.schema === FEED_OFF_SCHEMA) return validateFeed(body);
  if (Object.keys(body).some((key) => FORBIDDEN.has(key))) return fail('rejected');
  if (Object.keys(body).some((key) => !BATCH_KEYS.has(key))) return fail('invalid');
  if (body.schema !== BATCH_SCHEMA || body.retention_consent !== true) return fail('consent');
  if (!Array.isArray(body.samples) || body.samples.length < 1 || body.samples.length > 32) return fail('invalid');
  const samples = [];
  let previous = null;
  for (const raw of body.samples) {
    const checked = validateSample(raw);
    if (!checked.ok) return checked;
    if (previous !== null && checked.sample.source_seq <= previous) return fail('reordered');
    if (samples.length && (checked.sample.session_id !== samples[0].session_id || checked.sample.consent_epoch !== samples[0].consent_epoch)) return fail('invalid');
    previous = checked.sample.source_seq;
    samples.push(checked.sample);
  }
  if (String(body.nonce) !== String(samples[0].source_seq)) return fail('nonce');
  return {ok: true, body: {schema: BATCH_SCHEMA, retention_consent: true, nonce: String(samples[0].source_seq), samples}};
}

function permissionStatus(state) {
  if (state === 'denied') return 'denied';
  if (state === 'ended') return 'unavailable';
  if (state === 'granted') return 'granted';
  return 'off';
}

export function createSensoriumSession({
  now = () => 0,
  sessionId = 'shell-a2',
  surfaceId = 'app-shell',
  post = async () => ({ok: true, receipts: []}),
  onChat = null,
} = {}) {
  const state = {
    enabled: false,
    elected: false,
    retention: false,
    revoked: false,
    epoch: 0,
    seq: 0,
    lease: null,
    hidden: false,
    hiddenSent: false,
    permissions: {camera: 'off', mic: 'off', motion: 'off'},
    reading: null,
    pending: [],
    feedOff: null,
    timer: null,
    captureStarts: 0,
    committed: false,
    backpressured: false,
    lastFeelings: null,
  };
  const fresh = (at) => state.reading && Number.isInteger(state.reading.at) && at >= state.reading.at && at - state.reading.at <= FRESH_MS;

  function emit(at, channels, face) {
    state.seq += 1;
    const sample = {
      schema: SAMPLE_SCHEMA,
      surface_id: surfaceId,
      session_id: sessionId,
      consent_epoch: state.epoch,
      source_seq: state.seq,
      captured_at_ms: at,
      channels,
      face,
    };
    state.lastFeelings = face ? feelingsFromFace(face.face, face.pulse) : null;
    if (state.pending.length >= MAX_PENDING) {
      state.backpressured = true;
      state.seq -= 1;
      return null;
    }
    state.pending.push(sample);
    if (state.pending.length >= MAX_PENDING) state.backpressured = true;
    return sample;
  }

  function blank(status = 'absent') {
    return {
      brightness: absentChannel('none', status),
      hue: absentChannel('none', status),
      frame_motion: absentChannel('none', status),
      device_motion: absentChannel('none', status),
      sound: absentChannel('none', status),
      pulse_bpm: absentChannel('none', status),
    };
  }

  function channelFor(kind, name, source, value, at) {
    const permission = permissionStatus(state.permissions[kind]);
    if (permission !== 'granted') return absentChannel('none', permission === 'granted' ? 'absent' : permission);
    if (!fresh(at)) return absentChannel(source, 'stale');
    if (!finite(value)) return absentChannel(source, 'unavailable');
    return measuredChannel(name, value, source, 1);
  }

  function tick(at) {
    if (onChat) state.onChat = onChat;
    if (!state.enabled || !state.retention || state.revoked || !state.elected) return null;
    if (state.hidden) {
      if (state.hiddenSent) return null;
      state.hiddenSent = true;
      state.reading = null;
      return emit(at, blank('absent'), null);
    }
    if (state.pending.length >= MAX_PENDING) {
      state.backpressured = true;
      return null;
    }
    const fingertip = state.lease === 'fingertip';
    const reading = state.reading;
    const channels = blank('absent');
    if (fingertip) {
      channels.brightness = absentChannel('none', 'absent');
      channels.hue = absentChannel('none', 'absent');
      channels.frame_motion = absentChannel('none', 'absent');
    } else {
      channels.brightness = channelFor('camera', 'brightness', 'camera', reading?.brightness, at);
      channels.hue = channelFor('camera', 'hue', 'camera', reading?.hue, at);
      channels.frame_motion = channelFor('camera', 'frame_motion', 'camera', reading?.frameMotion, at);
    }
    channels.device_motion = channelFor('motion', 'device_motion', 'device_motion', reading?.deviceMotion, at);
    channels.sound = channelFor('mic', 'sound', 'microphone', reading?.sound, at);
    channels.pulse_bpm = fresh(at) ? pulseChannel(reading?.pulse) : absentChannel('none', 'stale');
    const cameraLive = !fingertip && state.permissions.camera === 'granted' && fresh(at);
    const face = faceForSample(cameraLive, reading?.face, reading?.facePulse);
    return emit(at, channels, face);
  }

  return {
    setEnabled(value) { state.enabled = value === true; },
    setElected(value) { state.elected = value === true; },
    setLease(value) { state.lease = value === 'fingertip' || value === 'ambient' ? value : null; },
    setPermission(kind, value) { if (kind in state.permissions) state.permissions[kind] = value; },
    setHidden(value) {
      const next = value === true;
      if (next && !state.hidden) state.hiddenSent = false;
      state.hidden = next;
      if (next) { state.reading = null; state.lastFeelings = null; }
    },
    setReading(reading) { state.reading = reading || null; },
    grantRetention(_at, epoch, seq) {
      state.retention = true;
      state.revoked = false;
      state.seq = Number.isInteger(seq) && seq >= 0 ? seq : 0;
      state.feedOff = null;
      state.epoch = Number.isInteger(epoch) && epoch > 0 ? epoch : state.epoch + 1;
    },
    revokeRetention() {
      if (state.epoch > 0) {
        state.feedOff = {schema: FEED_OFF_SCHEMA, retention_consent: true, session_id: sessionId, consent_epoch: state.epoch};
      }
      state.retention = false;
      state.revoked = true;
      state.pending = [];
      state.reading = null;
      state.lastFeelings = null;
    },
    tick,
    async flush() {
      if (state.feedOff) {
        const body = state.feedOff;
        const result = await post(body);
        if (result && result.ok) { state.feedOff = null; state.committed = true; }
        return result;
      }
      if (!state.pending.length) return {ok: true, receipts: []};
      const body = {schema: BATCH_SCHEMA, retention_consent: true, nonce: String(state.pending[0].source_seq), samples: state.pending.slice()};
      const result = await post(body);
      if (result && result.ok) {
        state.pending = [];
        state.committed = true;
        state.backpressured = false;
      }
      return result;
    },
    arm(schedule) {
      if (state.timer) return state.timer;
      state.timer = schedule(CADENCE_MS, () => tick(now()));
      return state.timer;
    },
    disarm() { state.timer = null; },
    beginCapture() {
      if (!state.enabled || !state.retention || !state.elected || state.captureStarts) return false;
      state.captureStarts += 1;
      return true;
    },
    pending() { return state.pending.slice(); },
    feedOff() { return state.feedOff; },
    lastFeelings() { return state.lastFeelings; },
    backpressure() { return state.backpressured; },
    disclosure() { return {pending: state.pending.length, committed: state.committed}; },
  };
}
