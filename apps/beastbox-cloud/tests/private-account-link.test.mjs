import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('Spark links to the real consent-based private account panel',()=>{
 assert.match(r('public/spark/index.html'),/href="\/settings#private-memory">Save across devices</);
 const panel=r('components/private-cosmos-panel.tsx');assert.match(panel,/id="private-memory"/);
 assert.match(r('app/api/cosmos/private/session/route.ts'),/consent!==true/);
});
