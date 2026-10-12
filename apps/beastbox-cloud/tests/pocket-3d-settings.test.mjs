import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {POCKET_3D_KEY,DEFAULT_POCKET_3D,normalizePocket3D,readPocket3D,savePocket3D} from '../lib/companion/pocket-3d-settings.mjs';
const root=new URL('../',import.meta.url);
const source=(file)=>readFileSync(new URL(file,root),'utf8');
const storage=()=>{
 const records=new Map();return {
  getItem:key=>records.get(key)??null,
  setItem:(key,value)=>records.set(key,value),
  raw:records
 };
};
test('3D settings fail closed to visual defaults when storage is absent, corrupt, or inaccessible',()=>{
 const local=storage();
 assert.deepEqual(readPocket3D(local),DEFAULT_POCKET_3D);
 local.raw.set(POCKET_3D_KEY,'not-json');
 assert.deepEqual(readPocket3D(local),DEFAULT_POCKET_3D);
 local.raw.set(POCKET_3D_KEY,JSON.stringify({enabled:'false',quality:'ultra',qbeast_id:'changed'}));
 assert.deepEqual(readPocket3D(local),DEFAULT_POCKET_3D);
 assert.deepEqual(readPocket3D({getItem(){throw Error('private storage')}}),DEFAULT_POCKET_3D);
});
test('quality and visibility persist only typed, allowlisted 3D fields',()=>{
 const local=storage();
 const saved=savePocket3D(local,{enabled:false,quality:'low',battery:'forged',model:'overridden'});
 assert.deepEqual(saved,{enabled:false,quality:'low'});
 assert.deepEqual(readPocket3D(local),saved);
 assert.deepEqual(normalizePocket3D({enabled:true,quality:'high'}),{enabled:true,quality:'high'});
 assert.deepEqual(JSON.parse(local.raw.get(POCKET_3D_KEY)),saved);
});
test('site settings and original Cage renderer use one presentation-only preference contract',()=>{
 const settings=source('components/universe-settings.tsx');
 const pocket=source('components/cage-pocket-dimension.tsx');
 const cage=source('components/beast-cage-portal.tsx');
 assert.match(settings,/savePocket3D/);
 assert.match(settings,/Three.js pocket/);
 assert.match(pocket,/readPocket3D/);
 assert.match(pocket,/webglcontextlost/);
 assert.match(pocket,/renderer\.render\(scene,camera\)/);
 assert.match(cage,/POCKET_3D_CAMERA_RESET/);
 assert.doesNotMatch(source('lib/companion/pocket-3d-settings.mjs'),/fetch\(|model\.safetensors|beastbox-companion-session-v1/);
});
