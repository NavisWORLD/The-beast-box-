// Owner numeric ingress. Identity comes from the owner session, then the bridge.
// The flag off returns before any sample is forwarded. No model and no QPU.
import {bridgeConfigured, isOwner} from '@/lib/security';
import {validateBatch} from '@/lib/sensorium/sample.mjs';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function livedOn() {
  const value = process.env.BEASTBOX_LIVED_BACKBONE;
  return value == null || value.trim() === '' || value === 'on';
}
function reply(status: number, body: unknown) {
  return Response.json(body, {status, headers: {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}});
}
function sameOrigin(request: Request) {
  const origin = request.headers.get('origin');
  return !!origin && origin === new URL(request.url).origin;
}
function hasSearch(request: Request) {
  return new URL(request.url).search.length > 0;
}

async function forward(method: 'GET' | 'POST', body?: string) {
  const root = process.env.BEASTBOX_CLOUD_BRIDGE_URL!;
  const url = new URL('/api/sensorium', root.endsWith('/') ? root : root + '/');
  try {
    const upstream = await fetch(url, {
      method,
      body,
      cache: 'no-store',
      redirect: 'error',
      headers: {
        Authorization: 'Bearer ' + process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,
        ...(method === 'POST' ? {'Content-Type': 'application/json'} : {}),
      },
      signal: AbortSignal.timeout(15_000),
    });
    const raw = await upstream.text();
    if (raw.length > 64_000) return reply(502, {enabled: true, admitted: false, error: 'response'});
    let data: unknown;
    try { data = JSON.parse(raw); } catch { return reply(502, {enabled: true, admitted: false, error: 'response'}); }
    if (!data || typeof data !== 'object' || Array.isArray(data)) return reply(502, {enabled: true, admitted: false, error: 'response'});
    const record = data as Record<string, unknown>;
    const snap = record.snapshot;
    if (snap && typeof snap === 'object' && !Array.isArray(snap)) {
      const view = snap as Record<string, unknown>;
      delete view.origin_commitment;
      delete view.state12;
      delete view.channels;
      delete view.face;
      delete view.feelings;
    }
    return reply(upstream.ok ? 200 : upstream.status >= 500 ? 502 : upstream.status, record);
  } catch {
    return reply(502, {enabled: true, admitted: false, error: 'bridge'});
  }
}

export async function GET(request: Request) {
  if (hasSearch(request)) return reply(400, {enabled: false, admitted: false, error: 'query'});
  if (!livedOn()) return reply(200, {enabled: false, admitted: false});
  if (!await isOwner()) return reply(401, {enabled: false, admitted: false, error: 'owner'});
  if (!bridgeConfigured()) return reply(503, {enabled: true, admitted: false, error: 'bridge'});
  return forward('GET');
}

export async function POST(request: Request) {
  if (hasSearch(request)) return reply(400, {enabled: false, admitted: false, error: 'query'});
  if (!livedOn()) return reply(200, {enabled: false, admitted: false});
  if (!await isOwner()) return reply(401, {enabled: false, admitted: false, error: 'owner'});
  if (!sameOrigin(request)) return reply(403, {enabled: true, admitted: false, error: 'origin'});
  if (!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) return reply(415, {enabled: true, admitted: false, error: 'json'});
  const text = await request.text();
  if (text.length > 64_000) return reply(413, {enabled: true, admitted: false, error: 'size'});
  let parsed: unknown;
  try { parsed = JSON.parse(text); } catch { return reply(400, {enabled: true, admitted: false, error: 'json'}); }
  const checked = validateBatch(parsed);
  if (!checked.ok || !checked.body) return reply(400, {enabled: true, admitted: false, error: checked.code || 'invalid'});
  if (!bridgeConfigured()) return reply(503, {enabled: true, admitted: false, error: 'bridge'});
  return forward('POST', JSON.stringify(checked.body));
}
