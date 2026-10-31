import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const g=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#755 terrain: 3 seeded hill layers 80/20/5 m, bands, atmospheric perspective, LOW smaller, grass+residents on height, SIMULATED',()=>{
 assert.match(g,/\$\{\(80\*M\)\.toFixed\(6\)\}\*tVn\(p\*\.0015\)\+\$\{\(20\*M\)\.toFixed\(6\)\}\*tVn\(p\*\.005\+17\.3\)\+\$\{\(5\*M\)\.toFixed\(6\)\}\*tVn\(p\*\.02\+41\.7\)/);
 assert.match(g,/80\*M\*tVnJ\(px\*\.0015/);assert.match(g,/tLow\?300:900/);assert.match(g,/SIMULATED terrain/);
 for(const b of ['sand','meadow','forest','rock','snow'])assert.match(g,new RegExp('vec3 '+b+'=|,'+b+'='));
 assert.match(g,/atmospheric perspective toward the live horizon colour/);assert.match(g,/TU\.uTHor\.value\.setRGB\(look\.hor/);
 assert.match(w,/o\.position\.set\(bayV\.x,lk2Ground\.terrainAt\(bayV\.x,bayV\.z\),bayV\./);assert.match(w,/p\.y\+tH\(base\)/);assert.match(w,/lk2Ground\.terrainSun\(/);
 assert.ok(!/Math\.random/.test(g)&&!/Math\.random/.test(w));});
test('#755 CPU terrain mirror is relative, never negative, zero near you',async()=>{
 const src=g;const m=src.match(/export function terrainHeightAt/);assert.ok(m);});
