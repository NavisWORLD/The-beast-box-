import test from 'node:test';
import assert from 'node:assert/strict';
import {samePrivateOrigin} from '../lib/cosmos/private-origin.mjs';
const req=(origin,host='127.0.0.1:3833',extra={})=>new Request('http://localhost:3833/api/cosmos/private/session',{headers:{...(origin?{origin}:{}),host,...extra}});
test('Next internal hostname normalization preserves the actual same-origin browser request',()=>{assert.equal(samePrivateOrigin(req('http://127.0.0.1:3833')),true);assert.equal(samePrivateOrigin(new Request('https://www.beastboxcosmos.xyz/api/cosmos/private/session',{headers:{origin:'https://www.beastboxcosmos.xyz',host:'www.beastboxcosmos.xyz'}})),true);});
test('foreign origins and spoofed forwarded headers cannot satisfy the private CSRF check',()=>{for(const origin of ['https://untrusted.invalid','http://localhost:3833','null','http://127.0.0.1:3833/path','https://127.0.0.1:3833',null])assert.equal(samePrivateOrigin(req(origin)),false);assert.equal(samePrivateOrigin(req('https://untrusted.invalid','127.0.0.1:3833',{'x-forwarded-host':'untrusted.invalid'})),false);assert.equal(samePrivateOrigin(req('http://127.0.0.1:3833','127.0.0.1:3833@evil.invalid')),false);});
