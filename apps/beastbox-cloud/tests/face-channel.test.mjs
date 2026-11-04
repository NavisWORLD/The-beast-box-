import test from 'node:test';import assert from 'node:assert/strict';
import {faceProxies,FACE_KEYS} from '../lib/companion/face-channel.mjs';
import {FacePulse} from '../lib/bio/face-pulse.mjs';
import {buildFaceEstimates,validateFaceEstimates} from '../lib/bio/face-estimates.mjs';
import {experience,isNumericExperience} from '../lib/companion/field-perception.mjs';
const W=32,H=24;
function frame(paint){const px=new Uint8ClampedArray(W*H*4);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const [r,g,b]=paint(x,y);const i=(y*W+x)*4;px[i]=r;px[i+1]=g;px[i+2]=b;px[i+3]=255;}return px;}
const SKIN=[198,140,105],WALL=[70,80,120];
test('skin region reads as a present face with scale and centroid; plain wall does not',()=>{
 const withFace=faceProxies(frame((x,y)=>x>=10&&x<22&&y>=5&&y<19?SKIN:WALL),W,H);
 assert.equal(withFace.facePresent,1);assert.ok(withFace.faceScale>0.15&&withFace.faceScale<0.3);
 assert.ok(Math.abs(withFace.faceX)<0.2&&Math.abs(withFace.faceY)<0.2);
 assert.ok(withFace.faceGreen>100);
 const wall=faceProxies(frame(()=>WALL),W,H);
 assert.equal(wall.facePresent,0);assert.equal(wall.faceGreen,0);
 for(const k of FACE_KEYS)assert.ok(k in withFace);
});
test('blink is a change measure against the previous eye level',()=>{
 const px=frame((x,y)=>x>=10&&x<22&&y>=5&&y<19?SKIN:WALL);
 const a=faceProxies(px,W,H);const b=faceProxies(px,W,H,a.eye);
 assert.equal(b.faceBlink,0);
 const darker=faceProxies(frame((x,y)=>x>=10&&x<22&&y>=5&&y<19?[120,84,63]:[40,46,70]),W,H,a.eye);
 assert.ok(darker.faceBlink>0);
});
test('face pulse recovers a synthetic 72bpm green oscillation, and stays null on noise',()=>{
 const pulse=new FacePulse();const t0=100000;
 for(let i=0;i<300;i++){const t=t0+i*100;pulse.push(t,120+10*Math.sin(2*Math.PI*1.2*(t-t0)/1000));}
 const est=pulse.estimate();assert.ok(est,`expected an estimate, got null`);
 assert.ok(Math.abs(est.bpm-72)<=6,`bpm ${est.bpm}`);
 const noise=new FacePulse();let s=7;const rnd=()=>{s=(s*16807)%2147483647;return s/2147483647;};
 for(let i=0;i<300;i++)noise.push(t0+i*100,110+rnd()*30);
 const nest=noise.estimate();assert.ok(nest===null||nest.sqi<0.9);
});
test('estimates record is labelled ESTIMATE and validates; the sealed packet is untouched',()=>{
 const est=buildFaceEstimates({face:{facePresent:1,faceScale:0.22,faceX:0.05,faceY:-0.1,faceBlink:0.3},pulse:{bpm:71.6,sqi:0.55}});
 assert.equal(est.heartbeat_label,'ESTIMATE');assert.equal(est.pulse.bpm,72);
 assert.deepEqual(validateFaceEstimates(est),{ok:true,errors:[]});
 const bad={...est,heartbeat_label:'MEASURED'};assert.equal(validateFaceEstimates(bad).ok,false);
});
test('experience records carry face keys only when present; old records still validate',()=>{
 const base={brightness:.5,hue:10,motion:.1,gazeX:0,gazeY:0,loudness:.2,pitchHz:220};
 const plain=experience(base,1000);assert.ok(!('facePresent' in plain));assert.ok(isNumericExperience(plain));
 const faced=experience({...base,facePresent:1,faceScale:.22,faceX:.05,faceY:-.1,faceBlink:.3},1000);
 assert.equal(faced.facePresent,1);assert.ok(isNumericExperience(faced));
});
