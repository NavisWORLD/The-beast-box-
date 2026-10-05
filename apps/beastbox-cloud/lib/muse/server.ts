import { createHash } from 'node:crypto';
import { storageStatus, storeFromEnv } from './store.mjs';
import { rateLimit } from './rate-limit.mjs';

export const NO_STORE = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };

export function museStore() { return storeFromEnv(process.env); }
export function museStorage() { return storageStatus(process.env); }

/** Public origin of this deployment (Vercel sets the forwarded host). */
export function originOf(request: Request) {
  const url = new URL(request.url);
  const host = request.headers.get('x-forwarded-host');
  const proto = request.headers.get('x-forwarded-proto');
  if (host && /^[A-Za-z0-9.-]+(:\d+)?$/.test(host)) return `${proto === 'http' ? 'http' : 'https'}://${host}`;
  return url.origin;
}
export const mcpUrl = (origin: string) => origin + '/api/mcp';

export function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return Response.json(body, { status, headers: { ...NO_STORE, ...headers } });
}
export function noStorage() {
  const status = museStorage();
  return json(503, {
    error: 'storage_not_configured',
    error_description: 'The Meta Muse connector needs server storage on this deployment. Add a Redis REST store (Vercel Marketplace: Upstash for Redis).',
    missing_env: status.missing,
  });
}

/** Hash of the caller's address, used only as a rate-limit bucket. */
export function clientBucket(request: Request) {
  const ip = request.headers.get('x-vercel-forwarded-for') || request.headers.get('x-forwarded-for') || 'local';
  return createHash('sha256').update('bbm-ip:' + ip.split(',')[0].trim().slice(0, 64)).digest('hex').slice(0, 24);
}
export async function limited(store: any, bucket: string, id: string) {
  const rl = await rateLimit(store, bucket, id);
  if (rl.ok) return null;
  return json(429, { error: 'rate_limited', error_description: `Too many requests. Try again in ${rl.retryAfter} seconds.` }, { 'Retry-After': String(rl.retryAfter) });
}

/** Device routes are called only by the Beast Box page itself. */
export function sameOrigin(request: Request) {
  const origin = request.headers.get('origin');
  return !!origin && (origin === new URL(request.url).origin || origin === originOf(request));
}
export function deviceSecretOf(request: Request) {
  const m = /^Bearer (bbm_dev_[A-Za-z0-9_-]{20,100})$/.exec(request.headers.get('authorization') || '');
  return m ? m[1] : '';
}
export async function readJson(request: Request, max = 16000): Promise<any> {
  const raw = await request.text();
  if (raw.length > max) throw new Error('too large');
  return raw ? JSON.parse(raw) : {};
}
