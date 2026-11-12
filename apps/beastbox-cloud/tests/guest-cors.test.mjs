import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GUEST_CORS_ORIGINS,guestCorsOrigin,guestCorsPreflight,withGuestCors} from '../lib/guest-cors.mjs';
const route=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');

test('guest CORS: exactly one allowlisted origin, the NavisWORLD GitHub Pages chat',()=>{
 assert.deepEqual([...GUEST_CORS_ORIGINS],['https://navisworld.github.io']);
 assert.ok(Object.isFrozen(GUEST_CORS_ORIGINS));
 assert.equal(guestCorsOrigin('https://navisworld.github.io'),'https://navisworld.github.io');
 for(const o of [null,undefined,'','*','null','http://navisworld.github.io','https://navisworld.github.io:444','https://NavisWORLD.github.io',
  'https://evil.github.io','https://navisworld.github.io.evil.com','https://x.navisworld.github.io','https://www.beastboxcosmos.xyz'])
  assert.equal(guestCorsOrigin(o),null,String(o));
});

test('guest CORS: preflight grants POST + Content-Type only, never credentials or a wildcard',()=>{
 const ok=guestCorsPreflight('https://navisworld.github.io');
 assert.equal(ok.status,204);
 assert.equal(ok.headers.get('access-control-allow-origin'),'https://navisworld.github.io');
 assert.equal(ok.headers.get('access-control-allow-methods'),'POST');
 assert.equal(ok.headers.get('access-control-allow-headers'),'Content-Type');
 assert.equal(ok.headers.get('access-control-allow-credentials'),null);
 const bad=guestCorsPreflight('https://evil.example');
 assert.equal(bad.status,403);
 assert.equal(bad.headers.get('access-control-allow-origin'),null);
});

test('guest CORS: responses gain the read grant only for the allowlisted origin',()=>{
 const a=withGuestCors(Response.json({reply:'x'}),'https://navisworld.github.io');
 assert.equal(a.headers.get('access-control-allow-origin'),'https://navisworld.github.io');
 assert.match(a.headers.get('vary'),/Origin/);
 const b=withGuestCors(Response.json({reply:'x'}),'https://evil.example');
 assert.equal(b.headers.get('access-control-allow-origin'),null);
});

test('forever door: same-origin rule kept for everyone else; guest records stay training-excluded',()=>{
 assert.match(route,/Same-origin guest request required/);
 assert.match(route,/!allowedCrossOrigin&&request\.headers\.get\('origin'\)!==new URL\(request\.url\)\.origin/);
 assert.match(route,/export async function OPTIONS/);
 assert.match(route,/withGuestCors\(await foreverDoor\(request,cors!==null\),cors\)/);
 assert.match(route,/training_eligible:false/);
 assert.match(route,/if\(minted&&!allowedCrossOrigin\)headers\['Set-Cookie'\]/);
 assert.doesNotMatch(route,/Access-Control-Allow-Origin['"]?\s*[:,]\s*['"]\*/);
});
