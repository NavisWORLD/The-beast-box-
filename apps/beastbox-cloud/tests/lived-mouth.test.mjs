import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {chooseOneVoice} from '../lib/zeref/one-voice.mjs';
import {talkToBeast, talkPersona} from '../lib/companion/beast-talk.mjs';
import {assembleBridgeContext, contextOmitsCanonicalState} from '../lib/cosmos/live-context.mjs';
import {
  environmentIsNotCanonical, mintExchangeId, mouthReceipt, ownerTalkReceipt, speakLived,
} from '../lib/zeref/lived-exchange.mjs';

const HASH = 'ab'.repeat(32);
const DESC = 'cd'.repeat(32);
const OTHER = 'ef'.repeat(32);
const read = (p) => readFileSync(new URL('../' + p, import.meta.url), 'utf8');

function isolated(desc = DESC) {
  return {
    status: 'unavailable', reason: 'isolated', sequence: null, state_sha256: null,
    descriptor_sha256: desc, conditioned: false, changes_model_tensors: false,
    counts_as_memory_used: false, omitted_current_text_bytes: 0, scope: 'guest',
  };
}

test('exchange ids are deterministic and shared by both drafts', () => {
  const text = 'hello from the shell';
  const id = mintExchangeId('guest', 'a'.repeat(64), text);
  assert.equal(id, mintExchangeId('guest', 'a'.repeat(64), text));
  assert.equal(id.length, 32);
  assert.notEqual(id, mintExchangeId('guest', 'b'.repeat(64), text));
  const spoken = speakLived({
    exchangeId: id, gated: isolated(), growing: isolated(), chosen: 'gated', growingFailed: false,
  });
  assert.equal(spoken.exchange_id, id);
  assert.equal(spoken.spoken_by, 'gated');
  assert.equal(spoken.status, 'unavailable');
  assert.equal(spoken.conditioned, false);
  assert.equal(spoken.changes_model_tensors, false);
  assert.equal(spoken.counts_as_memory_used, false);
  assert.equal(spoken.descriptor_sha256, DESC);
});

test('one-voice scoring is unchanged and the spoken receipt uses that choice', () => {
  const prompt = 'Keeper: ocean\nZeref:';
  const voice = chooseOneVoice(prompt,
    {reply: 'I am so happy! I am so happy! I am so happy!'},
    {reply: 'The ocean waves roll under my moon.'});
  assert.equal(voice.chosen, 'growing');
  const spoken = speakLived({
    exchangeId: mintExchangeId('guest', 'a'.repeat(64), prompt),
    gated: isolated(DESC), growing: isolated(DESC), chosen: voice.chosen,
  });
  assert.equal(spoken.spoken_by, 'growing');
  assert.equal(spoken.descriptor_sha256, DESC);
});

test('a failed growing draft keeps the gated receipt', () => {
  const id = mintExchangeId('guest', 'a'.repeat(64), 'hello');
  const kept = speakLived({
    exchangeId: id, gated: isolated(DESC), growing: isolated(OTHER), chosen: 'growing', growingFailed: true,
  });
  assert.equal(kept.descriptor_sha256, DESC);
  assert.equal(kept.reason, 'isolated');
  assert.equal(kept.spoken_by, 'gated');
  assert.notEqual(kept.status, 'delivered');
});

test('disagreeing drafts are not reported as a successful snapshot', () => {
  const id = mintExchangeId('guest', 'a'.repeat(64), 'hello');
  const spoken = speakLived({
    exchangeId: id, gated: isolated(DESC), growing: isolated(OTHER), chosen: 'growing', growingFailed: false,
  });
  assert.equal(spoken.status, 'unavailable');
  assert.equal(spoken.reason, 'diverged');
  assert.equal(spoken.conditioned, false);
  assert.equal(spoken.descriptor_sha256, null);
  assert.equal(spoken.changes_model_tensors, false);
});

