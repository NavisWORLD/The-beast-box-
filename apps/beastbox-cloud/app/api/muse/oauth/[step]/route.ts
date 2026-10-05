import { AuthError, checkAuthorizeRequest, consumePairingCode, createAuthCode, exchangeToken, registerClient, revokeToken, scopeForChoice, SCOPE_CARE } from '@/lib/muse/auth.mjs';
import { clientBucket, json, limited, mcpUrl, museStore, noStorage, originOf, readJson, sameOrigin } from '@/lib/muse/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' };
const AUTHORIZE_FIELDS = ['client_id', 'redirect_uri', 'response_type', 'code_challenge', 'code_challenge_method', 'state', 'scope', 'resource'];

async function params(request: Request): Promise<Record<string, string>> {
  const type = (request.headers.get('content-type') || '').toLowerCase();
  if (type.includes('application/json')) {
    const body = await readJson(request, 8000);
    return Object.fromEntries(Object.entries(body || {}).filter(([, v]) => typeof v === 'string')) as Record<string, string>;
  }
  const raw = await request.text();
  if (raw.length > 8000) throw new Error('too large');
  return Object.fromEntries(new URLSearchParams(raw));
}
const oauthError = (e: unknown, cors = true) => {
  const err = e instanceof AuthError ? e : new AuthError('invalid_request', 'The request could not be read.');
  return json((err as any).status || 400, { error: (err as any).code, error_description: err.message }, cors ? CORS : {});
};

export async function OPTIONS() { return new Response(null, { status: 204, headers: CORS }); }

export async function POST(request: Request, ctx: { params: Promise<{ step: string }> }) {
  const { step } = await ctx.params;
  const store = museStore();
  if (!store) return noStorage();
  const busy = await limited(store, 'oauth', clientBucket(request));
  if (busy) return busy;
  const origin = originOf(request);

  if (step === 'register') {
    try { return json(201, await registerClient(store, await readJson(request, 8000)), CORS); }
    catch (e) { return oauthError(e instanceof AuthError ? e : new AuthError('invalid_client_metadata', 'Send RFC 7591 client metadata as JSON.')); }
  }

  if (step === 'token') {
    try { return json(200, await exchangeToken(store, await params(request)), { ...CORS, Pragma: 'no-cache' }); }
    catch (e) { return oauthError(e); }
  }

  if (step === 'revoke') {
    // RFC 7009: always 200, even for unknown tokens. The token value is never logged.
    try { const p = await params(request); await revokeToken(store, p.token); } catch { /* still 200 */ }
    return json(200, {}, CORS);
  }

  if (step === 'authorize') {
    if (!sameOrigin(request)) return json(403, { error: 'access_denied', error_description: 'The consent form must be submitted from the Beast Box page.' });
    let p: Record<string, string>;
    try { p = await params(request); } catch { return json(400, { error: 'invalid_request' }); }
    let client;
    try { client = await checkAuthorizeRequest(store, p, mcpUrl(origin)); }
    catch (e) { return oauthError(e, false); }
    const back = new URL(p.redirect_uri);
    if (p.state) back.searchParams.set('state', p.state);
    back.searchParams.set('iss', origin);
    if (p.decision !== 'allow') {
      back.searchParams.set('error', 'access_denied');
      back.searchParams.set('error_description', 'The beast owner declined.');
      return Response.redirect(back, 303);
    }
    const account = await consumePairingCode(store, p.pairing_code);
    if (!account) {
      const retry = new URL('/connect/meta-muse', origin);
      for (const k of AUTHORIZE_FIELDS) if (p[k]) retry.searchParams.set(k, p[k]);
      retry.searchParams.set('pair_error', '1');
      return Response.redirect(retry, 303);
    }
    // The owner's choice wins, but a client that asked only for beast.read never gets care.
    const asked = String(p.scope || '');
    const choice = p.access === 'care' && (!asked || asked.split(/\s+/).includes(SCOPE_CARE)) ? 'care' : 'read';
    const code = await createAuthCode(store, { client, redirectUri: p.redirect_uri, codeChallenge: p.code_challenge, scope: scopeForChoice(choice), accountId: account.id, resource: mcpUrl(origin) });
    back.searchParams.set('code', code);
    return Response.redirect(back, 303);
  }
  return json(404, { error: 'not_found' });
}
