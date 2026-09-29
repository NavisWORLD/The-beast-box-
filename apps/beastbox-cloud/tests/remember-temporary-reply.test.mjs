import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('remembering temporary replies requires explicit owner consent and trusted job ID',()=>{
 const route=read('app/api/bridge/[endpoint]/route.ts');
 const studio=read('components/studio.tsx');
 assert.ok(route.includes("'remember-reply'"));
 assert.match(route,/input\.consent!==true/);
 assert.match(route,/input\.job_id/);
 assert.match(route,/Same-origin owner action required/);
 assert.match(route,/if \(!await isOwner\(\)\)/);
 assert.match(studio,/rememberTemporaryReply/);
 assert.match(studio,/temporaryJobId/);
 assert.match(studio,/rememberConsent/);
 assert.match(studio,/It may quote private attachments or sensor text/);
 assert.match(studio,/remember-reply/);
});
