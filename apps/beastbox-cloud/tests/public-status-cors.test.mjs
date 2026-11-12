import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PUBLIC_STATUS_CORS_ORIGINS,publicStatusCorsOrigin,publicStatusCorsPreflight,withPublicStatusCors} from '../lib/public-status-cors.mjs';
const route=readFileSync(new URL('../app/api/cosmos/liveness/route.ts',import.meta.url),'utf8');

test('public status CORS: exactly one allowlisted origin, the NavisWORLD GitHub Pages profile',()=>{
 assert.deepEqual([...PUBLIC_STATUS_CORS_ORIGINS],['https://navisworld.github.io']);
 assert.ok(Object.isFrozen(PUBLIC_STATUS_CORS_ORIGINS));
 assert.equal(publicStatusCorsOrigin('https://navisworld.github.io'),'https://navisworld.github.io');
 for(const o of [null,undefined,'','*','null','http://navisworld.github.io','https://navisworld.github.io:444','https://NavisWORLD.github.io',
  'https://evil.github.io','https://navisworld.github.io.evil.com','https://x.navisworld.github.io','https://www.beastboxcosmos.xyz'])
  assert.equal(publicStatusCorsOrigin(o),null,String(o));
});

test('public status CORS: preflight grants GET, HEAD, OPTIONS only, never credentials or a wildcard',()=>{
 const ok=publicStatusCorsPreflight('https://navisworld.github.io');
 assert.equal(ok.status,204);
 assert.equal(ok.headers.get('access-control-allow-origin'),'https://navisworld.github.io');
 assert.equal(ok.headers.get('access-control-allow-methods'),'GET, HEAD, OPTIONS');
 assert.equal(ok.headers.get('access-control-allow-credentials'),null);
 assert.equal(ok.headers.get('access-control-allow-headers'),null);
 const bad=publicStatusCorsPreflight('https://evil.example');
 assert.equal(bad.status,403);
 assert.equal(bad.headers.get('access-control-allow-origin'),null);
});

test('public status CORS: responses gain the read grant only for the allowlisted origin',()=>{
 const a=withPublicStatusCors(Response.json({ok:true}),'https://navisworld.github.io');
 assert.equal(a.headers.get('access-control-allow-origin'),'https://navisworld.github.io');
 assert.match(a.headers.get('vary'),/Origin/);
 const b=withPublicStatusCors(Response.json({ok:true}),'https://evil.example');
 assert.equal(b.headers.get('access-control-allow-origin'),null);
});

test('liveness route: OPTIONS + GET CORS, still read-only, no wildcard, no guest-door POST grant',()=>{
 assert.match(route,/export function OPTIONS/);
 assert.match(route,/publicStatusCorsPreflight/);
 assert.match(route,/withPublicStatusCors/);
 assert.match(route,/export async function GET\(request/);
 assert.doesNotMatch(route,/Access-Control-Allow-Origin['"]?\s*[:,]\s*['"]\*/);
 assert.doesNotMatch(route,/Allow-Credentials/);
 assert.doesNotMatch(route,/method:'POST'/);
 assert.doesNotMatch(route,/putBlob|appendGuestEvent/);
 assert.match(route,/no-store/);
});
