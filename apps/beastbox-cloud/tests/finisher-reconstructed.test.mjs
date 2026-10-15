import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {explainCreature} from '../lib/companion/family-explain.mjs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const zeref=JSON.parse(r('public/spark/zeref-live-20261010/unsigned-session.json')).beast;
test('existing 8s behavior loop kept; hidden time still invents no experiences',()=>{assert.match(r('components/beast-session.tsx'),/Hidden time invents no experiences/);});
test('family explanation is honest: recorded seed, no invented jobs',()=>{
 const e=explainCreature(zeref,{mode:'friendly'});for(const k of ['seed','memory','behavior','growth','next'])assert.equal(typeof e.friendly[k],'string');
 assert.equal(e.advanced,null);const a=explainCreature(zeref,{mode:'advanced'}).advanced;assert.equal(a.hardwareClass,'recorded-ibm-hardware');
 assert.equal(explainCreature({},{mode:'advanced'}).advanced.jobId,null);});
test('only one grow button per saved creature; Spark eyebrow is plain words',()=>{
 assert.match(r('components/beast-cage-portal.tsx'),/showGrow=\{!sameSpark\}/);assert.match(r('components/zeref-diary-panel.tsx'),/showGrow\?<GrowInCosmos/);
 assert.doesNotMatch(r('public/spark/index.html'),/ACTIVE QBEAST/);assert.match(r('components/creature-dashboard.tsx'),/<FamilyExplain input=\{beast\}\/>/);});
test('turntable keeps the procedural guide as default subject',()=>{assert.match(r('app/beast-cage/turntable/page.tsx'),/useState<Subject>\('workshop'\)/);});
test('home defaults to the sprite-built 3D Zeref; flat sprite + classic guide removed from home only (code kept)',()=>{const h=r('components/homepage-creature.tsx');
 assert.match(h,/useState<View>\('zeref3d'\)/);assert.match(h,/<ZerefSprite3D/);assert.ok(!h.includes('>Classic 3D guide<'));assert.ok(h.includes('<CosmicCompanion3D')&&h.includes('<ZerefMoonwraith'));
 assert.match(r('app/beast-cage/turntable/page.tsx'),/useState<Subject>\('workshop'\)/);});
