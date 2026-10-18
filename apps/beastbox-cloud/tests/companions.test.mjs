import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {COMPANION_THEMES,COMPANION_LIMITS,companionTheme,kneeIK,legStep,feed,saveGrowth,loadGrowth} from '../lib/companions/companion-math.mjs';
import {drawPixelCompanion,PIXEL_SPRITES} from '../lib/companions/pixel-companion.mjs';
test('every named creature has a distinct themed companion; generated beasts get stable procedural ones',()=>{
 for(const id of ['zeref','art-nyxbean','art-frostmitt','art-kairo','art-shardhowl','art-velvetcoil'])assert.ok(COMPANION_THEMES[id]);
 assert.equal(COMPANION_THEMES['zeref'].motif,'cat-moth');assert.equal(COMPANION_THEMES['art-frostmitt'].motif,'ice-spider');assert.equal(COMPANION_THEMES['art-shardhowl'].motif,'crystal-mite');assert.equal(COMPANION_THEMES['art-velvetcoil'].motif,'scaled-jelly');
 assert.deepEqual(companionTheme('bb-123'),companionTheme('bb-123'));assert.ok(PIXEL_SPRITES[companionTheme('bb-xyz').motif]);});
test('IK knee + planted steps (no float, no sink)',()=>{const k=kneeIK({x:0,y:0,z:0},{x:.1,y:0,z:0},.075);assert.ok(k.y>0&&k.reach);
 const lg={foot:{x:0,y:0,z:0},from:{x:0,y:0,z:0},to:{x:0,y:0,z:0},t:1};legStep(lg,{x:.01,y:.2,z:0},.016);assert.equal(lg.foot.y,.2);
 legStep(lg,{x:.5,y:.2,z:0},.016);assert.equal(lg.t,0);for(let i=0;i<20;i++)legStep(lg,{x:.5,y:.2,z:0},.016);assert.equal(lg.foot.x,.5);assert.equal(lg.foot.y,.2);});
test('feeding pulses, grows (capped) and shares energy; growth persists',()=>{const c={x:0,y:0,z:0,grow:1};const m=[{x:.05,y:0,z:0,alive:true,e:.5}];const e=feed(c,m);assert.ok(e>0&&c.pulse===1&&c.grow>1&&!m[0].alive);
 c.grow=9;feed(c,[{x:0,y:0,z:0,alive:true,e:0}]);assert.equal(c.grow,COMPANION_LIMITS.growMax);
 const st={v:'',getItem(){return this.v},setItem(k,v){this.v=v}};saveGrowth(st,{zeref:1.2,bad:'x'});assert.deepEqual(loadGrowth(st),{zeref:1.2});});
test('pixel companion draws outline pixels; cage + sprite wiring; iPhone caps',()=>{const calls=[];const ctx={save(){},restore(){},fillRect(...a){calls.push(a)},set fillStyle(v){},set shadowColor(v){},set shadowBlur(v){}};
 const r=drawPixelCompanion(ctx,'zeref',0);assert.equal(r.motif,'cat-moth');assert.ok(calls.length>10);
 const src=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');assert.match(src('components/pixel-beast.tsx'),/drawPixelCompanion/);assert.match(src('components/cage-pocket-dimension.tsx'),/createCompanions\(THREE,scene,\{low\}\)/);
 assert.ok(COMPANION_LIMITS.maxCompanions<=8&&COMPANION_LIMITS.motesLow<=20);});
