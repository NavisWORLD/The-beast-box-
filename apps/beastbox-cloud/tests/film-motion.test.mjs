import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {motionPersona,createActor,stepActor,countsEntropy} from '../lib/companion/film-motion.mjs';
const src=readFileSync(new URL('../lib/companion/film-motion.mjs',import.meta.url),'utf8');
test('persona is deterministic from the creature\'s own id/seed; counts only when given',()=>{
 assert.deepEqual(motionPersona({id:'art-nyxbean'}),motionPersona({id:'art-nyxbean'}));
 assert.notDeepEqual(motionPersona({id:'art-nyxbean'}),motionPersona({id:'art-frostmitt'}));
 assert.equal(motionPersona({id:'x'}).source,'id-only');assert.equal(motionPersona({id:'x',counts:{'00':5,'11':5}}).source,'seed+labelled-counts');
 assert.equal(countsEntropy(null),null);assert.equal(countsEntropy({'00':5,'11':5}),1);
 assert.ok(!/Math\.random/.test(src),'no unseeded randomness');assert.ok(!/fetch\(|localStorage|Date\.now/.test(src));});
test('over time an actor anticipates, hops (stretch up), lands (squash) and walks within its radius',()=>{
 const a=createActor(motionPersona({id:'art-frostmitt'}),{radius:1.5,seed:'t'});const seen=new Set();let minSy=9,maxSy=0,maxLift=0,maxR=0;
 for(let i=0;i<60*120;i++){const p=stepActor(a,1/60,{lookAt:{x:3,z:3}});seen.add(p.state);minSy=Math.min(minSy,p.sy);maxSy=Math.max(maxSy,p.sy);maxLift=Math.max(maxLift,p.lift);maxR=Math.max(maxR,Math.hypot(p.x,p.z));}
 for(const s of ['idle','walk','anticipate','hop','land'])assert.ok(seen.has(s),s);
 assert.ok(minSy<.9&&maxSy>1.05,'squash and stretch');assert.ok(maxLift>.3,'hops');assert.ok(maxR<=1.55,'stays on its patch');});
test('reduced motion: no hops, no squash',()=>{const a=createActor(motionPersona({id:'z'}));for(let i=0;i<600;i++){const p=stepActor(a,1/60,{reduced:true});assert.equal(p.lift,0);assert.equal(p.sy,1);}});
test('follow-through: tail/ear springs lag after a landing',()=>{const a=createActor(motionPersona({id:'art-kairo'}),{seed:'q'});let moved=false;for(let i=0;i<60*60;i++){const p=stepActor(a,1/60,{});if(Math.abs(p.tail)>.02||Math.abs(p.ear)>.02){moved=true;break;}}assert.ok(moved);});
