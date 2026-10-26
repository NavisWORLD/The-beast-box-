// Visual Life Pass, B1: foam field. Determinism, isolation, birth at crest and shore, downwind advection, age cap, calm = zero, no clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {FOAM,createFoamField,stepFoam,syncFoam,foamAt,foamStats,foamBytes} from '../lib/universe/foam-field.mjs';
import {seaFrom,SEA} from '../lib/universe/sea-state.mjs';
import {createWorldField,stepWorldField,cellN} from '../lib/universe/world-field.mjs';
// west half water, east half land: a shore runs down the middle
const split=n=>n[0]>0?{id:'deep_ocean',h:-.2}:{id:'grassland',h:.2};
const world=(seed='foam')=>createWorldField({seed,W:32,H:16,initial:split});
const rough={dir:0.4,wind:.9,storm:.8,amp:.05,chop:.85,whitecap:.9};
const calm={dir:0,wind:0,storm:0,amp:SEA.ampBase*.35,chop:.25,whitecap:0};
const run=(F,sea,n,f=createFoamField(F))=>{for(let i=0;i<n;i++){F.tick++;stepFoam(f,F,sea);}return f;};
const snap=f=>JSON.stringify({b:[...f.born],a:[...f.age],f:[...f.foam],d:f.drift,t:f.tick});
test('same seed + same ticks = the same foam, byte for byte, twice (stepped by the real world field)',()=>{
 const go=()=>{const F=world();const f=createFoamField(F);for(let i=0;i<300;i++){stepWorldField(F,.25);syncFoam(f,F);}return snap(f);};
 assert.equal(go(),go());
});
test('isolation: stepping the foam changes nothing in the world field',()=>{
 const A=world('iso'),B=world('iso');const f=createFoamField(B);
 for(let i=0;i<200;i++){stepWorldField(A,.25);stepWorldField(B,.25);syncFoam(f,B);}
 const dump=F=>JSON.stringify({t:F.tick,temp:[...F.temp],moist:[...F.moist],grow:[...F.grow],idx:[...F.idx],storm:F.storm,sun:F.sunDir,L:F.S.L,ch:F.S.ch});
 assert.equal(dump(A),dump(B));
});
test('foam is born at crests and at the shore, only in water',()=>{
 const F=world();const f=run(F,rough,24);const st=foamStats(f,F);assert.ok(st.peak>0.2,'something foamed');
 let shore=0,open=0;for(let j=0;j<F.H;j++)for(let i=0;i<F.W;i++){const k=j*F.W+i;if(F.height[k]>=0){assert.equal(f.foam[k],0,'no foam on land');continue;}
  const nearLand=F.height[j*F.W+(i+1)%F.W]>=0||F.height[j*F.W+(i+F.W-1)%F.W]>=0;if(f.foam[k]>0.05){if(nearLand)shore++;else open++;}}
 assert.ok(shore>0,'shore foam');assert.ok(open>0,'crest foam in open water');
});
test('foam advects downwind: a patch moves with the engine wind and keeps its direction',()=>{
 const F=world();const f=createFoamField(F);const k0=4*F.W+10;f.born[k0]=1;f.age[k0]=0;f.foam[k0]=1;
 const wind={dir:0,wind:1,storm:0,amp:.01,chop:.25,whitecap:0}; // no births: only carry
 const cx=()=>{let s=0,m=0;for(let i=0;i<F.W;i++){const v=f.foam[4*F.W+i];s+=v*i;m+=v;}return m?s/m:null;};
 const x0=cx();for(let i=0;i<8;i++){F.tick++;stepFoam(f,F,wind);}const x1=cx();
 assert.ok(x1>x0+1.5,`moved downwind (+x): ${x0} -> ${x1}`);
 const g=world();const h=createFoamField(g);const kk=4*g.W+20;h.born[kk]=1;h.age[kk]=0;h.foam[kk]=1;
 for(let i=0;i<8;i++){g.tick++;stepFoam(h,g,{...wind,dir:Math.PI});}
 let s=0,m=0;for(let i=0;i<g.W;i++){const v=h.foam[4*g.W+i];s+=v*i;m+=v;}assert.ok(s/m<20-1.5,'reversed wind carries it the other way');
 assert.ok(f.drift[0]>0&&f.drift[0]<.5&&h.drift[0]>.5,'drift integrates the wind (wraps in 0..1, opposite way for reversed wind)');
});
test('foam fades with age and is exactly zero at the age cap (no births)',()=>{
 const F=world();const f=createFoamField(F);const k=6*F.W+12;f.born[k]=1;f.age[k]=0;f.foam[k]=1;let last=2;
 for(let i=1;i<=FOAM.ageCapTicks;i++){F.tick++;stepFoam(f,F,{...calm,wind:0});const m=Math.max(...f.foam);assert.ok(m<=last+1e-9);last=m;}
 assert.equal(Math.max(...f.foam),0);assert.equal(Math.min(...f.age),FOAM.ageCapTicks);
});
test('calm tick: zero wind and zero storm give zero foam, even from a shore',()=>{
 const F=world();const real=seaFrom({mp:{wind:{x:0,z:0}},storm:0});assert.equal(real.whitecap,0);
 const f=run(F,real,120);assert.equal(foamStats(f,F).peak,0);for(const v of foamBytes(f))assert.equal(v,0);
});
test('storm and wind raise the foam; reads by direction agree with the cell grid',()=>{
 const F=world();const a=run(F,{...rough,storm:0,whitecap:.15},60),b=run(world(),rough,60);
 assert.ok(foamStats(b,F).cover>foamStats(a,F).cover);
 const n=cellN(F,3,8);assert.equal(foamAt(b,F,n),b.foam[8*F.W+3]);
});
test('sync steps exactly once per world tick and never past it',()=>{
 const F=world();const f=createFoamField(F);F.tick=3;assert.equal(syncFoam(f,F),3);assert.equal(f.tick,3);assert.equal(syncFoam(f,F),0);
});
test('no clock, no Math.random in foam-field',()=>{
 const src=readFileSync(new URL('../lib/universe/foam-field.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date|requestAnimationFrame/.test(src));
});
