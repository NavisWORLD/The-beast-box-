import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#750 ring look: width, warm tips under bloom, clumps, contact patches, LOW density unchanged',()=>{
 assert.match(w,/p\.x\*=\.7778\/h;p\.z\*=\.7778\/h;/);assert.ok(Math.abs(.09*.7778-.07)<.001);
 assert.match(w,/min\(vec3\(\.298,\.549,\.165\)\*1\.15\+vec3\(\.06,\.02,0\.\),tipC\*1\.25\)/);
 const warm=[.298*1.15+.06,.549*1.15+.02,.165*1.15],tip=[.549,.753,.29];warm.forEach((v,i)=>assert.ok(v<=tip[i]*1.25));
 assert.match(w,/const NC=lowT\?24:40/);assert.match(w,/d=\.12\+\(lowT\?\.5:\.78\)\*Math\.sqrt\(r\(\)\)/);assert.ok(.12+.78<=.9);
 assert.match(w,/const nR=lowT\?ringMax:Math\.round\(ringMax\*1\.5\)/);assert.match(w,/const ringN=lowT\?Math\.round\(nR\/3\):nR;/);
 assert.match(w,/pm\.material\.opacity=\.1\+\.35\*sl/);assert.match(w,/alphaMap:cTex/);
 assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
