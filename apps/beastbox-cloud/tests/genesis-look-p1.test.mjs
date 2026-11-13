import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readdirSync,readFileSync} from 'node:fs';
import {readLook,currentLook,snapshotWorld,withLook,DEFAULT_LOOK,LOOK_KEY} from '../lib/look/look-mode.ts';
import {presentationTier,dropTierIfSlow,considerDrop,budgetFor} from '../lib/look/tiers.ts';
import {motionAt,presentationTick,windSway,cloudDrift,treeSway,FOLIAGE_IN_P1,CREATURE_MOTION,MOTION_LABEL} from '../lib/look/motion.ts';
import {hazeAmount,hazeStack,hazeTint} from '../lib/look/haze.ts';
import {sunDiscDir} from '../lib/look/sky-dome.ts';
import {foamAmount,fresnelSchlick,buildWater,shoreSurface,shoreAlpha,WAVE_CREST,WATER_LABEL} from '../lib/look/water.ts';
import {buildTerrainLod,smoothNormal,ringPlan,plannedTris} from '../lib/look/terrain-lod.ts';
import {buildFoliage,syncFoliage} from '../lib/look/foliage.ts';
import {readSeededHeight} from '../lib/look/height-read.ts';
import {attachGenesisLook} from '../lib/look/attach.ts';
import {SPECKLE_STOP} from '../lib/look/speckle.ts';
import {oneSunAt} from '../lib/universe/one-sun.mjs';
import {lightRigFor} from '../lib/universe/sky-view.mjs';

const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),key:i=>[...m.keys()][i]??null,get length(){return m.size;}};};
const posHash=geo=>{const a=geo.attributes.position.array;return createHash('sha256').update(Buffer.from(a.buffer,a.byteOffset,a.byteLength)).digest('hex');};

test('Park is the one look, an old saved look is cleared, and the world state is untouched',()=>{
 const s=mem();
 s.setItem('lw:universe','{"seed":"s","tick":3}');
 s.setItem('lw:spawned','1');
 s.setItem('lw:traits:guest','{"calm":0.5}');
 const before=snapshotWorld(s);
 assert.equal(DEFAULT_LOOK,'park');
 assert.equal(readLook(s),'park');
 s.setItem(LOOK_KEY,'classic');
 assert.equal(readLook(s),'park');
 assert.equal(s.getItem(LOOK_KEY),null);
 assert.equal(currentLook(),'park');
 const world={seed:'s',tick:3,planets:[{id:'home'}]};
 const frozen=structuredClone(world);
 assert.equal(withLook(world).world,world);
 assert.equal(withLook(world).look,'park');
 assert.deepEqual(snapshotWorld(s),before);
 assert.equal(s.getItem('lw:universe'),'{"seed":"s","tick":3}');
 assert.deepEqual(world,frozen);
});

test('desktop defaults to HIGH, phones to MED, and a slow frame window drops one tier',()=>{
 const s=mem();
 assert.equal(presentationTier(s,{phone:true,cores:2,memoryGB:1}),'MED');
 assert.equal(presentationTier(s,{phone:true,cores:8,memoryGB:8}),'MED');
 assert.equal(presentationTier(s,{phone:true,reducedMotion:true,cores:2,memoryGB:1}),'MED');
 assert.equal(presentationTier(s,{phone:true,softGL:true,cores:8,memoryGB:8}),'MED');
 assert.equal(presentationTier(s,{cores:4,memoryGB:4,softGL:true}),'HIGH');
 assert.equal(presentationTier(s,{cores:8,memoryGB:8}),'GOD');
 s.setItem('beastbox.quality.v1','LOW');
 assert.equal(presentationTier(s,{cores:8,memoryGB:8}),'LOW');
 assert.equal(budgetFor('MED').dpr,1.5);
 assert.equal(budgetFor('MED').rings,4);
 assert.equal(dropTierIfSlow('HIGH',21,'HIGH'),'MED');
 assert.equal(dropTierIfSlow('MED',10,'HIGH'),'MED');
 assert.equal(dropTierIfSlow('GOD',30,'HIGH'),'HIGH');
 assert.equal(considerDrop('HIGH','HIGH',Array.from({length:10},()=>40)).consumed,false);
 const slow=considerDrop('HIGH','HIGH',Array.from({length:30},()=>100));
 assert.equal(slow.consumed,true);
 assert.equal(slow.tier,'MED');
 assert.equal(considerDrop('HIGH','HIGH',Array.from({length:30},()=>10)).tier,'HIGH');
});

