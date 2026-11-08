// A viewport toggle that passes through 0×0 must not rebuild a framebuffer with a zero attachment.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {applyViewport,positiveSize} from '../lib/look/viewport.ts';

const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');

test('a resize to 0x0 and back never leaves a black frame',()=>{
 const calls=[];
 const buf={w:1280,h:800,pixels:'sky'};
 const remember=(name,w,h)=>{
  calls.push([name,w,h]);
  if(!(w>0)||!(h>0))buf.pixels='black';
  else {buf.w=w;buf.h=h;buf.pixels='lit';}
 };
 const renderer={setSize(w,h){remember('renderer',w,h);}};
 const composer={setSize(w,h){remember('composer',w,h);}};
 const target={setSize(w,h){remember('target',w,h);}};
 const camera={aspect:1,updateProjectionMatrix(){}};
 const parts=()=>({renderer,composers:[composer],targets:[target],camera});
 assert.equal(positiveSize(0,0),null);
 assert.equal(positiveSize(10,0),null);
 assert.equal(positiveSize(-1,20),null);
 assert.equal(applyViewport(0,0,parts()),false);
 assert.equal(calls.length,0);
 assert.equal(buf.pixels,'sky');
 assert.equal(applyViewport(1280,800,parts()),true);
 assert.equal(buf.pixels,'lit');
 assert.equal(applyViewport(0,0,parts()),false);
 assert.equal(buf.w,1280);
 assert.equal(buf.h,800);
 assert.equal(buf.pixels,'lit');
 assert.equal(applyViewport(393,852,parts()),true);
 assert.equal(buf.w,393);
 assert.equal(buf.h,852);
 assert.equal(buf.pixels,'lit');
 assert.equal(camera.aspect,393/852);
 for(const c of calls)assert.ok(c[1]>0&&c[2]>0,`setSize saw ${c.join(' ')}`);
 assert.ok(!calls.some(c=>c[1]===0||c[2]===0));
});

test('the living world defers a zero viewport and the composers refuse it',()=>{
 const lw=read('components/living-world.tsx');
 const post=read('lib/look/post.ts');
 const chain=read('lib/universe/post-chain-three.ts');
 const ascii=read('lib/universe/mechanics-three.ts');
 assert.match(lw,/applyViewport\(r\.width,r\.height/);
 assert.match(lw,/requestAnimationFrame\(\(\)=>\{resizePending=false;resize\(\);\}\)/);
 assert.doesNotMatch(lw,/renderer\.setSize\(r\.width/);
 assert.match(post,/positiveSize\(w,h\)/);
 assert.match(post,/if\(!s\)return/);
 assert.match(chain,/if\(!\(w>0\)\|\|!\(h>0\)\)return/);
 assert.match(ascii,/s\.x>0&&s\.y>0&&\(rt\.width/);
});
