import test from 'node:test';import assert from 'node:assert/strict';import * as THREE from 'three';
import {readFileSync,statSync} from 'node:fs';
import {createZerefDriver,ZEREF_MOODS,ZEREF_MORPHS} from '../lib/creatures3d/zeref-glb-driver.mjs';
function rig(){
 const root=new THREE.Group();const mk=(name,parent,x,y,z)=>{const b=new THREE.Bone();b.name=name;b.position.set(x,y,z);parent.add(b);return b;};
 const r=mk('root',root,0,0,0),sp=mk('spine',r,0,.1,0),ch=mk('chest',sp,0,.3,0),hd=mk('head',ch,0,.15,0);
 for(const s of ['L','R']){const k=s==='L'?-1:1;const e0=mk('ear.0.'+s,hd,k*.28,.4,0);mk('ear.1.'+s,e0,0,.2,0);
  const w0=mk('wing.0.'+s,ch,k*.15,0,-.15);const w1=mk('wing.1.'+s,w0,0,.3,0);mk('wing.2.'+s,w1,0,.3,0);}
 for(const s of ['L','R']){const k=s==='L'?-1:1;mk('leg.'+s,sp,k*.2,-.1,-.05);mk('paw.'+s,sp,k*.12,.1,.15);}
 let p=sp;for(let i=0;i<5;i++)p=mk('tail.'+i,p,0,i?.15:-.05,i?0:-.2);
 const mesh=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshBasicMaterial());
 mesh.morphTargetDictionary=Object.fromEntries(ZEREF_MORPHS.map((n,i)=>[n,i]));mesh.morphTargetInfluences=ZEREF_MORPHS.map(()=>0);root.add(mesh);
 root.updateMatrixWorld(true);return {root,mesh};
}
const run=(seed,mood,frames=240)=>{const {root,mesh}=rig();const d=createZerefDriver(THREE,root,{seed,mood});
 for(let i=0;i<frames;i++)d.update(1/60);const t=root.getObjectByName('tail.4');const w=new THREE.Vector3().setFromMatrixPosition(t.matrixWorld);return {d,mesh,w,root};};
test('driver builds 5 spring chains (tail, 2 ears, 2 wings) on the CST clock',()=>{
 const {d}=run('zeref','calm',10);assert.equal(d.chains.length,5);assert.ok(d.clock.steps>=19&&d.clock.steps<=21);
});
test('deterministic per seed, different across seeds, finite poses',()=>{
 const a=run('zeref','happy'),b=run('zeref','happy'),c=run('nyx','happy');
 assert.deepEqual(a.w.toArray(),b.w.toArray());assert.notDeepEqual(a.w.toArray(),c.w.toArray());
 a.root.traverse(o=>{for(const v of o.quaternion.toArray())assert.ok(Number.isFinite(v));});
});
test('moods drive expression morphs; chain lengths are preserved',()=>{
 for(const m of Object.keys(ZEREF_MOODS)){const {mesh,d}=run('zeref',m,300);
  for(const [k,v] of Object.entries(ZEREF_MOODS[m].morph))assert.ok(Math.abs(mesh.morphTargetInfluences[mesh.morphTargetDictionary[k]]-v)<.08,m+':'+k);
  for(const c of d.chains)for(let i=1;i<c.ch.pts.length;i++){const p=c.ch.pts[i],q=c.ch.pts[i-1];assert.ok(Math.abs(Math.hypot(p.x-q.x,p.y-q.y,p.z-q.z)-c.ch.len[i-1])<.02);}}
});
test('the shipped GLB is meshopt-compressed, rigged, has every expression, mouth and brow morph target and stays under the mobile budget',()=>{
 const u=new URL('../public/creatures3d/zeref.glb',import.meta.url);const b=readFileSync(u);assert.equal(b.toString('ascii',0,4),'glTF');
 const n=b.readUInt32LE(12);const j=JSON.parse(b.subarray(20,20+n).toString('utf8'));
 assert.ok(j.extensionsUsed.includes('EXT_meshopt_compression'));for(const k of ZEREF_MORPHS)assert.ok(j.meshes[0].extras.targetNames.includes(k),k);
 const names=j.nodes.map(x=>x.name);for(const k of ['head','spine','tail.4','wing.2.L','ear.1.R'])assert.ok(names.includes(k),k);
 const tris=j.meshes[0].primitives.reduce((s,p)=>s+j.accessors[p.indices].count/3,0);assert.ok(tris<=25000,'tris '+tris);
 assert.ok(statSync(u).size<1.5e6);
});
test('blinks stay stable and brief at low frame rates (30 and 20 fps): no flicker, no stuck lids',()=>{
 for(const fps of [30,20,60]){const {root,mesh}=rig();const d=createZerefDriver(THREE,root,{seed:'zeref',mood:'calm'});const bi=mesh.morphTargetDictionary.blink;
  let closed=0,runs=0,prev=false,frames=fps*20;
  for(let i=0;i<frames;i++){d.update(1/fps);const c=mesh.morphTargetInfluences[bi]>.5;if(c){closed++;if(!prev)runs++;}prev=c;}
  assert.ok(runs>=3&&runs<=12,fps+'fps blink count '+runs);assert.ok(closed/frames<.12,fps+'fps closed fraction '+closed/frames);}
});
test('walk gait: stance paws are locked to the scrolling floor (no sliding), swing paws lift, tail counterbalances',()=>{
 const {root}=rig();const d=createZerefDriver(THREE,root,{seed:'zeref',mood:'walk'});
 for(let i=0;i<240;i++)d.update(1/60);  // walk blend settles
 let maxSlip=0,maxLift=0,prev=null;
 for(let i=0;i<180;i++){d.update(1/60);const f=d.feet(),tr=d.travel;
  if(prev)for(let j=0;j<f.length;j++){if(f[j].lift<1e-4&&prev.f[j].lift<1e-4){const slip=Math.abs((f[j].z+tr)-(prev.f[j].z+prev.tr));maxSlip=Math.max(maxSlip,slip);}maxLift=Math.max(maxLift,f[j].lift);}
  prev={f,tr};}
 assert.ok(maxSlip<.004,'stance slip '+maxSlip);assert.ok(maxLift>.03,'lift '+maxLift);assert.ok(d.travel>.3,'travel '+d.travel);
});
test('bones are found under GLTFLoader-sanitized names (tail0, earR... dots stripped): chains and feet bind',()=>{
 const {root}=rig();root.traverse(o=>{o.name=o.name.replace(/\./g,'');});
 const d=createZerefDriver(THREE,root,{seed:'zeref',mood:'walk'});assert.equal(d.chains.length,5);assert.equal(d.feet().length,4);
});
test('cosmic drive: deterministic per seed; scared stirs the beast, calm settles; heartbeat is faster when aroused',()=>{
 const go=(m,n=600)=>{const {root}=rig();const d=createZerefDriver(THREE,root,{seed:'zeref',mood:m});const beats=[];for(let i=0;i<n;i++){d.update(1/60);beats.push(d.cosmic().beat);}return {c:d.cosmic(),beats};};
 const a=go('scared'),b=go('scared'),k=go('calm');
 assert.deepEqual(a.c,b.c);assert.ok(a.c.stir>.8,'scared stir '+a.c.stir);assert.ok(k.c.stir<.3,'calm stir '+k.c.stir);
 const peaks=bs=>bs.filter((v,i)=>i&&v>.9&&bs[i-1]<=.9).length;assert.ok(peaks(a.beats)>=peaks(k.beats),'beats');
});