test('Genesis motion is deterministic for a seed and tick and does not change world state',()=>{
 const world={seed:'meadow',tick:3.25,planets:[{id:'p'}],beast:{x:1,y:2,z:3},traveler:{x:4,y:0,z:1}};
 const before=structuredClone(world);
 const a=motionAt(world.seed,world.tick,false);
 const b=motionAt(world.seed,world.tick,false);
 assert.deepEqual(a,b);
 assert.equal(a.label,MOTION_LABEL);
 assert.notEqual(motionAt(world.seed,4,false).wavePhase,a.wavePhase);
 assert.notEqual(motionAt('other',world.tick,false).wavePhase,a.wavePhase);
 assert.deepEqual(motionAt(world.seed,1,true),motionAt(world.seed,99,true));
 assert.equal(motionAt(world.seed,5,true).waveAmp,0);
 assert.equal(motionAt(world.seed,5,true).skyDrift,0);
 assert.equal(presentationTick(4,1000,0,true),0);
 assert.equal(presentationTick(4,1000,0,false),presentationTick(4,1000,0,false));
 assert.ok(presentationTick(4,500,0,false)>4&&presentationTick(4,500,0,false)<5);
 assert.deepEqual(world,before);
 assert.equal(CREATURE_MOTION.applied,false);
 assert.equal(FOLIAGE_IN_P1,true);
 const frame=motionAt('wind',2,false);
 assert.equal(windSway(frame,1,2),windSway(frame,1,2));
 assert.equal(cloudDrift(frame),frame.cloudPhase);
 assert.equal(typeof treeSway(frame),'number');
 assert.equal(treeSway(motionAt('wind',2,true)),0);
});

test('seeded height is read only and the same seed builds the same hills',async()=>{
 const opts=Object.freeze({org:[.2,-.4],seed:[3,9],bay:[.4,.8,0],on:true,r:420});
 const before=JSON.stringify(opts);
 let calls=0;
 const heightAt=(x,z)=>{calls++;return readSeededHeight(x,z,opts);};
 const THREE=await import('three');
 const a=buildTerrainLod(THREE,{heightAt,tier:'LOW',seed:'hills'});
 const b=buildTerrainLod(THREE,{heightAt,tier:'LOW',seed:'hills'});
 assert.ok(calls>100);
 assert.equal(JSON.stringify(opts),before);
 assert.equal(posHash(a.geometry),posHash(b.geometry));
 assert.equal(a.rings,4); /* Cory Nov 12: LOW adds one coarse far ring so the horizon is 3D hills, not a flat card */
 assert.ok(plannedTris(ringPlan('MED'))<budgetFor('MED').tris);
 assert.ok(plannedTris(ringPlan('LOW'))<budgetFor('LOW').tris);
 const p=a.geometry.attributes.position,n=a.geometry.attributes.normal;
 const x=p.getX(20),y=p.getY(20),z=p.getZ(20);
 const cn=smoothNormal(heightAt,x,z);
 const dot=n.getX(20)*cn[0]+n.getY(20)*cn[1]+n.getZ(20)*cn[2];
 assert.ok(dot>.999,dot);
 assert.ok(Number.isFinite(y));
});

