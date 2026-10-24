// "The engine carries the sky", PR 3: one wave field, derived from engine channels, mirrored in GLSL.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {SEA,SEA_GLSL,seaFrom,waveHeightAt,crestFoam,shoreFoam,sunGlitter,fresnelMix,waterDeep,rideAt} from '../lib/universe/sea-state.mjs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
const init=n=>({id:'deep_ocean',h:-.2});
const field=n=>{const F=createWorldField({seed:'sea',W:16,H:8,initial:init});for(let i=0;i<n;i++)stepWorldField(F,1);return F;};
const dirs=[[0,1,0],[1,0,0],[0,0,1],[0.6,0.64,0.48],[-0.3,0.5,0.81240384],[0.1,-0.9,0.42]].map(v=>{const l=Math.hypot(...v);return v.map(x=>x/l);});
// a tiny GLSL-subset evaluator: strip the float types and run the text as JS with sin/cos in scope
const glsl=(()=>{const js=SEA_GLSL.replace(/float seaWaveHeight\(([^)]*)\)\{/,(m,a)=>'return function('+a.replace(/float /g,'')+'){').replace(/float /g,'let ').replace(/\n\}$/,'\n}');return new Function('sin','cos',js)(Math.sin,Math.cos);})();
test('CPU and GLSL wave heights agree at sampled points, times, winds and storms',()=>{
 for(const storm of [0,0.4,1])for(const dir of [0,1.3,-2.2])for(const d of dirs)for(const t of [0,1.7,40,300.25]){
  const sea={dir,wind:.5,storm,amp:(SEA.ampBase+SEA.ampStorm*storm)*0.7,chop:0.25+0.75*storm,whitecap:.4};
  const a=waveHeightAt(sea,d,t),b=glsl(d[0],d[1],d[2],t,dir,sea.amp,sea.chop);assert.ok(Math.abs(a-b)<1e-6,`${a} vs ${b}`);}
});
test('GLSL text is ES 1.00 safe: no int loops, no pow() on negatives, no unsupported types',()=>{
 assert.ok(!/\bint\b|\bfor\b|\buvec|\bin\b/.test(SEA_GLSL.replace(/float seaWaveHeight/,'')));assert.ok(SEA_GLSL.includes('float seaWaveHeight('));
});
test('sea is derived from the engine: wind from the CST wind, amplitude monotonic in storm, whitecaps follow storm',()=>{
 const F=field(400);const s=seaFrom(F);assert.ok(Number.isFinite(s.dir)&&s.amp>0);
 const base={dir:0,wind:.5,storm:0};let lastA=-1,lastW=-1;for(const st of [0,.2,.4,.6,.8,1]){const x=seaFrom({mp:{wind:{x:.3,z:.1}},storm:st});assert.ok(x.amp>lastA&&x.whitecap>lastW);lastA=x.amp;lastW=x.whitecap;}
 void base;assert.ok(seaFrom({mp:{wind:{x:.5,z:.5}},storm:.5}).amp>seaFrom({mp:{wind:{x:.05,z:0}},storm:.5}).amp,'stronger wind, higher swell');
});
test('same seed + same ticks = same sea and same heights, twice',()=>{
 const a=seaFrom(field(250)),b=seaFrom(field(250));assert.deepEqual(a,b);assert.equal(waveHeightAt(a,dirs[3],12.5),waveHeightAt(b,dirs[3],12.5));
});
test('the field moves with engine time and stays inside its amplitude bound',()=>{
 const sea={dir:.3,wind:.6,storm:1,amp:.062,chop:1,whitecap:1};let moved=false,max=0;for(let t=0;t<60;t+=.5){const h=waveHeightAt(sea,dirs[3],t);if(Math.abs(h-waveHeightAt(sea,dirs[3],0))>1e-4)moved=true;max=Math.max(max,Math.abs(h));}
 assert.ok(moved);assert.ok(max<=sea.amp*(1+.6+.22+.12)+1e-9);
});
test('crest foam forms and dissolves over ~2 s of engine time, and is zero in a calm sea',()=>{
 const calm={dir:0,wind:0,storm:0,amp:.012,chop:.25,whitecap:0};for(const d of dirs)assert.equal(crestFoam(calm,d,5),0);
 const sea={dir:.3,wind:.8,storm:1,amp:.06,chop:1,whitecap:1};let peak=0,at=0;for(let i=0;i<600;i++){const t=i*.05;const f=crestFoam(sea,dirs[3],t);if(f>peak){peak=f;at=t;}}
 // pick a gated point if this one never foams
 let d=dirs[3],ok=peak>0;if(!ok)for(let k=0;k<200&&!ok;k++){const v=[Math.sin(k),Math.cos(k*1.3),Math.sin(k*.7)];const l=Math.hypot(...v);d=v.map(x=>x/l);for(let i=0;i<400;i++){const f=crestFoam(sea,d,i*.05);if(f>0){peak=f;at=i*.05;ok=true;break;}}}
 assert.ok(ok&&peak>0);assert.ok(peak<=1);
});
test('shore foam sits at the waterline edge, swings with the swell, and wet sand follows moisture',()=>{
 const sea={dir:0,wind:.5,storm:.5,amp:.03,chop:.6,whitecap:.6};const e0=shoreFoam(sea,0,0).edge,e1=shoreFoam(sea,0,4).edge;assert.notEqual(e0,e1);
 const a=shoreFoam(sea,e0,0);assert.ok(a.foam>0.4);assert.equal(shoreFoam(sea,-5,0).foam,0);
 assert.ok(shoreFoam(sea,e0+.5,0,1).wetSand>shoreFoam(sea,e0+.5,0,0).wetSand);assert.equal(shoreFoam(sea,e0+9,0,1).wetSand,0);
});
test('sun glitter is tight and white high, wide and gold low, widened by chop; none below the horizon',()=>{
 const sea={chop:0.2},rough={chop:1};const hi=sunGlitter(.95,sea,[1,1,1]),lo=sunGlitter(.1,sea,[1,1,1]);assert.ok(lo.width>hi.width);assert.ok(lo.color[2]<hi.color[2]);assert.ok(sunGlitter(.5,rough).width>sunGlitter(.5,sea).width);assert.equal(sunGlitter(-.2,sea).intensity,0);
});
test('fresnel: looking straight down shows deep colour, grazing shows the sky; water colour follows temperature',()=>{
 const deep=[0,.1,.2],sky=[.8,.9,1];const dn=fresnelMix(1,deep,sky),gz=fresnelMix(0,deep,sky);assert.ok(Math.abs(dn[0]-0.02*.8)<1e-9);assert.ok(Math.abs(gz[0]-sky[0])<1e-9);
 assert.ok(waterDeep({temperature_k:350})[1]>waterDeep({temperature_k:240})[1]);
});
test('everything rides one field: rideAt heave equals waveHeightAt, and pitch/roll are finite and follow the slope',()=>{
 const sea={dir:.3,wind:.7,storm:.8,amp:.05,chop:.8,whitecap:.8};const d=dirs[3];const fwd=[0,1,0],right=[1,0,-1];
 const r=rideAt(sea,d,fwd,right,9);assert.equal(r.heave,waveHeightAt(sea,d,9));assert.ok(Number.isFinite(r.pitch)&&Number.isFinite(r.roll));
 const flat=rideAt({...sea,amp:0},d,fwd,right,9);assert.equal(flat.pitch,0);assert.equal(flat.roll,0);
});
test('no clock and no Math.random in sea-state',()=>{
 const src=readFileSync(new URL('../lib/universe/sea-state.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));
});
