import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {mirrorLivedExchange} from '../lib/cosmos/forever-store.mjs';
import {ZEREF_DIR} from '../lib/cosmos/zeref-cloud.mjs';
import {ownerChainWrite} from '../lib/zeref/lived-exchange.mjs';

const read = (path) => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const REPLICA = `${ZEREF_DIR}/lived-replica/exchanges.jsonl`;

function fakeBlobFetch() {
  const blobs = new Map();
  let n = 0;
  return {blobs, fetch: async (url, {method, headers, body}) => {
    const u = new URL(url);
    const name = decodeURIComponent(u.pathname.split('/').slice(2).join('/'));
    const H = Object.fromEntries(Object.entries(headers).map(([key, value]) => [key.toLowerCase(), value]));
    if (method === 'PUT' && u.searchParams.get('restype') === 'container') return new Response('', {status: 201});
    const cur = blobs.get(name);
    if (method === 'GET') return cur ? new Response(cur.text, {headers: {etag: cur.etag}}) : new Response('', {status: 404});
    if (H['if-none-match'] === '*' && cur) return new Response('<Code>BlobAlreadyExists</Code>', {status: 409});
    if (H['if-match'] && (!cur || cur.etag !== H['if-match'])) return new Response('<Code>ConditionNotMet</Code>', {status: 412});
    const etag = '"e' + (++n) + '"';
    blobs.set(name, {text: String(body ?? ''), etag});
    return new Response('', {status: 201, headers: {etag}});
  }};
}

const receipt = {
  schema: 'lived-exchange-receipt-v1', status: 'lived', scope: 'owner', role: 'spoken',
  label: 'RECORDED', exchange_id: 'ab'.repeat(16), event_id: 'cd'.repeat(32),
  text_sha256: 'ef'.repeat(32), state_sha256: '12'.repeat(32),
  counts: {chars: 4, utf8_bytes: 4},
};

test('guest and visitor doors do not write the owner chain', () => {
  assert.deepEqual(ownerChainWrite('guest'), {wrote: false, reason: 'isolated', chain: null});
  assert.deepEqual(ownerChainWrite('visitor'), {wrote: false, reason: 'isolated', chain: null});
  assert.equal(ownerChainWrite('owner').wrote, false);
  const guest = read('app/api/guest/route.ts');
  const forever = read('app/api/guest/forever/route.ts');
  const growing = read('app/api/guest-growing/route.ts');
  assert.match(guest, /ownerChainWrite\('guest'\)/);
  assert.match(forever, /ownerChainWrite\('visitor'\)/);
  assert.match(growing, /ownerChainWrite\('guest'\)/);
  assert.doesNotMatch(guest, /lived-backbone|bb-deada969\.sqlite/);
  assert.doesNotMatch(forever, /lived-backbone|bb-deada969\.sqlite/);
  assert.doesNotMatch(growing, /lived-backbone|bb-deada969\.sqlite/);
  const call = guest.indexOf("ownerChainWrite('guest')");
  const guard = guest.indexOf("guest exchange stays off the owner chain");
  const handler = guest.indexOf("Local guest inference unavailable or timed out");
  assert.ok(call >= 0 && guard > call && handler > guard);
  assert.match(guest.slice(call, guard), /try\{/);
});

test('azure mirror is a hash replica and a failed mirror does not claim the chain', async () => {
  const {blobs, fetch} = fakeBlobFetch();
  const real = globalThis.fetch;
  globalThis.fetch = fetch;
  try {
    const cfg = storageConfig({AZURE_STORAGE_CONTAINER_SAS_URL: 'https://acct.blob.core.windows.net/beast-cosmos?sv=x&sig=y'});
    const mirrored = await mirrorLivedExchange(cfg, {...receipt, text: 'must not be copied'});
    assert.equal(mirrored.mirrored, false);
    assert.equal(mirrored.canonical, false);
    assert.equal(blobs.has(REPLICA), false);
    const ok = await mirrorLivedExchange(cfg, receipt);
    assert.equal(ok.mirrored, true);
    assert.equal(ok.canonical, false);
    assert.equal(ok.status, 'replica');
    const line = blobs.get(REPLICA).text;
    assert.match(line, /lived-exchange-replica-v1/);
    assert.doesNotMatch(line, /must not be copied|hello from the shell/);
    assert.equal(line.includes('diary.jsonl'), false);
    const again = await mirrorLivedExchange(cfg, receipt);
    assert.equal(blobs.get(REPLICA).text, line);
    const isolated = await mirrorLivedExchange(cfg, {...receipt, scope: 'guest'});
    assert.equal(isolated.mirrored, false);
    assert.equal(blobs.get(REPLICA).text, line);
    globalThis.fetch = async () => { throw new Error('replica down'); };
    const missed = await mirrorLivedExchange(cfg, {...receipt, exchange_id: 'cd'.repeat(16), role: 'heard'});
    assert.equal(missed.status, 'unconfirmed');
    assert.equal(missed.canonical, false);
    assert.equal(blobs.get(REPLICA).text, line);
  } finally {
    globalThis.fetch = real;
  }
});
