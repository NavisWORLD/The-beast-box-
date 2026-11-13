import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const g=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
test('#756 hills show: absolute seeded height, 6-unit spawn pad only, narrow bay cut, debug lookup + magenta flag, honest label',()=>{
 assert.ok(!/tRaw\(uTOrg\)/.test(g));
 assert.match(g,/uTBay\.y\*\.95,uTBay\.y\*1\.2/);assert.match(g,/terrdbg=1/);assert.match(g,/ground\.visible=false/);
 assert.match(g,/label:'Terrain shape · SEEDED',at:tAt/);assert.ok(!/Math\.random/.test(g));});
// Nov 12 2026: Cory asked for real first-person hills ('waaaay better'), so the #757 7-deg cap is replaced: near rolling hills from ~5 units out,
// a winding valley toward the bay, far relief capped at .14*d (~8 deg). GPU and CPU mirror must still match.
test('#757 (Nov 12 update) hills grow with distance: rolling near hills, valley toward the bay, far relief capped at .14*d, CPU mirror matches',()=>{
 assert.match(g,/smoothstep\(6\.0,uTR\*\.2,d\),\.14\*d\)/);assert.match(g,/ss\(6,o\.r\*\.2,d\),\.14\*d\)/);
 assert.match(g,/float tRoll\(vec2 l\)/);assert.match(g,/export function terrainRoll/);assert.match(g,/float tValley\(vec2 l\)/);assert.match(g,/export function terrainValley/);
 assert.match(g,/smoothstep\(4\.5,13\.0,d\)/);assert.match(g,/ss\(4\.5,13,d\)/);});
test('#762 bands in metres of the real shape, slope in degrees, lit by the one sun colour, ambient floor, haze from 300 m',()=>{
 assert.match(g,/float tM\(vec2 l\)/);assert.match(g,/vRm=tM\(l\)/);assert.match(g,/wet=dry\*\.5/);assert.match(g,/smoothstep\(36\.0,44\.0,bh\)/);assert.match(g,/smoothstep\(100\.0,110\.0,bh\)\*\(1\.0-smoothstep\(27\.0,32\.0,vSl\)\)/);
 assert.match(g,/uTSunC\*dif\*uSunL\*uDay/);assert.match(g,/uTAmb\*\.25/);assert.match(g,/-300\.0\)/);});
test('#764 sea at a SEEDED water level: depth fade, foam line, fresnel, one-sun glint, live sea clock, SIMULATED',()=>{
 const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(g,/const float T_WATER=8\.0/);assert.match(g,/mix\(shallow,deep,smoothstep\(\.0,6\.0,dep\)\)/);assert.match(g,/pow\(1\.0-max\(dot\(N,V\),0\.0\),4\.0\)/);assert.match(g,/,100\.0\)\*uSunL\*uDay/);assert.match(g,/float fo=/);
 assert.match(g,/sea:'SIMULATED sea/);assert.match(w,/lk2Ground\.terrainSea\(UG\.uSeaT\.value/);assert.ok(!/Math\.random/.test(g));});
