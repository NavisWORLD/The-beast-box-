// Nov 12 2026: rounded props (rocks, caps, crystals) only; creatures, Zeref and the eyed trees are never rounded.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {roundMode,weld,subdivide,taubin} from '../lib/look/prop-round.ts';
test('only prop materials from prop models are rounded',()=>{
 assert.equal(roundMode('rock','/x/aliveprops/models/rock_boulder_alive.glb'),'soft');assert.equal(roundMode('cap','/x/aliveprops/models/m.glb'),'soft');
 assert.equal(roundMode('crystal','/x/groundcover/models/c.glb'),'gem');assert.equal(roundMode('rock','/x/trees/models/t_near.glb'),null);assert.equal(roundMode('leaf_purple','/x/aliveprops/a.glb'),null);
 const src=readFileSync(new URL('../lib/look/prop-round.ts',import.meta.url),'utf8');assert.doesNotMatch(src,/Math\.random/);});
test('weld + subdivide + taubin keeps a tetrahedron closed and roughly its size',()=>{
 const P=[0,0,0,1,0,0,0,1,0,0,0,1],I=[0,2,1,0,1,3,0,3,2,1,2,3];let {P:p,I:i}=weld(P,I);assert.equal(p.length/3,4);({P:p,I:i}=subdivide(p,i));({P:p,I:i}=subdivide(p,i));assert.equal(i.length/3,4*16);
 const q=taubin(p,i);const ext=(a)=>Math.max(...a.filter((_,k)=>k%3===0))-Math.min(...a.filter((_,k)=>k%3===0));assert.ok(ext(q)>ext(p)*.6&&ext(q)<=ext(p)*1.05);});
