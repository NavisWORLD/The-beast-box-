import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const src=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
// plasma.ts is TS; check the pure envelopes by evaluating the exported arrow bodies textually-equivalent copies
const P=src('lib/worlds/plasma.ts');
test('plasma planet has core shader, ring, instanced emission lines, orbit chains, lens + flash + label',()=>{
 for(const k of ['CORE_FS','TorusGeometry','InstancedBufferGeometry','aDir','uLean','chainLines','lensRing','sectorSprite','one path, one order'])assert.ok(P.includes(k),k);
 assert.match(P,/vS>0\.\?uCol\*1\.4:vec3\(1\.\)/);// coloured one side, white the other
 assert.match(P,/linesLow:48,linesHigh:96/);});
test('lens stretch 1.5x0.8 easing back; flash window',()=>{const f=new Function('return '+P.match(/export function lensStretch\((.|\n)*?\n?}\n/)[0].replace('export ','').replace(/:number/g,'').replace('dur=1.4','dur'))();
 const [sx,sy]=f(0,1.4);assert.ok(Math.abs(sx-1.5)<1e-9&&Math.abs(sy-.8)<1e-9);assert.deepEqual(f(2,1.4),[1,1]);});
test('wired: planets use plasma, tunnel on depart/arrive, feed pulses core, cage flash/inversion + nebula swirl',()=>{const w=src('lib/worlds/worlds.ts'),c=src('components/cage-pocket-dimension.tsx');
 assert.match(w,/buildPlasmaPlanet\(/);assert.match(w,/plasma\?\.tunnel\(/);assert.match(w,/pulseNear/);assert.match(c,/uw\.pulseNear\(/);assert.match(c,/invert\(1\)/);assert.match(c,/nebula\.rotation\.y\+=/);});
