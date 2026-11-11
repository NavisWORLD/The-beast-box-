import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';
import {chooseOneVoice} from '../lib/zeref/one-voice.mjs';
import {talkToBeast, talkPersona} from '../lib/companion/beast-talk.mjs';
import {RAWRPHOS_PUBLIC_PIN} from '../lib/companion/brain.mjs';
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

test('exchange ids are deterministic and shared by both drafts', async () => {
  const text = 'hello from the shell';
  const id = await mintExchangeId('guest', 'a'.repeat(64), text);
  const expected = createHash('sha256').update(`lived-exchange-v1\nguest\n${'a'.repeat(64)}\n${text}`, 'utf8').digest('hex').slice(0, 32);
  assert.equal(id, expected);
  assert.equal(id, await mintExchangeId('guest', 'a'.repeat(64), text));
  assert.equal(id.length, 32);
  assert.notEqual(id, await mintExchangeId('guest', 'b'.repeat(64), text));
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

test('one-voice scoring is unchanged and the spoken receipt uses that choice', async () => {
  const prompt = 'Keeper: ocean\nZeref:';
  const voice = chooseOneVoice(prompt,
    {reply: 'I am so happy! I am so happy! I am so happy!'},
    {reply: 'The ocean waves roll under my moon.'});
  assert.equal(voice.chosen, 'growing');
  const spoken = speakLived({
    exchangeId: await mintExchangeId('guest', 'a'.repeat(64), prompt),
    gated: isolated(DESC), growing: isolated(DESC), chosen: voice.chosen,
  });
  assert.equal(spoken.spoken_by, 'growing');
  assert.equal(spoken.descriptor_sha256, DESC);
});

test('a failed growing draft keeps the gated receipt', async () => {
  const id = await mintExchangeId('guest', 'a'.repeat(64), 'hello');
  const kept = speakLived({
    exchangeId: id, gated: isolated(DESC), growing: isolated(OTHER), chosen: 'growing', growingFailed: true,
  });
  assert.equal(kept.descriptor_sha256, DESC);
  assert.equal(kept.reason, 'isolated');
  assert.equal(kept.spoken_by, 'gated');
  assert.notEqual(kept.status, 'delivered');
});

test('disagreeing drafts are not reported as a successful snapshot', async () => {
  const id = await mintExchangeId('guest', 'a'.repeat(64), 'hello');
  const spoken = speakLived({
    exchangeId: id, gated: isolated(DESC), growing: isolated(OTHER), chosen: 'growing', growingFailed: false,
  });
  assert.equal(spoken.status, 'unavailable');
  assert.equal(spoken.reason, 'diverged');
  assert.equal(spoken.conditioned, false);
  assert.equal(spoken.descriptor_sha256, null);
  assert.equal(spoken.changes_model_tensors, false);
});

test('owner talk sees the snapshot admitted with no chat, and guests do not', async () => {
  const admitted = {sequence: 4, state_sha256: HASH};
  const payload = {result: {result: {response: 'noted', lived_state: {
    status: 'delivered', sequence: admitted.sequence, state_sha256: admitted.state_sha256,
    descriptor_sha256: DESC, conditioned: true, changes_model_tensors: false,
    counts_as_memory_used: false, omitted_current_text_bytes: 0, scope: 'owner',
  }}}};
  const owner = ownerTalkReceipt(payload, await mintExchangeId('owner', 'owner', 'hello'));
  assert.equal(owner.sequence, 4);
  assert.equal(owner.state_sha256, HASH);
  assert.equal(owner.descriptor_sha256, DESC);
  assert.equal(owner.conditioned, true);
  assert.equal(owner.changes_model_tensors, false);
  assert.equal(owner.counts_as_memory_used, false);
  assert.equal(owner.scope, 'owner');
  for (const scope of ['guest', 'visitor']) {
    const hidden = mouthReceipt(payload.result.result.lived_state, {scope, exchangeId: await mintExchangeId(scope, 'a'.repeat(64), 'hello')});
    assert.equal(hidden.status, 'unavailable');
    assert.equal(hidden.reason, 'isolated');
    assert.equal(hidden.sequence, null);
    assert.equal(hidden.state_sha256, null);
    assert.equal(JSON.stringify(hidden).includes(HASH), false);
    assert.equal(JSON.stringify(hidden).includes('0.137'), false);
  }
});

test('stale and omitted owner receipts stay honest', async () => {
  const stale = mouthReceipt({
    status: 'unavailable', reason: 'stale', sequence: 4, state_sha256: HASH,
    descriptor_sha256: DESC, conditioned: false,
  }, {scope: 'owner', spokenBy: 'owner', exchangeId: await mintExchangeId('owner', 'owner', 'hi')});
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

test('unicode and 1800-character turns keep one exchange id', async () => {
  const cjk = '你'.repeat(1800);
  const emoji = '😀'.repeat(1800);
  const a = await mintExchangeId('visitor', 'id', cjk);
  assert.equal(a, await mintExchangeId('visitor', 'id', cjk));
  assert.notEqual(a, await mintExchangeId('visitor', 'id', emoji));
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
    exchange_id: await mintExchangeId('guest', 'guest', 'Hi!'), spoken_by: 'gated',
  };
  const guest = await talkToBeast({
    text: 'Hi!', persona: talkPersona({}),
    fetchImpl: async (_url, init) => {
      bodies.push(JSON.parse(init.body));
      return new Response(JSON.stringify({
        provider: 'rawrphos-local', model: 'rawrphos-native', step: RAWRPHOS_PUBLIC_PIN.step,
        checkpoint_sha256: RAWRPHOS_PUBLIC_PIN.checkpoint_sha256, guest_stateless: true,
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
      provider: 'rawrphos-local', model: 'rawrphos-native', step: RAWRPHOS_PUBLIC_PIN.step,
      checkpoint_sha256: RAWRPHOS_PUBLIC_PIN.checkpoint_sha256, guest_stateless: true, reply: 'hello',
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

function importSpecifiers(source) {
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');
  const specs = [];
  for (const match of code.matchAll(/(?:import|export)\s+(?:[\s\S]*?\sfrom\s+)?['"]([^'"]+)['"]/g)) specs.push(match[1]);
  for (const match of code.matchAll(/import\(\s*['"]([^'"]+)['"]\s*\)/g)) specs.push(match[1]);
  for (const match of code.matchAll(/require\(\s*['"]([^'"]+)['"]\s*\)/g)) specs.push(match[1]);
  return specs;
}

function resolveLocal(fromFile, spec) {
  if (!spec.startsWith('.')) return null;
  const base = resolve(dirname(fromFile), spec);
  const candidates = [base, `${base}.mjs`, `${base}.js`, `${base}.json`, resolve(base, 'index.mjs'), resolve(base, 'index.js')];
  return candidates.find((candidate) => existsSync(candidate)) || null;
}

function nodeImportsReachableFrom(entry) {
  const hits = [];
  const seen = new Set();
  const queue = [entry];
  while (queue.length) {
    const current = queue.pop();
    if (!current || seen.has(current)) continue;
    seen.add(current);
    const source = readFileSync(current, 'utf8');
    for (const spec of importSpecifiers(source)) {
      if (spec.startsWith('node:')) hits.push(`${current} -> ${spec}`);
      const next = resolveLocal(current, spec);
      if (next) queue.push(next);
    }
  }
  return hits;
}

test('beast-talk import graph does not reach a node: module', () => {
  const entry = fileURLToPath(new URL('../lib/companion/beast-talk.mjs', import.meta.url));
  assert.deepEqual(nodeImportsReachableFrom(entry), []);
});
