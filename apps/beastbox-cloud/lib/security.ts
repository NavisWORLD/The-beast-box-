import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';
const COOKIE = 'beastbox-session';
const SESSION_AGE = 60 * 60 * 8;
export function ownerConfigured() { return !!(process.env.BEASTBOX_OWNER_PASSWORD && process.env.BEASTBOX_CLOUD_AUTH_SECRET && process.env.BEASTBOX_CLOUD_AUTH_SECRET.length >= 32); }
export function bridgeConfigured() { return !!(process.env.BEASTBOX_CLOUD_BRIDGE_URL && process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN && validBackendUrl(process.env.BEASTBOX_CLOUD_BRIDGE_URL)); }
export function validBackendUrl(value: string | undefined): boolean {
  if (!value) return false;
  try {
    const u = new URL(value);
    return u.protocol === 'https:' && !u.username && !u.password && !u.hash && !u.search &&
      !['localhost', '127.0.0.1', '0.0.0.0', '::1'].includes(u.hostname) && !u.hostname.endsWith('.local');
  } catch { return false; }
}
function sign(payload: string) {
  return createHmac('sha256', process.env.BEASTBOX_CLOUD_AUTH_SECRET!).update(payload).digest('hex');
}
function eq(a: string, b: string) {
  const x=Buffer.from(a); const y=Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x,y);
}
export function verifyPassword(password: string): boolean {
  return ownerConfigured() && typeof password === 'string' && eq(password, process.env.BEASTBOX_OWNER_PASSWORD!);
}
export function newSession() {
  const payload = [String(Math.floor(Date.now()/1000) + SESSION_AGE), randomBytes(16).toString('hex')].join('.');
  return payload + '.' + sign(payload);
}
export function verifySession(token: string | undefined): boolean {
  if (!ownerConfigured() || !token || token.length > 256) return false;
  const [expiry, nonce, mac, extra] = token.split('.');
  if (extra || !expiry || !nonce || !mac || !/^\d{10}$/.test(expiry) || !/^[a-f0-9]{32}$/.test(nonce) || !/^[a-f0-9]{64}$/.test(mac)) return false;
  const validTime = Number(expiry) > Date.now()/1000 && Number(expiry) <= Date.now()/1000 + SESSION_AGE;
  return validTime && eq(mac, sign(expiry+'.'+nonce));
}
export async function isOwner() { return verifySession((await cookies()).get(COOKIE)?.value); }
export function cookieName() {return COOKIE;}
export function cookieOptions() { return { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict' as const, path: '/', maxAge: SESSION_AGE }; }
export function safeJson(status: number, body: unknown) { return Response.json(body, {status, headers: {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'} }); }
