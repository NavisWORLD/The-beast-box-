// Camera modes are a view-local presentation. Switching them must not change the shared world.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {VIEW_MODE_KEY} from '../lib/world/view-mode.mjs';
import {CAMERA_SWITCH_ORDER,presentationCamera,stepPresentationCamera} from '../lib/world/camera-presentation.mjs';
import {viewChipLabel} from '../lib/world/view-mode.mjs';

const read=()=>({
 traveler:{n:{x:1,y:0,z:0},f:{x:0,y:0,z:1},position:{x:8.2,y:0,z:0}},
 beast:{n:{x:0,y:1,z:0},f:{x:1,y:0,z:0},position:{x:0,y:8.4,z:0}},
 radius:8,
 ground:.2,
});
const world=()=>({
 traveler:read().traveler,
 beast:read().beast,
 clock:{tick:41,seed:'ibm-seed',paused:false,running:true},
 universe:{tick:41,seed:'ibm-seed',schema:3,storms:[{id:'s1'}],life:[{id:'beast'}]},
});
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
const len=p=>Math.hypot(p.x,p.y,p.z);

test('no mode leaves the camera on the default path',()=>{
 const src=read();
 const before=structuredClone(src);
 assert.equal(presentationCamera(null,src),null);
 assert.equal(presentationCamera(undefined,src),null);
 assert.equal(presentationCamera('',src),null);
 assert.equal(presentationCamera('nope',src),null);
 assert.deepEqual(src,before);
 const cam={mode:'engine',position:{x:3,y:4,z:5},up:{x:0,y:1,z:0},lookAt:{x:0,y:0,z:1}};
 const frozen=structuredClone(cam);
 assert.equal(stepPresentationCamera(cam,null,{reduced:false,alpha:.5}),null);
 assert.deepEqual(cam,frozen);
});

test('Orbit, Behind and First person read the world and write nothing back',()=>{
 const state=world();
 const before=structuredClone(state);
 const storage=mem();
 storage.setItem(VIEW_MODE_KEY,'behind');
 storage.setItem('lw:universe',JSON.stringify(state.universe));
 storage.setItem('lw:trav:beast',JSON.stringify(state.traveler));
 const view={mode:null,camera:null};
 assert.deepEqual([...CAMERA_SWITCH_ORDER],['orbit','behind','first']);
 for(const mode of CAMERA_SWITCH_ORDER){
  view.mode=mode;
  view.camera=presentationCamera(mode,{traveler:state.traveler,beast:state.beast,radius:8,ground:.2});
  assert.equal(view.camera.mode,mode);
  for(const p of [view.camera.position,view.camera.up,view.camera.lookAt])for(const k of ['x','y','z'])assert.equal(Number.isFinite(p[k]),true);
  assert.deepEqual(state,before,'traveler, beast, clock and universe stay identical');
  assert.equal(storage.getItem(VIEW_MODE_KEY),'behind','the presentation mode is not persisted');
  assert.equal(storage.getItem('lw:universe'),JSON.stringify(before.universe));
  assert.equal(storage.getItem('lw:trav:beast'),JSON.stringify(before.traveler));
  assert.equal(viewChipLabel(mode,'Duskscale',true),mode==='behind'?'View: Behind Duskscale':mode==='orbit'?'View: Orbit':'View: First person');
 }
 const poses=CAMERA_SWITCH_ORDER.map(m=>presentationCamera(m,read()));
 assert.notDeepEqual(poses[0].position,poses[1].position);
 assert.notDeepEqual(poses[1].position,poses[2].position);
 assert.ok(Math.abs(len(poses[0].position)-8*4.3)<1e-6,'orbit stands off at the existing planet multiple');
 assert.ok(len(poses[2].position)>7&&len(poses[2].position)<12,'first person stays at the traveler eye');
 assert.ok(poses[1].position.y>8,'behind sits just off the beast');
});

test('inputs are not mutated, and reduced motion snaps',()=>{
 const src=read();
 const frozen=structuredClone(src);
 for(const mode of CAMERA_SWITCH_ORDER)presentationCamera(mode,src);
 assert.deepEqual(src,frozen);
 const pose=presentationCamera('behind',src);
 const prev={mode:'behind',position:{x:0,y:10,z:-3},up:{x:0,y:1,z:0},lookAt:{x:0,y:8,z:0}};
 const prevCopy=structuredClone(prev);
 const poseCopy=structuredClone(pose);
 const eased=stepPresentationCamera(prev,pose,{reduced:false,alpha:.5});
 assert.deepEqual(prev,prevCopy);
 assert.deepEqual(pose,poseCopy);
 assert.ok(Math.abs(eased.position.y-((prev.position.y+pose.position.y)/2))<1e-9);
 const snapped=stepPresentationCamera(prev,pose,{reduced:true,alpha:.25});
 assert.deepEqual(snapped.position,pose.position);
 assert.deepEqual(snapped.lookAt,pose.lookAt);
 const jumped=stepPresentationCamera(prev,presentationCamera('first',src),{reduced:false,alpha:.2});
 assert.deepEqual(jumped.position,presentationCamera('first',src).position,'a mode change snaps instead of flying through the planet');
});

test('the living world applies the pose only to the THREE camera',()=>{
 const lw=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 const css=fs.readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
 const mod=fs.readFileSync(new URL('../lib/world/camera-presentation.mjs',import.meta.url),'utf8');
 assert.match(lw,/useState<string\|null>\(null\)/);
 assert.match(lw,/camModeRef\.current=camMode/);
 assert.match(lw,/viewChipLabel\(camMode,beastName,true\)/);
 assert.match(lw,/viewChipLabel\(m,beastName,true\)/);
 assert.match(lw,/viewChipLabel\(viewMode,beastName,spawned\)/);
 assert.match(lw,/data-lw-view=\{viewMode\}/);
 assert.match(lw,/viewModeCamera\(viewRef\.current\)/);
 assert.match(lw,/camera\.position\.copy\(camPos\)/);
 const i=lw.indexOf('presentationCamera(cm,');
 assert.ok(i>0);
 const seg=lw.slice(i,lw.indexOf('if(post&&!asciiRef.current)',i));
 assert.match(seg,/camera\.position\.set\(next\.position/);
 assert.match(seg,/camera\.lookAt\(next\.lookAt/);
 assert.match(seg,/reduced:reducedNow\(\)/);
 assert.doesNotMatch(seg,/pN\.(copy|set|fromArray|normalize)|bN\.(copy|set|fromArray|normalize)|localStorage|sessionStorage|writeViewMode|setSpawned|__lw|grow\(|oneWorldClock|setItem\(/);
 assert.match(lw,/setCamMode\(cur=>cur===m\?null:m\)/);
 const ui=lw.slice(lw.indexOf('data-lw-cam-switch'),lw.indexOf('data-lw-view-chips'));
 assert.doesNotMatch(ui,/localStorage|sessionStorage|writeViewMode|__lw/);
 assert.match(css,/@container \(max-width:420px\)/);
 assert.match(css,/\[data-lw-cam-switch\]\{width:min\(210px,calc\(50cqw - 12px\)\)/);
 assert.match(css,/\[data-lw-view-chips\]\{max-width:min\(168px,46cqw\)/);
 assert.match(lw,/--lw-line-top:calc\(env\(safe-area-inset-top\) \+ 230px\)/);
 const code=mod.split('\n').filter(l=>!l.trim().startsWith('//')&&!l.trim().startsWith('*')&&!l.trim().startsWith('/*')).join('\n');
 assert.doesNotMatch(code,/Math\.random|localStorage|sessionStorage|__lw|window|globalThis/);
});
