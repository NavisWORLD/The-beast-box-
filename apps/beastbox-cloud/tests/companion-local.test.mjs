import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {loadQbeast} from '../public/spark/qbeast.mjs';
import {
  CompanionMemory, RECORDED_RUN, acceptHearing, acceptVision, birth, loopbackOnly, reply, simulateLive,
} from '../lib/companion-local.mjs';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');

test('recorded seed matches the compact IBM run and the Python personality card', () => {
  assert.equal(RECORDED_RUN.counts_sha256, 'd437ad227c2e36c82041e721dbf1773f774ad3668dc6db3c639572ef74c44296');
  assert.equal(RECORDED_RUN.shots, 733 + 3363);
  const born = birth('serene');
  assert.equal(born.card.name, 'Glacecoil');
  assert.equal(born.card.island, 'The Pale Expanse');
  assert.equal(born.card.tic, 'rim?');
  assert.equal(born.card.catchphrase, 'star crumb');
  assert.equal(born.card.seed, '99dc004a31cc649f94937ba465c119ec57fe625dee91a348304e7be3a8124186');
  assert.equal(born.card.claims.conscious, false);
  assert.equal(born.traits.calm, 90);
});

test('simulated run is labeled and sense text changes animation', () => {
  const born = birth('serene');
  const quiet = simulateLive(born.traits, []);
  const bright = simulateLive(born.traits, [{schema:'companion-vision-event-v1', text:'a bright fast bounce', model:'llava'}]);
  const book = simulateLive(born.traits, [{schema:'companion-vision-event-v1', text:'an open book on the desk', model:'moondream'}]);
  const loud = simulateLive(born.traits, [{schema:'companion-hearing-event-v1', transcript:'', loudness:0.9, onset:true, engine:'loudness-only'}]);
  assert.equal(quiet.label, 'SIMULATED');
  assert.equal(quiet.quantum_hardware, 'not_contacted');
  assert.equal(quiet.pipeline, 'packets_to_dyn12+mirror_step+StateFamily');
  assert.equal(quiet.regge, 'not_in_repo');
  assert.equal(quiet.animation, 'rest');
  assert.equal(bright.animation, 'orbit');
  assert.equal(book.animation, 'perch');
  assert.equal(loud.animation, 'orbit');
  assert.notEqual(quiet.dyn12_0, bright.dyn12_0);
  assert.equal(bright.raw_frame_stored, undefined);
  assert.equal(acceptVision({schema:'companion-vision-event-v1', text:'desk lamp', model:'moondream'}).raw_frame_stored, false);
  assert.throws(() => acceptVision({schema:'companion-vision-event-v1', text:'desk', model:'moondream', image:'abcd'}), /raw media/);
  const fallback = acceptHearing({schema:'companion-hearing-event-v1', transcript:'hello', loudness:0.2, onset:false, engine:'web-speech-fallback'});
  assert.equal(fallback.fallback, true);
  assert.equal(fallback.raw_audio_stored, false);
});

test('memory grows, recalls, and exports a spark-loadable qbeast without raw media', () => {
  const born = birth('serene');
  const memory = new CompanionMemory();
  memory.add('keeper nickname is Pebble', 'note', 'chat');
  memory.add('a quiet lamp', 'vision', 'moondream');
  assert.equal(memory.records.length, 2);
  assert.match(memory.search('nickname')[0].text, /Pebble/);
  assert.throws(() => memory.add('api_key hunter2', 'note', 'chat'), /private/);
  const text = memory.exportQbeast(born.genome);
  const loaded = loadQbeast(text);
  assert.equal(loaded.snapshot.events.length, 3);
  assert.match(loaded.snapshot.events[1].payload.summary, /Pebble/);
  assert.equal(loaded.snapshot.public_state.mode, 'unavailable');
  const answer = reply(born.card, 'Are you conscious?');
  assert.match(answer, /not a conscious/);
  assert.match(answer, /does not know everything/);
  assert.doesNotMatch(answer, /I am conscious/);
  assert.equal(loopbackOnly('http://127.0.0.1:11434/api/chat'), true);
  assert.equal(loopbackOnly('https://example.com/api/chat'), false);
});

test('Brain Bay card is additive and deployment follows the intentional main contract', () => {
  const bay = read('../components/companion-local-bay.tsx');
  const studio = read('../components/studio.tsx');
  const vercel = read('../vercel.json');
  assert.match(bay, /useState\(false\)/);
  assert.match(bay, /Frame discarded/);
  assert.match(bay, /web-speech-fallback/);
  assert.match(bay, /Web Speech fallback: the browser vendor may process audio/);
  assert.match(bay, /SIMULATED/);
  assert.match(bay, /raw frames and audio are never stored/i);
  assert.doesNotMatch(bay, /\/api\/bridge\/models/);
  assert.match(studio, /<ModelSwitcher backendReachable=\{bridge\}/);
  assert.match(studio, /<CompanionLocalBay variant="bay"\/>/);
  assert.match(studio, /<CompanionLocalBay variant="chat"\/>/);
  assert.match(studio, /<LiveSenses visible=\{page==='SETTINGS'\}/);
  const deployments = JSON.parse(vercel).git.deploymentEnabled;
  assert.equal(deployments.main, true);
  assert.equal(deployments['feature/cosmic-chaos-vercel-app-001'], false);
  assert.doesNotMatch(read('../components/cosmos-world.tsx'), /CompanionLocalBay/);
  assert.doesNotMatch(read('../components/model-switcher.tsx'), /CompanionLocalBay/);
});
