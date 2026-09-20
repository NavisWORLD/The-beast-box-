import { cookies } from 'next/headers';
import { cookieName, cookieOptions, isOwner, newSession, ownerConfigured, ownerSetupStatus, safeJson, verifyPassword } from '@/lib/security';
export const dynamic = 'force-dynamic';
export async function GET() {return safeJson(200, { owner: await isOwner(), ...ownerSetupStatus() });}
export async function POST(request: Request) {
  if (!ownerConfigured()) return safeJson(503, {error:'Owner login is not provisioned. Configure secrets in Vercel Preview.'});
  if (Number(request.headers.get('content-length') || 0) > 2048) return safeJson(413,{error:'Request too large'});
  let body: unknown;
  try {body=await request.json();} catch {return safeJson(400,{error:'Invalid login request'});}
  const password = body && typeof body === 'object' && 'password' in body ? (body as {password?:unknown}).password : undefined;
  if (typeof password !== 'string' || password.length > 512 || !verifyPassword(password)) return safeJson(401,{error:'Invalid credentials'});
  (await cookies()).set(cookieName(), newSession(), cookieOptions());
  return safeJson(200,{owner:true});
}
export async function DELETE() {
  (await cookies()).set(cookieName(), '', {...cookieOptions(), maxAge:0});
  return safeJson(200,{owner:false});
}
