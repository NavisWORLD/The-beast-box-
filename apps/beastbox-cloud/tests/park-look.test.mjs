import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {LOOKS,readLook,writeLook,lookLabel,nextLook,isLook,usesGenesisBase,snapshotWorld} from '../lib/look/look-mode.ts';
import {PARK_DAY,PARK_NIGHT,PARK_COST,parkGrade,hexRgb,saturation} from '../lib/look/park-palette.ts';
import {PARK_VARIANTS,editShader,attachParkLook,PARK_LABEL} from '../lib/look/park.ts';
import {attachGenesisLook} from '../lib/look/attach.ts';
import {layoutGrass,PARK_GRASS_BUDGET,grassBudget,seededStream,buildParkGrass,syncParkGrass} from '../lib/look/park-grass.ts';

const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),key:i=>[...m.keys()][i]??null,get length(){return m.size;}};};

test('Park is a third opt-in look; Classic stays the default and the world is untouched',()=>{
 assert.deepEqual([...LOOKS],['classic','genesis','park']);
 assert.ok(isLook('park'));
 assert.equal(lookLabel('park'),'Look: Park');
 assert.equal(nextLook('classic'),'genesis');
 assert.equal(nextLook('genesis'),'park');
 assert.equal(nextLook('park'),'classic');
 assert.equal(usesGenesisBase('park'),true);
 assert.equal(usesGenesisBase('genesis'),true);
 assert.equal(usesGenesisBase('classic'),false);
 const s=mem();s.setItem('lw:universe','{"seed":"s","tick":3}');
 assert.equal(readLook(s),'classic');
 const before=snapshotWorld(s);
 writeLook(s,'park');
 assert.equal(readLook(s),'park');
 assert.deepEqual(snapshotWorld(s),before);
});

test('Park palette carries the spec hex values and grades brighter than Genesis by day, indigo by night',()=>{
 assert.equal(PARK_DAY.skyZenith,'#1AA6FF');assert.equal(PARK_DAY.haze,'#90D4E8');assert.equal(PARK_DAY.meadowSun,'#79D389');
 assert.equal(PARK_DAY.grassTip,'#8EE09A');assert.equal(PARK_DAY.grassRoot,'#2F5A43');assert.equal(PARK_DAY.sand,'#F5D7A0');
 assert.equal(PARK_DAY.cliffSun,'#E08A62');assert.equal(PARK_DAY.oceanShallow,'#4DD9FC');assert.equal(PARK_DAY.oceanDeep,'#2BA0D4');
 assert.equal(PARK_NIGHT.shadow,'#3A5A70');assert.equal(PARK_NIGHT.zenith,'#000444');assert.equal(PARK_NIGHT.farHills,'#4174A3');
 assert.deepEqual(hexRgb('#1AA6FF').map(v=>Math.round(v*255)),[0x1a,0xa6,0xff]);
 for(const k of Object.values(PARK_COST))for(const t of ['LOW','MED','HIGH','GOD'])assert.ok(t in k);
 const noon=parkGrade(50);
 assert.equal(noon.stop,'noon');
 assert.deepEqual(noon.zenith.map(v=>+v.toFixed(4)),hexRgb('#1AA6FF').map(v=>+v.toFixed(4)));
 assert.deepEqual(noon.haze.map(v=>+v.toFixed(4)),hexRgb('#90D4E8').map(v=>+v.toFixed(4)));
 // Genesis day zenith default in lib/look/attach.ts is [.2,.45,.75]; Park must be clearly more saturated.
 assert.ok(saturation(noon.zenith)>saturation([.2,.45,.75])+.1);
 assert.ok(Math.max(...noon.meadow)>Math.max(.20,.46,.16)+.3,'Park meadow is a bright lime, not olive');
 const night=parkGrade(-30);
 assert.equal(night.stop,'night');
 assert.ok(night.zenith[2]>night.zenith[0]&&night.zenith[2]>night.zenith[1],'night zenith is blue, not grey');
 assert.ok(night.zenith[2]>.2,'night is indigo, not black');
 assert.notDeepEqual(parkGrade(2,true).horizon,parkGrade(2,false).horizon,'morning and dusk differ');
 assert.deepEqual(parkGrade(12.5,true),parkGrade(12.5,true),'pure function of the one sun');
});

