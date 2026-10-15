import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('Open Field is linked from home, Cage nav + friendly explore line, game nav and Spark footer',()=>{
 for(const f of ['app/page.tsx','app/sol-game/page.tsx','public/spark/index.html'])assert.match(r(f),/href="\/beast-cage\/field"/,f);
 const cage=r('components/beast-cage-portal.tsx');assert.equal((cage.match(/href="\/beast-cage\/field"/g)||[]).length,2);
 assert.doesNotMatch(cage.slice(cage.indexOf('className="cage-quiet"')-80,cage.indexOf('className="cage-quiet"')),/data-advanced-only/);
});
