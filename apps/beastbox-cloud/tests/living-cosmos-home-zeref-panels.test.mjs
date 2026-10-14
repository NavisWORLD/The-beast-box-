import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('home guide renders Zeref rig with turntable; procedural guide preserved',()=>{const s=r('components/homepage-creature.tsx');
 assert.match(s,/cosmos-zeref-turn/);assert.match(s,/rotateY\(/);assert.match(s,/useState<View>\('zeref'\)/);assert.ok(s.includes('<CosmicCompanion3D'));for(const k of ['Classic 3D guide','Rotate 360°','Front','Side','Back'])assert.ok(s.includes(k));});
test('home card and pocket residents are minimizable, collapsed on phone',()=>{const s=r('components/homepage-creature.tsx'),p=r('components/cage-pocket-dimension.tsx');
 for(const x of [s,p]){assert.match(x,/matchMedia\('\(max-width:560px\)'\)/);assert.match(x,/<details/);assert.match(x,/onToggle=/);}
 assert.match(s,/Minimize card/);assert.match(p,/Minimize residents/);});
