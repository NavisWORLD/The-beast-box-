import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('shared Ollama teacher is server-side, labeled, capped and fed to distill',()=>{
 const r=read('app/api/teacher/ollama/route.ts');
 assert.match(r,/process\.env\.OLLAMA_API_KEY/);assert.match(r,/TEACHER_NOT_BEAST_VOICE/);
 assert.match(r,/PER_VISITOR_HOUR/);assert.match(r,/dailyCap/);assert.match(r,/screenText\(prompt\)/);assert.match(r,/SHARED_TEACHER_AUTO/);
 assert.doesNotMatch(r,/reply,.*key/);
 const talk=read('lib/companion/beast-talk.mjs');assert.match(talk,/"shared-ollama"/);assert.doesNotMatch(talk,/OLLAMA_API_KEY/);
 assert.doesNotMatch(read('components/beast-talk-panel.tsx'),/OLLAMA_API_KEY/);
 assert.match(read('components/beast-talk-panel.tsx'),/'shared-ollama':'Ollama'/);
});
test('workshop is gated to owner or allowlisted verified accounts',()=>{
 assert.match(read('app/workspace/page.tsx'),/WorkshopGate/);
 assert.match(read('components/workshop-gate.tsx'),/Message Cory for access/);
 const a=read('lib/accounts.ts');assert.match(a,/BEASTBOX_WORKSHOP_ALLOWLIST/);assert.match(a,/scryptSync/);assert.match(a,/verified\?/);
});
test('accounts send verification email only via configured provider',()=>{
 const a=read('lib/accounts.ts');assert.match(a,/RESEND_API_KEY&&process\.env\.BEASTBOX_EMAIL_FROM/);
 assert.match(read('app/api/account/route.ts'),/signup/);
});
