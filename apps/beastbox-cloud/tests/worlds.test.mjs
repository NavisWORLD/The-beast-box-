import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {LIMITS,WORLDS,cstTree,treeTips,worldAnchor,moonPeriod,tunnelPath,travelPose,wellPull} from '../lib/worlds/worlds-math.mjs';
test('CST trees: deterministic, capped, 1/phi taper',()=>{const a=cstTree('x'),b=cstTree('x');assert.deepEqual(a,b);assert.ok(a.length<=LIMITS.maxSegments&&a.length>10);
 const l=s=>Math.hypot(s.b[0]-s.a[0],s.b[1]-s.a[1],s.b[2]-s.a[2]);const d2=a.filter(s=>s.d===2);assert.ok(d2.every(s=>l(s)<l(a[0])));assert.ok(treeTips(a).length>0);});
test('worlds: distinct, outside home, own wells and gentle orbits',()=>{assert.ok(WORLDS.length>=4);assert.equal(new Set(WORLDS.map(w=>w.atmo)).size,WORLDS.length);
 for(const w of WORLDS){const p=worldAnchor(w,0),q=worldAnchor(w,10);assert.ok(Math.hypot(p.x,p.z)>35);assert.ok(Math.hypot(p.x-q.x,p.y-q.y,p.z-q.z)<3);assert.ok(moonPeriod(w)>5);}
 const f=wellPull({x:0,y:0,z:0},{x:10,y:0,z:0},5);assert.ok(f.x>0&&f.g<wellPull({x:5,y:0,z:0},{x:10,y:0,z:0},5).g);});
test('gravity tunnel: exact endpoints, bent by wells, out-stay-back',()=>{const to={x:40,y:10,z:0};const w=[{x:20,y:4,z:15,mass:12}];
 const s=tunnelPath({x:0,y:0,z:0},to,[]),g=tunnelPath({x:0,y:0,z:0},to,w);assert.deepEqual(g[0],{x:0,y:0,z:0});assert.deepEqual(g.at(-1),to);assert.ok(g[32].z>s[32].z);
 const trip={out:g};assert.equal(travelPose(trip,1).phase,'go');assert.equal(travelPose(trip,12).phase,'stay');assert.equal(travelPose(trip,20).phase,'back');assert.ok(travelPose(trip,30).done);});
test('cage wiring + mobile caps',()=>{const c=fs.readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 assert.match(c,/buildWorlds\(THREE,scene,\{low/);assert.match(c,/uw\.bodies\(\)/);assert.match(c,/uwPose/);
 const w=fs.readFileSync(new URL('../lib/worlds/worlds.ts',import.meta.url),'utf8');assert.match(w,/InstancedMesh/);assert.match(w,/new THREE\.LOD/);assert.match(w,/cloudsLow/);
 assert.ok(LIMITS.homeTreesLow<=LIMITS.homeTreesHigh&&LIMITS.cloudsLow*LIMITS.puffs<=60);});
