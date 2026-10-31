import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const g=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#753 far meadow warm lift: 7-12 units soft, live sun, under bloom, not on Beach Two',()=>{
 assert.match(g,/uFarLift:\{value:0\}/);assert.match(g,/smoothstep\(5\.0,8\.0,vD\)\*\(1\.0-smoothstep\(11\.0,14\.0,vD\)\)/);
 assert.match(g,/smoothstep\(\.0,\.3,uSunL\)/);assert.match(g,/c=min\(c,vec3\(\.85\)\)/);
 assert.match(w,/lk2Ground\.farLift\(beachCamRef\.current\?0:1\)/);assert.ok(!w.includes('Math.random'));});
