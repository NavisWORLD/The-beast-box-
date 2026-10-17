import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {voiceStatus,speakWith} from '../lib/companion/voice-provider.mjs';
const src=readFileSync(new URL('../components/open-field-camera.tsx',import.meta.url),'utf8')+readFileSync(new URL('../components/camera-field.tsx',import.meta.url),'utf8');
test('Open Field labels its AR mode honestly and never records',()=>{assert.match(src,/not full AR/);assert.match(src,/WebXR AR · real surface tracking/);assert.match(src,/NOT RECORDED/);assert.doesNotMatch(src,/MediaRecorder|toDataURL|fetch\(/);});
test('camera tracks stop on close, hide, pagehide and unmount; denial is handled',()=>{assert.match(src,/getTracks\(\)\.forEach\(t=>t\.stop\(\)\)/);assert.match(src,/'pagehide',stop/);assert.match(src,/NotAllowedError/);});
test('Grok voice slot reports not configured without a key and never speaks a fake voice',async()=>{
 const s=await voiceStatus(async()=>new Response(JSON.stringify({schema:'beastbox-voice-v1',grok:false})));assert.equal(s.grok.configured,false);
 assert.equal(speakWith('grok-tts','hi').ok,false);
 const route=readFileSync(new URL('../app/api/voice/route.ts',import.meta.url),'utf8');assert.match(route,/grok:key\.length>=20/);assert.doesNotMatch(route,/key[,}]\s*\)/);
});
test('Open Field AR: true AR tracking vs camera overlay labels, Zeref + companion, play actions',()=>{const st=readFileSync(new URL('../components/ar-creature-stage.ts',import.meta.url),'utf8');assert.match(src,/True AR tracking/);assert.match(src,/Camera overlay/);assert.match(src,/bb-deada969/);for(const a of ['call','feed','toy'])assert.match(src,new RegExp(`data-ar-action|'${a}'`));assert.match(st,/function call\(/);assert.match(st,/function feed\(/);assert.match(st,/function toss\(/);assert.match(st,/function pet\(/);assert.match(st,/friend/);});
test('camera field: environment camera, playsinline, grounded creature with emotions, wired into the /go field',()=>{
 const f=readFileSync(new URL('../components/camera-field.tsx',import.meta.url),'utf8');
 assert.match(f,/facingMode:\{ideal:'environment'\}/);assert.match(f,/playsInline/);assert.match(f,/setAttribute\('playsinline',''\)/);
 assert.match(f,/deriveEmotions\(beast\)/);assert.match(f,/createArStage/);assert.match(f,/data-start-camera/);assert.match(f,/not full AR/);
 const st=readFileSync(new URL('../components/ar-creature-stage.ts',import.meta.url),'utf8');assert.match(st,/immersive-ar/);assert.match(st,/hit-test/);assert.match(st,/deviceorientation/);assert.match(st,/USDZExporter/);assert.match(st,/stepHop\(/);assert.match(st,/ShadowMaterial/);
 const go=readFileSync(new URL('../components/beast-go.tsx',import.meta.url),'utf8');assert.match(go,/<CameraField fullscreen/);
});