test('water carves the land, fresnel and foam follow depth, waves are labelled SIMULATED',async()=>{
 assert.equal(WATER_LABEL,'Waves · SIMULATED');
 assert.ok(WAVE_CREST>=.5);
 assert.equal(shoreAlpha(0),0);
 assert.equal(shoreAlpha(-.2),0);
 assert.ok(shoreAlpha(1)>shoreAlpha(.15));
 assert.equal(foamAmount(0),0);
 assert.ok(foamAmount(.1)>.5);
 assert.equal(foamAmount(1),0);
 assert.ok(fresnelSchlick(1)<.05);
 assert.ok(fresnelSchlick(0)>.9);
 const THREE=await import('three');
 const mesh=buildWater(THREE,{heightAt:(x,z)=>Math.sin(x*.7)*1.2,waterLevel:0,tier:'LOW',span:6});
 assert.ok(mesh.wet>0&&mesh.dry>0);
 assert.ok(mesh.foam>0);
 assert.equal(mesh.label,WATER_LABEL);
 const heightAt=(x,z)=>readSeededHeight(x,z,{org:[0,0],seed:[120,340],bay:[0,0,0],on:true,r:900});
 const shore=shoreSurface(heightAt);
 assert.equal(shore.at(0,0),0);
 assert.equal(shore.at(0,0),shoreSurface(heightAt).at(0,0));
 assert.equal(shore.coeff,shoreSurface(heightAt).coeff);
 let wet=0,dry=0;
 for(let i=0;i<24;i++){const a=i/24*Math.PI*2,x=Math.cos(a)*48,z=Math.sin(a)*48;if(shore.at(x,z)>heightAt(x,z))wet++;else dry++;}
 assert.ok(wet>0&&dry>0,`wet ${wet} dry ${dry}`);
});

test('haze thins with height and the sun disc matches the one sun',()=>{
 assert.ok(hazeAmount(80,0) > hazeAmount(80,30));
 assert.ok(hazeAmount(10,0) < hazeAmount(80,0));
 const stacked=hazeStack(400,0),lifted=hazeStack(30,40);
 assert.equal(stacked.layers.length,3);
 assert.ok(stacked.amount>lifted.amount);
 let night=null,day=null;
 for(let s=0;s<240;s+=.5){const os=oneSunAt(s);if(os.elevationDeg<-8)night=os;if(os.elevationDeg>25)day=os;}
 assert.ok(night&&day);
 const rig=lightRigFor(night);
 const disc=sunDiscDir(night,rig);
 for(let i=0;i<3;i++)assert.ok(Math.abs(disc.sunDir[i]-night.dir[i])<1e-6);
 assert.equal(disc.elevationDeg,rig.sunElevationDeg);
 assert.ok(disc.starAlpha>.5);
 assert.ok(disc.zenith[2]<.2);
 const dayDisc=sunDiscDir(day,lightRigFor(day));
 assert.equal(dayDisc.starAlpha,0);
 const tint=hazeTint(day.dir,day.sky.horizon,day.sky.zenith,0);
 assert.equal(tint.length,3);
});

test('Genesis adds no second light and lib/look has no Math.random',async()=>{
 const dir=new URL('../lib/look/',import.meta.url);
 for(const f of readdirSync(dir)){
  if(!/\.(ts|mjs|js)$/.test(f))continue;
  const s=readFileSync(new URL(f,dir),'utf8');
  assert.doesNotMatch(s,/Math\.random/,f);
  assert.doesNotMatch(s,/setInterval|setTimeout|Date\.now|performance\.now/,f);
  assert.doesNotMatch(s,/DirectionalLight|PointLight|SpotLight|HemisphereLight/,f);
 }
 const THREE=await import('three');
 const scene=new THREE.Scene();
 scene.add(new THREE.DirectionalLight());
 let world={seed:'s',tick:2};
 const before=structuredClone(world);
 const g=attachGenesisLook(THREE,scene,{
  seed:'s',tier:'LOW',heightAt:()=>Math.sin(0),
  getLook:()=>'park',reduced:()=>true,nowMs:()=>0,readTick:()=>world.tick,
  getSun:()=>({dir:[0,.7,.7],day:.2,elevationDeg:-12,sky:{zenith:[.01,.02,.05],horizon:[.05,.04,.08],starAlpha:.8}}),
 });
 const frame=g.sync();
 assert.equal(frame.reduced,true);
 assert.deepEqual(world,before);
 let lights=0;scene.traverse(o=>{if(o.isDirectionalLight)lights++;});
 assert.equal(lights,1);
 assert.equal(g.lightsAdded,0);
 assert.equal(g.creature.applied,false);
 assert.equal(scene.children[0].name,'genesis-anchor');
 g.dispose();
 const classic=new THREE.Object3D();classic.visible=false;
 const skyMark=new THREE.Object3D();skyMark.visible=true;
 const ground=attachGenesisLook(THREE,scene,{
  seed:'s',tier:'LOW',heightAt:()=>0,getLook:()=>'park',reduced:()=>true,nowMs:()=>0,readTick:()=>1,
  follow:()=>classic,classicRoots:()=>[classic,skyMark],
 });
 ground.sync();
 assert.equal(ground.group.visible,false);
 assert.equal(skyMark.visible,true);
 classic.visible=true;
 ground.sync();
 assert.equal(ground.group.visible,true);
 assert.equal(skyMark.visible,false);
 ground.dispose();
});

