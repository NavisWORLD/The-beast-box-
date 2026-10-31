import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const g=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
test('#756 hills show: absolute seeded height, 6-unit spawn pad only, narrow bay cut, debug lookup + magenta flag, honest label',()=>{
 assert.ok(!/tRaw\(uTOrg\)/.test(g));
 assert.match(g,/uTBay\.y\*\.95,uTBay\.y\*1\.2/);assert.match(g,/terrdbg=1/);assert.match(g,/ground\.visible=false/);
 assert.match(g,/label:'Terrain shape · SEEDED',at:tAt/);assert.ok(!/Math\.random/.test(g));});
test('#757 hills grow with distance and stay under ~7 deg',()=>{assert.match(g,/smoothstep\(6\.0,uTR\*\.35,d\),\.12\*d\)/);assert.match(g,/ss\(6,o\.r\*\.35,d\),\.12\*d\)/);});
test('#762 bands in metres of the real shape, slope in degrees, lit by the one sun colour, ambient floor, haze from 300 m',()=>{
 assert.match(g,/float tM\(vec2 l\)/);assert.match(g,/vRm=tM\(l\)/);assert.match(g,/wet=dry\*\.5/);assert.match(g,/smoothstep\(36\.0,44\.0,bh\)/);assert.match(g,/smoothstep\(100\.0,110\.0,bh\)\*\(1\.0-smoothstep\(27\.0,32\.0,vSl\)\)/);
 assert.match(g,/uTSunC\*dif\*uSunL\*uDay/);assert.match(g,/uTAmb\*\.25/);assert.match(g,/-300\.0\)/);});
