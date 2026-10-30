import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const rd=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('look pass 2: no random, pack values, honest labels',()=>{
 const look=rd('lib/universe/one-world-look.ts'),land=rd('components/seeded-land-2d.tsx'),lw=rd('components/living-world.tsx');
 for(const s of [look,land])assert.doesNotMatch(s,/Math\.random/);
 assert.match(look,/pow\(clamp\(e,0\.0,1\.0\),\.45\)/);assert.match(look,/#437E9E/);assert.match(look,/azimuthDeg:191\.785/);assert.match(look,/1\.0-lit/);
 assert.match(look,/d:2000,crestDeg:2\.24/);assert.match(land,/SEEDED/);
 assert.match(lw,/toneMappingExposure=\.85/);assert.match(lw,/sun\.intensity=(3\.03\*os1\.day|rig\.sunIntensity)/); /* rig.sunIntensity = 3.03 x day (sky-view lightRigFor, tested in p1-post-chain) */assert.doesNotMatch(lw,/map\(i=>srgb\(hz3/);
 assert.match(lw,/stepFlight\(S,inp,rdt,gAt\)/);assert.match(lw,/How this look is made<\/summary>/);assert.match(lw,/Mood · ABSENT/);
 assert.doesNotMatch(rd('lib/universe/surface-three.ts'),/\.6\+\.4\*t\[0\]/);});