test('speckle sources in lib/universe stay untouched, and the page wiring keeps Classic, the 2D fallback and the frame',()=>{
 assert.equal(SPECKLE_STOP.stopped,true);
 for(const f of SPECKLE_STOP.files)assert.match(f,/^lib\/universe\//);
 const lw=read('components/living-world.tsx');
 assert.match(lw,/attachGenesisLook\(/);
 assert.match(lw,/data-lw-look="park"/);
 assert.doesNotMatch(lw,/nextLook|writeLook/);
 assert.match(lw,/SeededLand2D/);
 assert.match(lw,/setLand2d\(/);
 assert.match(lw,/FogExp2/);
 assert.match(lw,/const frame=\(\)=>\{os1=null;p2s=null;/);
 assert.match(lw,/Horizon layers · SEEDED/);
 assert.match(lw,/Motion · SIMULATED/);
 assert.match(lw,/presentationTier\(/);
 assert.match(lw,/onTier:/);
 assert.match(lw,/__lwSky/);
 assert.match(lw,/max-width:480px/);
 assert.doesNotMatch(read('components/cage-pocket-dimension.tsx'),/localStorage|fetch\(/);
 assert.match(read('components/cage-pocket-dimension.tsx'),/attachGenesisLook\(/);
 assert.doesNotMatch(read('components/universe-settings.tsx'),/data-look-choice/);
 assert.match(read('components/universe-settings.tsx'),/data-look-park/);
 assert.match(read('components/universe-settings.tsx'),/data-quality-choice/);
 assert.match(read('components/tiny-universe-view.tsx'),/SeededLand2D/);
 assert.doesNotMatch(read('lib/look/attach.ts'),/windSway|cloudDrift|treeSway|InstancedMesh|beastNode|travNode/);
 assert.match(read('lib/look/foliage.ts'),/windSway\(/);
 assert.match(read('lib/look/foliage.ts'),/treeSway\(/);
 assert.doesNotMatch(read('lib/look/foliage.ts'),/beastNode|travNode/);
});

test('grass and trees take the wind hooks and freeze when motion is reduced',async()=>{
 const THREE=await import('three');
 const grown=buildFoliage(THREE,{heightAt:()=>1,shoreAt:()=>0,tier:'LOW',seed:'meadow'});
 assert.ok(grown.counts.grass>0&&grown.counts.trees>0);
 const frame=motionAt('meadow',3,false);
 syncFoliage(grown,frame);
 assert.equal(grown.grass.material.uniforms.uPhase.value,frame.windPhase);
 assert.equal(grown.grass.material.uniforms.uAmp.value,frame.windAmp);
 assert.equal(grown.trees.material.uniforms.uLean.value,treeSway(frame));
 syncFoliage(grown,motionAt('meadow',9,true));
 assert.equal(grown.grass.material.uniforms.uAmp.value,0);
 assert.equal(grown.trees.material.uniforms.uLean.value,0);
});
