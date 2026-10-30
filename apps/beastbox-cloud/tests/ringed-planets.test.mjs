// Port of Cosmo's ringedplanets/verify.py (23 checks), the ringPlan fix, and the wiring.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {RINGED_PACK as P} from '../lib/universe/ringed-planets-data.mjs';
import {RINGED_LABEL,NEVER_RINGS,isRinglessWorld,ringPresetFor,ringLook,planetShadowOnRing,ringShadowOnPlanet,forwardScatter,withRingShadow,RING_FRAG} from '../lib/universe/ringed-planets.mjs';
import {ringPlan} from '../lib/universe/neighbour-planets.mjs';
const rd=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');const T=['LOW','MED','HIGH','GOD'];
test('pack wording: no Math.random, no real-physics claim, no live quantum, no AI wording, SEEDED, four tiers',()=>{const txt=JSON.stringify(P).toLowerCase();
 assert.ok(!txt.replace(/(no|never) math\.random/g,'').includes('math.random'));assert.ok(!txt.replace(/not real physics/g,'').includes('real physics'));assert.ok(!txt.includes('live quantum'));assert.doesNotMatch(txt,/\bai\b/);
 assert.match(P.label,/^SEEDED/);assert.deepEqual(Object.keys(P.tiers).sort(),[...T].sort());assert.match(RINGED_LABEL,/SEEDED/);
 for(const f of ['lib/universe/ringed-planets.mjs','lib/universe/neighbour-planets.mjs'])assert.doesNotMatch(rd(f),/Math\.random/);});
test('lighting: one sun only, earthshine cap <= 0.03, terminator softness, rim strengths, airless no rim',()=>{const L=P.lighting;assert.ok(L.source.includes('ONE engine sun only'));
 assert.ok(L.earthshine.cap_linear>0&&L.earthshine.cap_linear<=.03);for(const [k,v] of Object.entries(L.terminator_softness))if(k!=='rule')assert.ok(v>=.03&&v<=.12);
 for(const r of Object.values(P.atmosphere_rims))assert.ok(r.strength>=0&&r.strength<=.6);assert.equal(P.atmosphere_rims.airless.strength,0);});
test('no rings on the three worlds; sky volcano ringless and placed',()=>{assert.deepEqual([...NEVER_RINGS].sort(),['world-desert','world-home','world-volcano']);
 assert.equal(P.sky_volcano.ring,null);assert.ok(Math.abs(P.sky_volcano.azimuth_deg-191.785)<.01);});
test('ring presets: ranges and 64 bands',()=>{for(const p of P.rings.presets){assert.ok(1.3<=p.inner_ratio&&p.inner_ratio<p.outer_ratio&&p.outer_ratio<=2.7);assert.ok(p.opacity>=.4&&p.opacity<=.8);assert.equal(p.bands_1d.length,64);assert.ok(p.bands_1d.every(v=>v>=0&&v<=1));}
 assert.ok(P.rings.forward_scatter.g>=1&&P.rings.forward_scatter.g<=2);for(const k of ['ring_shadow_on_planet','planet_shadow_on_ring'])assert.match(P.rings[k].formula,/sunDir/);});
test('tiers monotone',()=>{for(let i=1;i<T.length;i++)for(const k of ['sphere_segments','rings','ring_bands','rim','ring_shadow_on_planet','planet_shadow_on_ring','forward_scatter','max_lit_planets'])assert.ok(P.tiers[T[i]][k]>=P.tiers[T[i-1]][k],T[i]+' '+k);});
test('ringPlan: home, desert and volcano never get a ring, even when biggest; the biggest other planet still does',()=>{
 for(const id of ['world-home','world-desert','world-volcano','home','desert','volcano']){const L=[{id,radius_earth:9},{id:'n1',radius_earth:1},{id:'n2',radius_earth:2}];const r=ringPlan(L);assert.equal(r[0],null,id);assert.ok(r[2],id+': next biggest gets the ring');assert.ok(isRinglessWorld(id));}
 const all=[{id:'world-home',radius_earth:5},{id:'world-desert',radius_earth:4},{id:'world-volcano',radius_earth:6}];assert.deepEqual(ringPlan(all),[null,null,null]);assert.ok(!isRinglessWorld('crystal_moss'));});
test('ring look per tier and deterministic preset pick',()=>{assert.equal(ringPresetFor('x'),ringPresetFor('x'));const g=ringLook('x','GOD'),l=ringLook('x','LOW');assert.equal(g.useBands,1);assert.equal(l.useBands,0);assert.ok(g.scatter>1);assert.equal(l.scatter,0);assert.equal(g.bands.length,64);});
test('analytic shadows and forward scatter (CPU mirrors)',()=>{const sun=[1,0,0];assert.equal(planetShadowOnRing([-3,0,0],[0,0,0],1,sun),0);assert.equal(planetShadowOnRing([-3,5,0],[0,0,0],1,sun),1);assert.equal(planetShadowOnRing([3,0,0],[0,0,0],1,sun),1);
 const s=ringShadowOnPlanet([-2,0,0],[0,0,0],[1,0,0],[Math.SQRT1_2,Math.SQRT1_2,0],1,1.5,2.5,.6);assert.ok(s<1);assert.equal(ringShadowOnPlanet([-1,0,0],[0,0,0],[1,0,0],[-1,0,0],1,1.5,2.5,.6),1);
 assert.ok(forwardScatter([-1,0,0],sun)>2);assert.equal(forwardScatter([1,0,0],sun),1);});
test('wired: rings use the pack shader and preset per tier; planet gets the ring shadow patch; no new light',()=>{const w=rd('components/living-world.tsx');assert.match(w,/ringLook\(pl\.id,tier0\)/);assert.match(w,/fragmentShader:RING_FRAG/);assert.match(w,/withRingShadow\(/);
 assert.match(withRingShadow('void main(){vec3 c=vec3(1);gl_FragColor=vec4(c,1.0);}'),/ringShade\(vW/);assert.doesNotMatch(RING_FRAG,/Light/);});
