import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('guide card and diary: no Moonwraith persona line, raw ids only behind data-advanced-only',()=>{
 const g=read('components/spark-beast-companion.tsx');
 assert.doesNotMatch(g,/Moonwraith · site guide/);
 assert.match(g,/IBM seed RECORDED on IBM hardware/);
 const h=read('components/homepage-creature.tsx');
 assert.doesNotMatch(h,/ZEREF · MOONWRAITH|Artistic 3D Moonwraith|HELLO FROM THE WORKSHOP/);
 const d=read('components/zeref-diary-panel.tsx');
 assert.doesNotMatch(d,/Diary keyed to the Moonwraith display persona/);
 assert.doesNotMatch(d,/recorded IBM quantum run/);
 assert.match(d,/<span data-advanced-only>Diary key bb-7f9c2a03/);
 assert.match(read('components/zeref-knowledge-diagnostics.tsx'),/<span data-advanced-only>\{beastId\}, <\/span>/);
});
test('old names are gone',()=>{
 for(const [p,re] of [['app/research/page.tsx',/COSMOS LAB/],['app/research/stage015/page.tsx',/COSMOS LAB/],['app/beast-cage/field/page.tsx',/Field game/],['app/beast-cage/talk/page.tsx',/OWNER WORKSTATION/],['components/beast-cage-talk.tsx',/Lost COSMOS field/],['components/lost-cosmos-dock.tsx',/'Spark Beast'/]])assert.doesNotMatch(read(p),re,p);
});
test('overclaim labels say RECORDED on IBM hardware / SIMULATED / SEEDED, never MEASURED for software',async()=>{
 const {GENESIS_LABEL}=await import('../lib/universe/tiny-universe-view.mjs');
 assert.equal(GENESIS_LABEL,'IBM seed RECORDED on IBM hardware (ibm_marrakesh)');
 const {SAND_LABEL}=await import('../lib/pocket-sand.mjs');
 assert.match(SAND_LABEL,/IBM seed RECORDED on IBM hardware.*Rigetti.*SIMULATED/);
 assert.doesNotMatch(read('components/beast-cage-portal.tsx'),/MEASURED SOFTWARE/);
});
test('Zeref guide card job id is the one in the repo receipts (shown whole, not a prefix)',async()=>{
 const {ZEREF_RECORDED_SOURCE}=await import('../lib/zeref/zeref-mind.mjs');
 assert.equal(ZEREF_RECORDED_SOURCE.job_id,'db4te7slf4us73c3888g');
 const rows=ZEREF_RECORDED_SOURCE.rows;assert.ok(rows.length>0&&rows.every(r=>r.j===ZEREF_RECORDED_SOURCE.job_id));
 assert.match(read('components/spark-beast-companion.tsx'),/ZEREF_RECORDED_SOURCE\.job_id\}/);
 assert.notEqual(ZEREF_RECORDED_SOURCE.job_id,'db4l2uclf4us73c2td10');
});
