import { createAccount, createPat, deviceAccount, newPairingCode, publicStatus, revokeById, setDeviceName, unpairAccount } from '@/lib/muse/auth.mjs';
import { PAIRING_METHODS, pairingLink, serverCardUrl } from '@/lib/muse/discovery.mjs';
import { validateSnapshot } from '@/lib/muse/snapshot.mjs';
import { syncAccount } from '@/lib/muse/tools.mjs';
import { clientBucket, deviceSecretOf, json, limited, mcpUrl, museStorage, museStore, noStorage, originOf, readJson, sameOrigin } from '@/lib/muse/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Ctx = { params: Promise<{ action: string }> };

function storagePayload(request: Request) {
  const s = museStorage();
  const origin = originOf(request);
  return { configured: s.configured, kind: s.kind, missing: s.missing, connectorUrl: mcpUrl(origin), serverCardUrl: serverCardUrl(origin), pairingMethods: PAIRING_METHODS };
}

async function device(request: Request) {
  const store = museStore();
  if (!store) return { error: noStorage() };
  if (!sameOrigin(request)) return { error: json(403, { error: 'same_origin_required' }) };
  const secret = deviceSecretOf(request);
  const account = secret ? await deviceAccount(store, secret) : null;
  if (!account) return { error: json(401, { error: 'not_paired', error_description: 'This browser is not paired with Meta Muse.' }) };
  return { store, secret, account };
}

export async function GET(request: Request, ctx: Ctx) {
  const { action } = await ctx.params;
  if (action === 'storage') return json(200, storagePayload(request));
  if (action !== 'link') return json(404, { error: 'not_found' });
  const d = await device(request);
  if (d.error) return d.error;
  return json(200, { ...publicStatus(d.account), serverCardUrl: serverCardUrl(originOf(request), d.account.deviceId), storage: storagePayload(request) });
}

export async function POST(request: Request, ctx: Ctx) {
  const { action } = await ctx.params;
  const store = museStore();
  if (!store) return noStorage();
  if (!sameOrigin(request)) return json(403, { error: 'same_origin_required' });
  let body: any = {};
  try { body = await readJson(request, 16000); } catch { return json(400, { error: 'invalid_json' }); }

  if (action === 'link') {
    const busy = await limited(store, 'link', clientBucket(request));
    if (busy) return busy;
    if (body.consent !== 'share-beast-snapshot') return json(400, { error: 'consent_required', error_description: 'Pairing shares a minimal beast snapshot. Send consent "share-beast-snapshot".' });
    const snapshot = body.snapshot ? validateSnapshot(body.snapshot) : null;
    const { account, deviceSecret } = await createAccount(store, { snapshot, deviceName: typeof body.deviceName === 'string' ? body.deviceName : '' });
    return json(201, { deviceSecret, ...publicStatus(account), serverCardUrl: serverCardUrl(originOf(request), account.deviceId), storage: storagePayload(request) });
  }

  const d = await device(request);
  if (d.error) return d.error;
  const { account } = d;

  if (action === 'code') {
    const busy = await limited(store, 'link', 'code:' + account.id);
    if (busy) return busy;
    const pair = await newPairingCode(store, account.id);
    // The link carries the code in its #fragment, which browsers never send to a server.
    return json(201, { ...pair, link: pairingLink(originOf(request), { code: pair.code, deviceId: account.deviceId }) });
  }
  if (action === 'sync') {
    const busy = await limited(store, 'sync', account.id);
    if (busy) return busy;
    const snapshot = body.snapshot ? validateSnapshot(body.snapshot) : null;
    if (body.snapshot && !snapshot) return json(400, { error: 'invalid_snapshot' });
    const out = await syncAccount(store, account.id, snapshot, body.ack);
    const fresh = await deviceAccount(store, d.secret!);
    return json(200, { ...out, status: fresh ? publicStatus(fresh) : null });
  }
  if (action === 'device') {
    try { return json(200, await setDeviceName(store, account.id, body.name)); }
    catch (e) { return json(400, { error: 'invalid_device_name', error_description: (e as Error).message }); }
  }
  if (action === 'pat') {
    const busy = await limited(store, 'link', 'pat:' + account.id);
    if (busy) return busy;
    const pat = await createPat(store, account.id, body.access === 'care' ? 'care' : 'read');
    return json(201, { ...pat, note: 'Shown once. Beast Box stores only a hash of this token.' });
  }
  return json(404, { error: 'not_found' });
}

export async function DELETE(request: Request, ctx: Ctx) {
  const { action } = await ctx.params;
  const d = await device(request);
  if (d.error) return d.error;
  if (action === 'link') return json(200, await unpairAccount(d.store!, d.account.id, d.secret));
  if (action === 'grant') {
    const id = new URL(request.url).searchParams.get('id') || '';
    if (!/^[a-f0-9]{12}$/.test(id)) return json(400, { error: 'invalid_id' });
    return json(200, await revokeById(d.store!, d.account.id, id));
  }
  return json(404, { error: 'not_found' });
}