test('owner talk sees the snapshot admitted with no chat, and guests do not', () => {
  const admitted = {sequence: 4, state_sha256: HASH};
  const payload = {result: {result: {response: 'noted', lived_state: {
    status: 'delivered', sequence: admitted.sequence, state_sha256: admitted.state_sha256,
    descriptor_sha256: DESC, conditioned: true, changes_model_tensors: false,
    counts_as_memory_used: false, omitted_current_text_bytes: 0, scope: 'owner',
  }}}};
  const owner = ownerTalkReceipt(payload, mintExchangeId('owner', 'owner', 'hello'));
  assert.equal(owner.sequence, 4);
  assert.equal(owner.state_sha256, HASH);
  assert.equal(owner.descriptor_sha256, DESC);
  assert.equal(owner.conditioned, true);
  assert.equal(owner.changes_model_tensors, false);
  assert.equal(owner.counts_as_memory_used, false);
  assert.equal(owner.scope, 'owner');
  for (const scope of ['guest', 'visitor']) {
    const hidden = mouthReceipt(payload.result.result.lived_state, {scope, exchangeId: mintExchangeId(scope, 'a'.repeat(64), 'hello')});
    assert.equal(hidden.status, 'unavailable');
    assert.equal(hidden.reason, 'isolated');
    assert.equal(hidden.sequence, null);
    assert.equal(hidden.state_sha256, null);
    assert.equal(JSON.stringify(hidden).includes(HASH), false);
    assert.equal(JSON.stringify(hidden).includes('0.137'), false);
  }
});

test('stale and omitted owner receipts stay honest', () => {
  const stale = mouthReceipt({
    status: 'unavailable', reason: 'stale', sequence: 4, state_sha256: HASH,
    descriptor_sha256: DESC, conditioned: false,
  }, {scope: 'owner', spokenBy: 'owner', exchangeId: mintExchangeId('owner', 'owner', 'hi')});
  assert.equal(stale.status, 'unavailable');
  assert.equal(stale.reason, 'stale');
  assert.equal(stale.conditioned, false);
  assert.equal(stale.sequence, 4);
  assert.equal(stale.state_sha256, HASH);
  assert.equal(JSON.stringify(stale).includes('brightness'), false);
  const omitted = mouthReceipt({
    status: 'omitted', reason: 'budget', sequence: 4, state_sha256: HASH,
    descriptor_sha256: DESC, conditioned: true, omitted_current_text_bytes: 12,
  }, {scope: 'owner', spokenBy: 'owner'});
  assert.equal(omitted.status, 'omitted');
  assert.equal(omitted.reason, 'budget');
  assert.equal(omitted.conditioned, false);
  assert.equal(omitted.descriptor_sha256, null);
  assert.equal(omitted.changes_model_tensors, false);
});

