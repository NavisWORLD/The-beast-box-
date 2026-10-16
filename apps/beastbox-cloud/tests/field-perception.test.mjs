import test from 'node:test';import assert from 'node:assert/strict';
import {analyzeFrame,analyzeAudio,notice,experience,isNumericExperience} from '../lib/companion/field-perception.mjs';
test('frame brightness + motion',()=>{const w=4,h=2,a=new Uint8ClampedArray(w*h*4).fill(0),b=new Uint8ClampedArray(w*h*4).fill(255);
 const f0=analyzeFrame(a,null,w,h);assert.equal(f0.brightness,0);const f1=analyzeFrame(b,f0.gray,w,h);assert.equal(f1.brightness,1);assert.equal(f1.motion,1);});
test('audio loudness and pitch',()=>{const sr=8000,buf=new Float32Array(2048).map((_,i)=>.5*Math.sin(2*Math.PI*200*i/sr));const a=analyzeAudio(buf,sr);assert.ok(a.loudness>.5);assert.ok(Math.abs(a.pitchHz-200)<15);});
test('notice + numeric-only experience',()=>{assert.equal(notice({loudness:.9,motion:0,brightness:.5},{loudness:.1}).emotion,'fear');
 const e=experience({brightness:.5,motion:.1,image:'x'},1);assert.ok(isNumericExperience(e));assert.equal('image' in e,false);assert.equal(isNumericExperience({t:1,img:'x'}),false);});
