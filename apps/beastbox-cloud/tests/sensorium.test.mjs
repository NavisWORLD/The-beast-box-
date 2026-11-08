import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {feelingsFromFace, EMOTIONS} from '../lib/companion/emotion.mjs';
import {buildFaceEstimates} from '../lib/bio/face-estimates.mjs';
import {
  CADENCE_MS,
  soundChannel,
  pulseChannel,
  faceForSample,
  feelingsLink,
  validateBatch,
  readRetention,
  writeRetention,
  createSensoriumSession,
} from '../lib/sensorium/sample.mjs';

const read = (p) => readFileSync(new URL('../' + p, import.meta.url), 'utf8');
const T0 = 1_700_000_000_000;
const FACE = {facePresent: 1, faceScale: 0.22, faceX: 0.05, faceY: -0.1, faceBlink: 0.3, eye: 0.4, faceGreen: 140};

function reading(at, extra = {}) {
  return {at, brightness: 0.42, hue: 18, frameMotion: 0.05, deviceMotion: 0.1, sound: 0.2, face: FACE, facePulse: null, pulse: null, ...extra};
}

function liveSession(post, extras = {}) {
  const chats = [];
  const session = createSensoriumSession({
    now: () => T0,
    sessionId: 'shell-a2',
    surfaceId: 'app-shell',
    post,
    onChat: () => chats.push('chat'),
    ...extras,
  });
  session.setEnabled(true);
  session.setElected(true);
  session.grantRetention(T0);
  session.setLease('ambient');
  session.setPermission('camera', 'granted');
  session.setPermission('mic', 'granted');
  session.setPermission('motion', 'granted');
  return {session, chats};
}

test('sixty seconds of foreground ticks emit ordered samples and never a chat', async () => {
  assert.equal(CADENCE_MS, 500);
  const posted = [];
  const {session, chats} = liveSession(async (batch) => {
    posted.push(batch);
    return {ok: true, receipts: batch.samples.map((sample, index) => ({status: 'admitted', sequence: index + 1}))};
  });
  for (let i = 0; i < 120; i++) {
    const at = T0 + i * CADENCE_MS;
    session.setReading(reading(at));
    const sample = session.tick(at);
    assert.equal(sample.source_seq, i + 1);
    assert.equal(sample.captured_at_ms, at);
    assert.equal(sample.schema, 'sensor-sample-v1');
    assert.equal(sample.consent_epoch, 1);
    assert.equal(Object.hasOwn(sample, 'feelings'), false);
    assert.equal(Object.hasOwn(sample, 'subject_id'), false);
  }
  const result = await session.flush();
  assert.equal(chats.length, 0);
  assert.equal(result.ok, true);
  assert.equal(posted.length, 1);
  assert.equal(posted[0].schema, 'sensor-batch-v1');
  assert.equal(posted[0].retention_consent, true);
  assert.equal(posted[0].nonce, '1');
  assert.equal(posted[0].samples.length, 120);
  assert.deepEqual(posted[0].samples.map((sample) => sample.source_seq), Array.from({length: 120}, (_, i) => i + 1));
  assert.equal(session.disclosure().pending, 0);
  assert.equal(session.disclosure().committed, true);
});

test('microphone and camera permissions are independent, and a missing mic is absent rather than silence', () => {
  assert.deepEqual(soundChannel(false, 0), {label: 'ABSENT', value: null, status: 'denied', source: 'none', quality: null});
  assert.equal(soundChannel(true, 0).label, 'MEASURED');
  assert.equal(soundChannel(true, 0).value, 0);
  const {session} = liveSession(async () => ({ok: true}));
  session.setPermission('mic', 'denied');
  session.setReading(reading(T0, {sound: 0}));
  const quiet = session.tick(T0);
  assert.equal(quiet.channels.sound.label, 'ABSENT');
  assert.equal(quiet.channels.sound.value, null);
  assert.equal(quiet.channels.sound.status, 'denied');
  assert.equal(quiet.channels.brightness.label, 'MEASURED');
  assert.equal(quiet.channels.brightness.value, 0.42);
  assert.equal(quiet.face.heartbeat_label, 'ESTIMATE');
  session.setPermission('mic', 'granted');
  session.setPermission('camera', 'denied');
  session.setReading(reading(T0 + 500, {sound: 0}));
  const blind = session.tick(T0 + 500);
  assert.equal(blind.channels.brightness.value, null);
  assert.equal(blind.channels.hue.value, null);
  assert.equal(blind.channels.frame_motion.value, null);
  assert.equal(blind.channels.brightness.status, 'denied');
  assert.equal(blind.face, null);
  assert.equal(blind.channels.sound.label, 'MEASURED');
  assert.equal(blind.channels.sound.value, 0);
  assert.equal(blind.channels.sound.source, 'microphone');
});

