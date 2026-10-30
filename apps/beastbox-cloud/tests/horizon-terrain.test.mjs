// Port of Cosmo's horizonterrain/verify.py (25 checks) plus the wiring into the first-person ground.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {HORIZON_PACK as P} from '../lib/universe/horizon-terrain-data.mjs';
import {HORIZON_LABEL,horizonLayerIds,farLayersFor,aerialFade,recentreAnchor,layerPhase,vertexEstimate,vertexBudget} from '../lib/universe/horizon-terrain.mjs';
const rd=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');const T=['LOW','MED','HIGH','GOD'];
const L=Object.fromEntries(P.layers.map(l=>[l.id,l]));const R=P.layers.filter(l=>l.id!=='patch');
test('pack wording: no Math.random, no real-physics claim, no live quantum, no AI wording, SEEDED, four tiers',()=>{
 const txt=JSON.stringify(P).toLowerCase();assert.ok(!txt.replace(/no math\.random/g,'').includes('math.random'));
 assert.ok(!txt.replace(/not real physics/g,'').includes('real physics'));assert.ok(!txt.includes('live quantum'));assert.doesNotMatch(txt,/\bai\b/);
 assert.match(P.label,/^SEEDED/);assert.deepEqual(Object.keys(P.tiers).sort(),[...T].sort());
 for(const f of ['lib/universe/horizon-terrain.mjs','lib/universe/horizon-terrain-data.mjs','lib/universe/one-world-look.ts'])assert.doesNotMatch(rd(f).replace(/(no|never) Math\.random/gi,''),/Math\.random/);
 assert.match(HORIZON_LABEL,/SEEDED/);assert.doesNotMatch(HORIZON_LABEL,/\bAI\b|real physics/i);});
test('flat FP patch >= 2.5 km, eye 1.6 m',()=>{assert.ok(L.patch.radius_m>=2500);assert.equal(L.patch.eye_height_m,1.6);});
test('R1-R4 match FIX_NOTES',()=>{const exp={R1:[300,12,'#6A7864'],R2:[1200,45,'#819393'],R3:[2000,80,'#8FA1A7'],R4:[4500,180,'#A7B6C1']};
 for(const [k,[d,h,c]] of Object.entries(exp)){assert.equal(L[k].distance_m,d);assert.equal(L[k].crest_m,h);assert.equal(L[k].colour.hex,c);}});
test('distance and fade increase outward; crests low; fade = 1-exp(-k d); bluer/lighter with distance',()=>{
 for(let i=1;i<R.length;i++){assert.ok(R[i-1].distance_m<R[i].distance_m&&R[i-1].fade<R[i].fade);assert.ok(R[i].colour.linear[2]>=R[i-1].colour.linear[2]-1e-9);}
 for(const l of R){assert.ok(l.crest_elev_deg>0&&l.crest_elev_deg<3);assert.ok(Math.abs(l.fade-aerialFade(l.distance_m))<1e-3);}});
test('parallax: world-fixed, recentre at 5% of distance',()=>{for(const l of R){assert.ok(l.parallax.world_fixed);assert.ok(Math.abs(l.parallax.recentre_after_move_m-.05*l.distance_m)<1e-3);}
 const a=[0,0,0];assert.equal(recentreAnchor(a,[14.9,0,0],300),a);assert.deepEqual(recentreAnchor(a,[15.1,0,0],300),[15.1,0,0]);assert.equal(recentreAnchor(a,[400,0,0],9000),a);});
test('tiers: vertex estimate within budget, MED reaches the 1-2 km ring, monotone',()=>{
 for(const t of T){assert.ok(vertexEstimate(t)<=vertexBudget(t));assert.equal(vertexEstimate(t),P.tiers[t].vertex_estimate);}
 assert.deepEqual(horizonLayerIds('LOW').slice(0,3),['patch','R1','R2']);assert.ok(horizonLayerIds('MED').includes('R3'));
 for(let i=1;i<T.length;i++){const A=P.tiers[T[i-1]],B=P.tiers[T[i]];for(const k of ['layers','patch_grid','ridge_segments','ridge_rows','vertex_budget'])assert.ok(B[k]>=A[k],T[i]+' '+k);}
 assert.deepEqual(farLayersFor('MED').map(l=>l.id),[]);assert.deepEqual(farLayersFor('HIGH').map(l=>l.id),['F5']);assert.deepEqual(farLayersFor('GOD').map(l=>l.id),['F5','F6']);});
test('layer phases are fixed per seed tag (same every load)',()=>{assert.deepEqual(layerPhase('x|F5'),layerPhase('x|F5'));assert.notDeepEqual(layerPhase('x|F5'),layerPhase('x|F6'));});
test('wired into the first-person ground in the lib, one sun only, no new light',()=>{const s=rd('lib/universe/one-world-look.ts');
 assert.match(s,/farLayersFor\(tier\)/);assert.match(s,/recentreAnchor\(/);assert.match(s,/__lwHorizon/);
 const add=s.slice(s.indexOf('export function addFlatGround'),s.indexOf('export function yawToward'));assert.doesNotMatch(add,/new THREE\.(Point|Directional|Spot|Hemisphere|Ambient)Light/);});
