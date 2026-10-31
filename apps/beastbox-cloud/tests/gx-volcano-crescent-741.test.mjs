import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {VOLCANO_LIT_LOOK,termEdges,SKY_OCCLUDER,setOccluder,occludes,occluderCos,VOLCANO_FP,VOLCANO_DAY_LOOK} from '../lib/universe/fp-volcano-sky.mjs';
const owl=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
const lf=readFileSync(new URL('../lib/universe/landforms-three.ts',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#741 lit crescent is the #B5532E surface with cracks as darker lines',()=>{
 assert.equal(VOLCANO_LIT_LOOK.litHex,'#B5532E');assert.ok(VOLCANO_LIT_LOOK.litCrackDark>0&&VOLCANO_LIT_LOOK.litCrackDark<1);
 assert.match(owl,/litSurf=uLitBody\*\(1\.0-uLitCrackDark\*crack\)/);assert.match(owl,/mix\(side,litSurf,lit\)/);});
test('#741 terminator softness 0.05, same centre as before (crescent does not move)',()=>{
 const [a,b]=termEdges();assert.ok(Math.abs(b-a-.05)<1e-9);assert.ok(Math.abs((a+b)/2-(-.06+.25)/2)<1e-9);assert.match(owl,/smoothstep\(uTerm\.x,uTerm\.y,l\)/);});
test('#741 night colour untouched',()=>{assert.equal(VOLCANO_DAY_LOOK.nightBodyHex,'#1C100E');assert.match(owl,/c\+=cc\*crack\*2\.2\*uLavaK\*uCrackK\*\(1\.0-lit\)/);});
test('#741 stars behind the disc are hidden; nothing hidden when the disc is off',()=>{
 const d=[0,.5,.866];setOccluder(true,d,VOLCANO_FP.angularDeg);assert.ok(Math.abs(SKY_OCCLUDER.uOccCos.value-occluderCos(VOLCANO_FP.angularDeg))<1e-12);
 assert.ok(occludes(d,d,VOLCANO_FP.angularDeg));assert.ok(!occludes([1,0,0],d,VOLCANO_FP.angularDeg));
 setOccluder(false,d,0);assert.equal(SKY_OCCLUDER.uOccCos.value,2);
 assert.match(lf,/OCC_DECL\+'attribute vec3 aM/);assert.match(lf,/\+OCC_CULL\+/);assert.match(lw,/starMat\.onBeforeCompile/);assert.match(owl,/setOccluder\(on,dir/);});
test('#741 no Math.random added',()=>{for(const s of [readFileSync(new URL('../lib/universe/fp-volcano-sky.mjs',import.meta.url),'utf8')])assert.ok(!/Math\.random/.test(s));});
