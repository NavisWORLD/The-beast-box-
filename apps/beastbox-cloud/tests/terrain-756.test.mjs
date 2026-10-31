import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const g=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
test('#756 hills show: absolute seeded height, 6-unit spawn pad only, narrow bay cut, debug lookup + magenta flag, honest label',()=>{
 assert.ok(!/tRaw\(uTOrg\)/.test(g));
 assert.match(g,/uTBay\.y\*\.95,uTBay\.y\*1\.2/);assert.match(g,/terrdbg=1/);assert.match(g,/ground\.visible=false/);
 assert.match(g,/label:'Terrain shape · SEEDED',at:tAt/);assert.ok(!/Math\.random/.test(g));});
test('#757 hills grow with distance and stay under ~7 deg',()=>{assert.match(g,/smoothstep\(6\.0,uTR\*\.35,d\),\.12\*d\)/);assert.match(g,/ss\(6,o\.r\*\.35,d\),\.12\*d\)/);});
