import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {LAYERS,clampYaw,ctmToMatrix4,faceKey,depthPose,volumeFor,MAX_YAW_DEG} from '../lib/zeref/sprite-layers.mjs';
const src=readFileSync(new URL('../components/zeref-sprite-3d.tsx',import.meta.url),'utf8');
test('layers are cut from the real ZerefFigure sprite parts in back-to-front order',()=>{
 const parts=LAYERS.map(l=>l.part);for(const p of ['tail','wingL','wingR','body','pawL','pawR','earL','earR','head'])assert.ok(parts.includes(p),p);
 assert.ok(parts.indexOf('tail')<parts.indexOf('body')&&parts.indexOf('body')<parts.indexOf('head'));
 assert.match(src,/<ZerefFigure id=\{id\}\/>/);assert.match(src,/paintRig\(P,f,mind\.t\)/);assert.match(src,/XMLSerializer/);});
test('identity CTM maps the sprite exactly onto the plane (front == sprite)',()=>{
 assert.deepEqual(ctmToMatrix4({a:1,b:0,c:0,d:1,e:0,f:0}).map(v=>+v.toFixed(9)+0),[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
 const m=ctmToMatrix4({a:1,b:0,c:0,d:1,e:100,f:-50});assert.equal(m[12],1);assert.equal(m[13],.5);
 const mirror=ctmToMatrix4({a:-1,b:0,c:0,d:1,e:400,f:0});assert.equal(mirror[0],-1);assert.equal(mirror[12]+0,0);});
test('full 360° orbit; depth-only extras vanish at the front',()=>{
 assert.equal(MAX_YAW_DEG,180);assert.equal(clampYaw(270),-90);assert.equal(clampYaw(-190),170);
 const f=depthPose(0,3);assert.equal(f.shell,0);assert.equal(f.wingFold,0);assert.equal(f.rim,0);assert.ok(depthPose(90).shell>0.9);});
test('sculpted volumes fit inside each part bounds and sit behind the sprite face',()=>{
 const v=volumeFor('body',{x:100,y:250,width:200,height:120});assert.ok(v.rx<1&&v.ry<.6);assert.equal(volumeFor('wingL',{x:0,y:0,width:10,height:10}),null);
 assert.match(src,/L\.z-0\.04-vol\.rz/);assert.match(src,/THREE\.FrontSide/);assert.match(src,/THREE\.DoubleSide/);});
test('face texture is re-cut only when the expression changes',()=>{assert.equal(faceKey({lid:0,mouth:{}}),faceKey({lid:0.01,mouth:{}}));assert.notEqual(faceKey({lid:0}),faceKey({lid:1}));});