test('face records stay estimates, a face that leaves is kept, and face pulse is never measured pulse', () => {
  const gone = faceForSample(true, {facePresent: 0, faceScale: 0.02, faceX: 0, faceY: 0, faceBlink: 0}, {bpm: 72, sqi: 0.55});
  assert.equal(gone.face.present, false);
  assert.equal(gone.heartbeat_label, 'ESTIMATE');
  assert.equal(gone.pulse.bpm, 72);
  assert.deepEqual(gone, buildFaceEstimates({
    face: {facePresent: 0, faceScale: 0.02, faceX: 0, faceY: 0, faceBlink: 0},
    pulse: {bpm: 72, sqi: 0.55},
  }));
  assert.equal(faceForSample(false, FACE, {bpm: 72, sqi: 0.55}), null);
  assert.equal(feelingsLink, feelingsFromFace);
  assert.deepEqual(feelingsLink(gone.face, gone.pulse).words, EMOTIONS);
  const {session} = liveSession(async () => ({ok: true}));
  session.setReading(reading(T0, {
    face: {facePresent: 0, faceScale: 0.02, faceX: 0, faceY: 0, faceBlink: 0, eye: 0, faceGreen: 0},
    facePulse: {bpm: 72, sqi: 0.55},
    pulse: {valid: true, bpm: 72, quality: 0.9, source: 'face_camera'},
  }));
  const sample = session.tick(T0);
  assert.equal(sample.face.face.present, false);
  assert.equal(sample.face.heartbeat_label, 'ESTIMATE');
  assert.equal(sample.face.pulse.bpm, 72);
  assert.equal(sample.channels.pulse_bpm.label, 'ABSENT');
  assert.equal(sample.channels.pulse_bpm.value, null);
  assert.deepEqual(session.lastFeelings().words, EMOTIONS);
  assert.equal(Object.hasOwn(sample, 'feelings'), false);
  const cameraPulse = pulseChannel({valid: true, bpm: 72, quality: 0.9, source: 'face_camera'});
  assert.equal(cameraPulse.value, null);
  const fingertip = pulseChannel({valid: false, bpm: 72, quality: 0.2, source: 'fingertip_ppg'});
  assert.equal(fingertip.label, 'ABSENT');
  assert.equal(fingertip.value, null);
});

test('fingertip capture does not publish finger colour as room light, and wearable pulse can be measured', () => {
  const {session} = liveSession(async () => ({ok: true}));
  session.setLease('fingertip');
  session.setReading(reading(T0, {
    brightness: 0.99,
    hue: 12,
    pulse: {valid: true, bpm: 72, quality: 0.8, source: 'fingertip_ppg'},
  }));
  const finger = session.tick(T0);
  assert.equal(finger.channels.brightness.label, 'ABSENT');
  assert.equal(finger.channels.hue.value, null);
  assert.equal(finger.channels.frame_motion.value, null);
  assert.equal(finger.face, null);
  assert.equal(finger.channels.pulse_bpm.label, 'MEASURED');
  assert.equal(finger.channels.pulse_bpm.value, 72);
  assert.equal(finger.channels.pulse_bpm.source, 'fingertip_ppg');
  session.setLease('ambient');
  session.setReading(reading(T0 + 500, {pulse: {valid: true, bpm: 64, quality: 0.7, source: 'wearable_ppg'}}));
  const worn = session.tick(T0 + 500);
  assert.equal(worn.channels.brightness.value, 0.42);
  assert.equal(worn.channels.pulse_bpm.source, 'wearable_ppg');
  assert.equal(worn.channels.pulse_bpm.value, 64);
  assert.equal(worn.face.heartbeat_label, 'ESTIMATE');
});

