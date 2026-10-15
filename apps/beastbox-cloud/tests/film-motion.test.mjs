import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {motionPersona,createActor,stepActor,countsEntropy,triggerCue,contactShadow,blendPose,STATES} from '../lib/companion/film-motion.mjs';
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
 for(const s of ['idle','walk','anticipate','hop','land','curious','scared','zoomies'])assert.ok(seen.has(s),s);
 assert.ok(minSy<.9&&maxSy>1.05,'squash and stretch');assert.ok(maxLift>.3,'hops');assert.ok(maxR<=1.55,'stays on its patch');});
test('reduced motion: no hops, no squash',()=>{const a=createActor(motionPersona({id:'z'}));for(let i=0;i<600;i++){const p=stepActor(a,1/60,{reduced:true});assert.equal(p.lift,0);assert.equal(p.sy,1);}});
test('follow-through: tail/ear springs lag after a landing',()=>{const a=createActor(motionPersona({id:'art-kairo'}),{seed:'q'});let moved=false;for(let i=0;i<60*60;i++){const p=stepActor(a,1/60,{});if(Math.abs(p.tail)>.02||Math.abs(p.ear)>.02){moved=true;break;}}assert.ok(moved);});
test('film clips: curious lean, scared scoot, and happy zoomies blend smoothly with grounded contact shadows',()=>{
 for(const s of ['idle','walk','hop','curious','scared','zoomies'])assert.ok(STATES.includes(s),s);
 const a=createActor(motionPersona({id:'art-nyxbean'}),{radius:1.6,seed:'clips'});
 triggerCue(a,'curious lean',{x:0.8,z:0.8});
 let p=stepActor(a,1/60,{lookAt:{x:0.8,z:0.8}});
 for(let i=0;i<20;i++)p=stepActor(a,1/60,{lookAt:{x:0.8,z:0.8}});
 assert.equal(p.state,'curious');
 assert.ok(p.lean>0.08,'curious lean pitches forward');
 assert.ok(p.ear>0.05,'curious lean perks ears');
 triggerCue(a,'scared scoot',{x:0.5,z:0.5});
 for(let i=0;i<20;i++)p=stepActor(a,1/60,{});
 assert.equal(p.state,'scared');
 assert.ok(p.sy<0.95,'scared scoot crouches low');
 assert.ok(p.lean<-0.05,'scared scoot leans back');
 triggerCue(a,'happy zoomies');
 let maxZoomLift=0;
 for(let i=0;i<30;i++){p=stepActor(a,1/60,{});maxZoomLift=Math.max(maxZoomLift,p.lift);}
 assert.equal(p.state,'zoomies');
 assert.ok(maxZoomLift>0.1,'happy zoomies bounce off the ground');
 const shGround=contactShadow({lift:0,sy:0.85});
 const shAir=contactShadow({lift:0.45,sy:1.15});
 assert.ok(shGround.scale>shAir.scale&&shGround.opacity>shAir.opacity,'contact shadow shrinks and softens in the air');
 const blended=blendPose({x:0,z:0,lift:0,sx:1,sy:1,heading:0,head:0,lean:0,tail:0,ear:0,state:'idle'},{x:1,z:1,lift:0.4,sx:0.9,sy:1.2,heading:1,head:0.4,lean:0.2,tail:0.3,ear:0.2,state:'hop'},0.5);
 assert.ok(Math.abs(blended.lift-0.2)<1e-6&&Math.abs(blended.lean-0.1)<1e-6);
});