test('every Park twin edit still matches the Genesis shaders',async()=>{
 const THREE=await import('three');
 const scene=new THREE.Scene();
 const g=attachGenesisLook(THREE,scene,{seed:'s',tier:'LOW',heightAt:(x,z)=>Math.sin(x*.05)*2+Math.cos(z*.04)*1.5,getLook:()=>'genesis',reduced:()=>true,nowMs:()=>0,readTick:()=>1});
 g.sync();
 const names=new Map(g.group.children.map(o=>[o.name,o]));
 for(const v of PARK_VARIANTS){
  const o=names.get(v.key);
  assert.ok(o,'Genesis mesh '+v.key);
  const out=editShader(o.material.fragmentShader,v.edits);
  assert.ok(out,'Park edit matched '+v.key);
  assert.match(out,/uPk/);
  assert.match(out,/#include <colorspace_fragment>/,'Park twins run three\'s output chunks so the hex lands on screen');
  for(const line of out.split('\n').filter(l=>l.startsWith('#define')))assert.equal(line.trim().split(/\s+/).length,3,'a #define owns its whole line: '+line);
 }
 g.dispose();
});

// What the renderer sees: a hidden group draws nothing; a visible one draws these materials and uniform values.
const snap=group=>!group.visible?'hidden':group.children.filter(o=>o.visible).map(o=>({name:o.name,visible:o.visible,mat:o.material?.name||o.material?.type,frag:o.material?.fragmentShader,
 u:o.material?.uniforms?Object.fromEntries(Object.entries(o.material.uniforms).map(([k,v])=>[k,v.value?.toArray?v.value.toArray():v.value])):null}));

test('Classic and Genesis frames are identical with Park mounted; Park swaps twins in and back out',async()=>{
 const THREE=await import('three');
 const make=(withPark,lookRef)=>{
  const scene=new THREE.Scene();
  const sun={dir:[.3,.8,.5],day:1,elevationDeg:40,sky:{zenith:[.2,.45,.75],horizon:[.62,.78,.9],starAlpha:0}};
  const g=attachGenesisLook(THREE,scene,{seed:'park',tier:'LOW',heightAt:(x,z)=>Math.sin(x*.05)*2+Math.cos(z*.04)*1.5,getLook:()=>lookRef.v,reduced:()=>true,nowMs:()=>0,readTick:()=>3,getSun:()=>sun});
  const p=withPark?attachParkLook(THREE,g,{getLook:()=>lookRef.v,getSun:()=>sun,seed:'park',heightAt:(x,z)=>Math.sin(x*.05)*2+Math.cos(z*.04)*1.5}):null;
  const frame=()=>{g.anchor.onBeforeRender();};
  return {g,p,frame};
 };
 for(const look of ['genesis','classic']){
  const ra={v:look},rb={v:look};
  const plain=make(false,ra),withPark=make(true,rb);
  plain.frame();withPark.frame();
  assert.deepEqual(snap(withPark.g.group),snap(plain.g.group),look+' identical with Park mounted');
  // Visit Park, then come back: still identical.
  rb.v='park';withPark.frame();
  assert.equal(withPark.p.on,true);
  if(look==='genesis'){
   const mats=withPark.g.group.children.filter(o=>/^park:genesis-/.test(o.material?.name||''));
   assert.equal(mats.length,PARK_VARIANTS.length,'all five Park twins swap in');
   assert.equal(withPark.p.state().swapped,PARK_VARIANTS.length);
   assert.equal(withPark.p.state().label,PARK_LABEL);
   const grass=withPark.g.group.children.find(o=>o.name==='park-grass');
   assert.ok(grass&&grass.visible,'Park meadow is drawn in Park');
   assert.equal(withPark.p.state().grass.count,grass.geometry.instanceCount);
  }
  rb.v=look;withPark.frame();plain.frame();
  assert.deepEqual(snap(withPark.g.group),snap(plain.g.group),look+' identical after a Park visit');
  plain.g.dispose();withPark.p.dispose();withPark.g.dispose();
 }
});

test('Park adds no light, no clock and no unseeded draw, and the page wiring keeps Classic and Genesis',()=>{
 for(const f of ['lib/look/park.ts','lib/look/park-palette.ts','lib/look/park-grass.ts']){
  const s=read(f);
  assert.doesNotMatch(s,/Math\.random|setInterval|setTimeout|Date\.now|performance\.now/,f);
  assert.doesNotMatch(s,/DirectionalLight|PointLight|SpotLight|HemisphereLight/,f);
  assert.doesNotMatch(s,/pok[eé]mon|nintendo|game freak/i,f);
 }
 const lw=read('components/living-world.tsx');
 assert.match(lw,/attachParkLook\(THREE,genesis/);
 assert.match(read('components/universe-settings.tsx'),/<option value="park">Park<\/option>/);
 assert.match(read('components/universe-settings.tsx'),/<option value="genesis">Genesis<\/option>/);
 assert.match(read('components/universe-settings.tsx'),/<option value="classic">Classic<\/option>/);
});

test('Park grass: seeded layout per tier, phone-safe MED, no blades in water, still on LOW and in reduced motion',async()=>{
 assert.equal(PARK_GRASS_BUDGET.LOW.blades,2000);assert.equal(PARK_GRASS_BUDGET.MED.blades,8000);
 assert.equal(PARK_GRASS_BUDGET.HIGH.blades,25000);assert.equal(PARK_GRASS_BUDGET.GOD.blades,60000);
 assert.equal(PARK_GRASS_BUDGET.LOW.sway,false);assert.equal(grassBudget('nope'),PARK_GRASS_BUDGET.MED);
 const s1=seededStream('k'),s2=seededStream('k');for(let i=0;i<50;i++)assert.equal(s1(),s2());
 const h=(x,z)=>Math.sin(x*.1)*.8+Math.cos(z*.07)*.6;
 const a=layoutGrass({seed:'w',tier:'MED',heightAt:h}),b=layoutGrass({seed:'w',tier:'MED',heightAt:h});
 assert.equal(a.count,8000);
 assert.deepEqual([...a.offsets],[...b.offsets],'two loads of one seed match');
 assert.deepEqual([...a.params],[...b.params]);
 assert.notDeepEqual([...layoutGrass({seed:'other',tier:'MED',heightAt:h}).offsets.slice(0,30)],[...a.offsets.slice(0,30)]);
 for(let i=0;i<a.count;i++){const x=a.offsets[i*3],z=a.offsets[i*3+2];assert.ok(Math.hypot(x,z)<=PARK_GRASS_BUDGET.MED.radius+1e-6);assert.ok(Math.abs(a.offsets[i*3+1]-h(x,z))<1e-5);}
 const dry=layoutGrass({seed:'w',tier:'LOW',heightAt:h,wetAt:(x)=>x<0});
 for(let i=0;i<dry.count;i++)assert.ok(dry.offsets[i*3]>=0,'no blade in water');
 const THREE=await import('three');
 const G=buildParkGrass(THREE,{seed:'w',tier:'LOW',heightAt:h});
 assert.equal(G.uniforms.uSway.value,0,'LOW holds the blades still');
 assert.equal(G.mesh.geometry.attributes.position.count,5,'5-vertex blade');
 const grade={grassRoot:[.1,.2,.1],grassTip:[.5,.8,.5],meadow:[.4,.8,.5],nightGround:[.1,.3,.3],day:1};
 syncParkGrass(G.uniforms,{phase:2,amp:.15,reduced:true},grade);
 assert.equal(G.uniforms.uAmp.value,0,'reduced motion holds still');
 syncParkGrass(G.uniforms,{phase:2,amp:.15},grade);
 assert.equal(G.uniforms.uAmp.value,.15);assert.equal(G.uniforms.uPhase.value,2);
 assert.match(G.mesh.material.fragmentShader,/#include <colorspace_fragment>/);
 assert.doesNotMatch(read('lib/look/park-grass.ts'),/Math\.random|Date\.now|performance\.now|setTimeout|setInterval/);
});