test('hidden, ended, stale, and revoked channels become null and nothing is held or invented', async () => {
  const posted = [];
  const {session} = liveSession(async (batch) => {
    posted.push(batch);
    return {ok: true, receipts: []};
  });
  session.setReading(reading(T0, {brightness: 0.9}));
  session.setHidden(true);
  const hidden = session.tick(T0);
  assert.equal(hidden.channels.brightness.value, null);
  assert.equal(hidden.channels.sound.value, null);
  assert.equal(hidden.face, null);
  assert.equal(session.tick(T0 + 500), null);
  session.setHidden(false);
  const resumed = session.tick(T0 + 1000);
  assert.equal(resumed.channels.brightness.value, null);
  session.setPermission('camera', 'ended');
  session.setReading(reading(T0 + 1500, {brightness: 0.9}));
  const ended = session.tick(T0 + 1500);
  assert.equal(ended.channels.brightness.value, null);
  assert.equal(ended.channels.brightness.status, 'unavailable');
  assert.equal(ended.face, null);
  session.setPermission('camera', 'granted');
  session.setReading(reading(T0, {brightness: 0.9}));
  const stale = session.tick(T0 + 2500);
  assert.equal(stale.channels.brightness.status, 'stale');
  assert.equal(stale.channels.brightness.value, null);
  session.setReading(reading(T0 + 3000, {brightness: 0.15}));
  session.tick(T0 + 3000);
  assert.ok(session.pending().length > 0);
  session.revokeRetention(T0 + 3000);
  assert.equal(session.pending().length, 0);
  assert.equal(session.tick(T0 + 3500), null);
  assert.equal(session.feedOff().schema, 'sensor-feed-off-v1');
  assert.equal(session.feedOff().consent_epoch, 1);
  assert.equal(session.feedOff().session_id, 'shell-a2');
  await session.flush();
  assert.equal(posted[0].schema, 'sensor-feed-off-v1');
  assert.equal(posted[0].samples, undefined);
  session.grantRetention(T0 + 4000);
  session.setReading(reading(T0 + 4000));
  const again = session.tick(T0 + 4000);
  assert.equal(again.consent_epoch, 2);
  assert.equal(again.source_seq, 1);
});

test('the shell keeps one timer and one capture, and a second tab does not produce', () => {
  const {session} = liveSession(async () => ({ok: true}));
  let timers = 0;
  const schedule = () => { timers += 1; return {id: timers}; };
  session.arm(schedule);
  session.arm(schedule);
  assert.equal(timers, 1);
  assert.equal(session.beginCapture(), true);
  assert.equal(session.beginCapture(), false);
  session.disarm();
  session.setElected(false);
  session.setReading(reading(T0));
  assert.equal(session.tick(T0), null);
  assert.equal(session.beginCapture(), false);
  session.setEnabled(false);
  session.setElected(true);
  assert.equal(session.tick(T0), null);
});

test('a continued epoch does not reuse source sequence 1', () => {
  const {session} = liveSession(async () => ({ok: true}));
  session.grantRetention(T0, 3, 40);
  session.setReading(reading(T0));
  const sample = session.tick(T0);
  assert.equal(sample.source_seq, 41);
  assert.equal(sample.consent_epoch, 3);
});

test('samples wait for the new retention consent, and a full queue pauses without dropping the earlier ones', async () => {
  const session = createSensoriumSession({sessionId: 'shell-a2', surfaceId: 'app-shell', post: async () => { throw new Error('offline'); }});
  session.setEnabled(true);
  session.setElected(true);
  session.setLease('ambient');
  session.setPermission('camera', 'granted');
  session.setPermission('mic', 'granted');
  session.setPermission('motion', 'granted');
  session.setReading(reading(T0));
  assert.equal(session.tick(T0), null);
  session.grantRetention(T0);
  for (let i = 0; i < 121; i++) {
    const at = T0 + i * CADENCE_MS;
    session.setReading(reading(at));
    session.tick(at);
  }
  assert.equal(session.backpressure(), true);
  assert.equal(session.pending().length, 120);
  assert.equal(session.pending()[0].source_seq, 1);
  assert.equal(session.pending()[119].source_seq, 120);
  await assert.rejects(() => session.flush());
  assert.equal(session.disclosure().pending, 120);
  assert.equal(session.disclosure().committed, false);
  const store = new Map();
  const memory = {getItem: (key) => store.get(key) ?? null, setItem: (key, value) => store.set(key, value)};
  assert.equal(readRetention(memory).accepted, false);
  writeRetention(memory, {accepted: true, epoch: 1, at: T0});
  assert.equal(readRetention(memory).accepted, true);
  assert.equal(readRetention(memory).epoch, 1);
  assert.doesNotMatch(JSON.stringify([...store.values()]), /origin|heartbeat|transcript|image/i);
});

