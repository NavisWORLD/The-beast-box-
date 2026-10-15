import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {voiceStatus,speakWith} from '../lib/companion/voice-provider.mjs';
const src=readFileSync(new URL('../components/open-field-camera.tsx',import.meta.url),'utf8')+readFileSync(new URL('../components/camera-field.tsx',import.meta.url),'utf8');
test('Open Field is honestly labelled not-AR and never records',()=>{assert.match(src,/not AR \(no tracking or surface detection\)/);assert.match(src,/NOT RECORDED/);assert.doesNotMatch(src,/MediaRecorder|toDataURL|fetch\(/);});
test('camera tracks stop on close, hide, pagehide and unmount; denial is handled',()=>{assert.match(src,/getTracks\(\)\.forEach\(t=>t\.stop\(\)\)/);assert.match(src,/'pagehide',stop/);assert.match(src,/NotAllowedError/);});
test('Grok voice slot reports not configured without a key and never speaks a fake voice',async()=>{
 const s=await voiceStatus(async()=>new Response(JSON.stringify({schema:'beastbox-voice-v1',grok:false})));assert.equal(s.grok.configured,false);
 assert.equal(speakWith('grok-tts','hi').ok,false);
 const route=readFileSync(new URL('../app/api/voice/route.ts',import.meta.url),'utf8');assert.match(route,/grok:key\.length>=20/);assert.doesNotMatch(route,/key[,}]\s*\)/);
});
test('camera field: environment camera, playsinline, grounded creature with emotions, wired into the /go field',()=>{
 const f=readFileSync(new URL('../components/camera-field.tsx',import.meta.url),'utf8');
 assert.match(f,/facingMode:\{ideal:'environment'\}/);assert.match(f,/playsInline/);assert.match(f,/setAttribute\('playsinline',''\)/);
 assert.match(f,/deriveEmotions\(beast\)/);assert.match(f,/stepActor\(/);assert.match(f,/data-start-camera/);assert.match(f,/not AR/);
 const go=readFileSync(new URL('../components/beast-go.tsx',import.meta.url),'utf8');assert.match(go,/<CameraField fullscreen/);
});