test('a missing lived field is a capability mismatch and not a second model call', () => {
  assert.equal(mouthReceipt(undefined, {scope: 'owner'}), null);
  assert.equal(mouthReceipt(null, {scope: 'guest'}).reason, 'capability');
  assert.equal(speakLived({gated: undefined, growing: undefined, growingFailed: false}), null);
  const guest = read('app/api/guest/route.ts');
  assert.equal((guest.match(/mintExchangeId\('guest',identity,text\)/g) || []).length, 1);
  assert.equal((guest.match(/await send\(/g) || []).length, 2);
  assert.doesNotMatch(guest, /healthz/);
  assert.match(guest, /growingFailed:growing===null/);
  const src = read('lib/zeref/lived-exchange.mjs');
  assert.doesNotMatch(src, /Math\.random\(|fetch\(|admit_sensor\(/);
});

test('unicode and 1800-character turns keep one exchange id', () => {
  const cjk = '你'.repeat(1800);
  const emoji = '😀'.repeat(1800);
  const a = mintExchangeId('visitor', 'id', cjk);
  assert.equal(a, mintExchangeId('visitor', 'id', cjk));
  assert.notEqual(a, mintExchangeId('visitor', 'id', emoji));
  const spoken = speakLived({exchangeId: a, gated: isolated(), growing: isolated(), chosen: 'gated'});
  assert.equal(spoken.exchange_id, a);
  assert.equal(spoken.counts_as_memory_used, false);
});

test('an environment summary cannot choose the canonical snapshot', () => {
  const environment = {state12: [0.137, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], brightness: 0.137, snapshot: {sequence: 9, state_sha256: HASH}};
  assert.deepEqual(environmentIsNotCanonical(environment), {ignored: true, snapshot: null});
  const rejected = mouthReceipt({
    status: 'delivered', sequence: 9, state_sha256: HASH, descriptor_sha256: DESC,
    conditioned: true, environment,
  }, {scope: 'owner', environment});
  assert.equal(rejected.status, 'unavailable');
  assert.equal(rejected.reason, 'rejected');
  assert.equal(rejected.sequence, null);
  assert.equal(JSON.stringify(rejected).includes('0.137'), false);
  assert.equal(JSON.stringify(rejected).includes(HASH), false);
  const context = assembleBridgeContext({continuity: 'You are yourself.', world: null, shelfHits: []}).context;
  assert.equal(contextOmitsCanonicalState(context), true);
  assert.equal(contextOmitsCanonicalState({...context, snapshot: environment.snapshot}), false);
});

test('public talk forwards a receipt and does not send state text', async () => {
  const bodies = [];
  const isolatedReceipt = {
    schema: 'lived-mouth-receipt-v1', status: 'unavailable', reason: 'isolated', sequence: null,
    state_sha256: null, descriptor_sha256: DESC, conditioned: false, changes_model_tensors: false,
    counts_as_memory_used: false, omitted_current_text_bytes: 0, scope: 'guest',
    exchange_id: mintExchangeId('guest', 'guest', 'Hi!'), spoken_by: 'gated',
  };
  const guest = await talkToBeast({
    text: 'Hi!', persona: talkPersona({}),
    fetchImpl: async (_url, init) => {
      bodies.push(JSON.parse(init.body));
      return new Response(JSON.stringify({
        provider: 'rawrphos-local', model: 'rawrphos-native', step: 36784, guest_stateless: true,
        reply: 'hello', lived_state: isolatedReceipt,
      }));
    },
  });
  assert.equal(guest.ok, true);
  assert.equal(guest.lived_state.status, 'unavailable');
  assert.equal(guest.lived_state.reason, 'isolated');
  assert.equal(guest.lived_state.counts_as_memory_used, false);
  assert.equal(guest.lived_state.state_sha256, null);
  assert.deepEqual(Object.keys(bodies[0]).sort(), ['provider', 'text']);
  const plain = await talkToBeast({
    text: 'Hi!', persona: talkPersona({}),
    fetchImpl: async () => new Response(JSON.stringify({
      provider: 'rawrphos-local', model: 'rawrphos-native', step: 36784, guest_stateless: true, reply: 'hello',
    })),
  });
  assert.equal(plain.ok, true);
  assert.equal(plain.lived_state, undefined);
});

test('owner talk surfaces the nested runtime receipt', async () => {
  const job = {state: 'done', result: {result: {response: 'noted', lived_state: {
    status: 'delivered', sequence: 4, state_sha256: HASH, descriptor_sha256: DESC,
    conditioned: true, changes_model_tensors: true, counts_as_memory_used: true,
  }}}};
  const result = await talkToBeast({
    route: 'connected-brain-bay', text: 'hello from the shell',
    fetchImpl: async (url) => {
      if (String(url).includes('/api/status'))
        return new Response(JSON.stringify({owner: true, backendReachable: true, providerKind: 'local'}));
      return new Response(JSON.stringify(job));
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.lived_state.sequence, 4);
  assert.equal(result.lived_state.state_sha256, HASH);
  assert.equal(result.lived_state.changes_model_tensors, false);
  assert.equal(result.lived_state.counts_as_memory_used, false);
  assert.equal(result.lived_state.conditioned, true);
});
