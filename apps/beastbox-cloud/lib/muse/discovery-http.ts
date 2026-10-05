import { createHash } from 'node:crypto';
import { deviceById } from './auth.mjs';
import { aiCatalog, CATALOG_TYPE, DISCOVERY_HEADERS, SERVER_CARD_TYPE, serverCard } from './discovery.mjs';
import { clientBucket, json, limited, museStore, originOf } from './server';

function respond(request: Request, body: unknown, type: string, maxAge: number) {
  const text = JSON.stringify(body);
  const etag = '"' + createHash('sha256').update(text).digest('base64url').slice(0, 27) + '"';
  const headers = { ...DISCOVERY_HEADERS, 'Content-Type': type, 'Cache-Control': `public, max-age=${maxAge}`, ETag: etag };
  if (request.headers.get('if-none-match') === etag) return new Response(null, { status: 304, headers });
  return new Response(text, { status: 200, headers });
}

/** GET handler for the Server Card (optionally for one paired device). */
export async function serverCardResponse(request: Request) {
  const origin = originOf(request);
  const deviceId = new URL(request.url).searchParams.get('device') || '';
  let device = null;
  if (deviceId) {
    const store = museStore();
    if (store) {
      const busy = await limited(store, 'oauth', clientBucket(request));
      if (busy) return busy;
      device = await deviceById(store, deviceId);
    }
    if (!device) return json(404, { error: 'unknown_device', error_description: 'No paired Beast Box device has this id.' }, DISCOVERY_HEADERS);
  }
  return respond(request, serverCard(origin, device), SERVER_CARD_TYPE, device ? 60 : 3600);
}
export function catalogResponse(request: Request) {
  return respond(request, aiCatalog(originOf(request)), CATALOG_TYPE, 3600);
}
export function discoveryOptions() {
  return new Response(null, { status: 204, headers: DISCOVERY_HEADERS });
}