test('a batch cannot name a subject, carry media, or skip retention consent', () => {
  const {session} = liveSession(async () => ({ok: true}));
  session.setReading(reading(T0));
  const sample = session.tick(T0);
  const good = {schema: 'sensor-batch-v1', retention_consent: true, nonce: '1', samples: [sample]};
  assert.equal(validateBatch(good).ok, true);
  for (const extra of [
    {subject_id: 'bb-7f9c2a03'},
    {beast_id: 'bb-deada969'},
    {scope: 'guest'},
    {image: 'data:image/png;base64,aaaa'},
    {transcript: 'hello'},
    {audio: [0.1, 0.2]},
    {origin: 'someone'},
    {feelings: {joy: 1}},
  ]) {
    assert.equal(validateBatch({...good, ...extra}).ok, false, JSON.stringify(extra));
  }
  assert.equal(validateBatch({...good, retention_consent: false}).ok, false);
  assert.equal(validateBatch({...good, nonce: '9'}).ok, false);
  assert.equal(validateBatch({...good, samples: [sample, sample]}).ok, false);
  const tampered = structuredClone(sample);
  tampered.channels.pulse_bpm = {label: 'MEASURED', value: 70, status: 'present', source: 'camera', quality: 1};
  assert.equal(validateBatch({...good, samples: [tampered]}).ok, false);
});

test('the app shell owns one sensorium, share world stops hardcoding silence, and the old consent sentence stays', () => {
  const layout = read('app/layout.tsx');
  const provider = read('components/sensorium-provider.tsx');
  const runtime = read('lib/sensorium/runtime.ts');
  const route = read('app/api/zeref/sensorium/route.ts');
  const share = read('components/share-world.tsx');
  const stream = read('lib/environment/share-stream.ts');
  const consent = read('components/environment-consent.tsx');
  const bridge = read('bridge/owner_bridge.py');
  assert.match(layout, /SensoriumProvider/);
  assert.match(layout, /process\.env\.BEASTBOX_LIVED_BACKBONE/);
  assert.match(layout, /isOwner\(/);
  assert.doesNotMatch(provider, /fetch\('\/api\/zeref\/sensorium', \{cache/);
  assert.match(provider, /data-sensorium-indicator/);
  assert.match(provider, /data-sensorium-stop/);
  assert.match(provider, /Keep derived sense numbers/);
  assert.match(provider, /enabled !== true|!status\.enabled|enabled===false/);
  assert.match(runtime, /getUserMedia\(\{audio/);
  assert.match(runtime, /getUserMedia\(\{video/);
  assert.match(runtime, /analysePpg/);
  assert.match(runtime, /feelingsFromFace/);
  assert.match(runtime, /visibilitychange/);
  assert.match(runtime, /pagehide/);
  assert.match(runtime, /claimSensorLease|releaseForSensorium/);
  assert.doesNotMatch(runtime, /Math\.random|SpeechRecognition|MediaRecorder|\/api\/guest/);
  assert.match(route, /process\.env\.BEASTBOX_LIVED_BACKBONE/);
  assert.match(route, /isOwner\(/);
  assert.match(route, /validateBatch/);
  assert.match(route, /private, no-store/);
  assert.match(route, /search/);
  assert.doesNotMatch(route, /Math\.random|console\.log|\/api\/guest|subject_id/);
  assert.doesNotMatch(share, /loudness:\s*0|pitchHz:\s*0/);
  assert.match(share, /measureSound/);
  assert.match(stream, /claimSensorLease/);
  assert.match(stream, /getUserMedia\(\{video/);
  assert.match(stream, /getUserMedia\(\{audio/);
  assert.match(consent, /sensorLeaseHolder\(\) === 'sensorium'/);
  assert.match(consent, /Stop sharing deletes your saved numbers\./);
  assert.doesNotMatch(consent, /Keep derived sense numbers/);
  assert.match(bridge, /BEASTBOX_LIVED_ORIGIN_COMMITMENT/);
  assert.match(bridge, /BEASTBOX_LIVED_PRIOR_HEAD/);
  assert.match(bridge, /"sensorium"/);
  for (const file of [provider, runtime, route, share, stream, read('lib/sensorium/sample.mjs')]) {
    assert.doesNotMatch(file, /Math\.random/);
  }
});
