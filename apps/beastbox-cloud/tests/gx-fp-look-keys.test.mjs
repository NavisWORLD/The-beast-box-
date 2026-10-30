import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../lib/universe/fp-look-keys.ts',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
const M=await import(new URL('../lib/universe/fp-look-keys.ts',import.meta.url).href);
test('look keys are skipped while typing: input, textarea, select, contenteditable, talk box',()=>{
  for(const tag of ['INPUT','TEXTAREA','SELECT','input'])assert.equal(M.isTypingTarget({tagName:tag}),true,tag);
  assert.equal(M.isTypingTarget({tagName:'DIV',isContentEditable:true}),true);
  assert.equal(M.isTypingTarget({tagName:'SPAN',closest:(q)=>q.includes('role="textbox"')?{}:null}),true);
  assert.equal(M.isTypingTarget({tagName:'CANVAS',closest:()=>null}),false);
  assert.equal(M.isTypingTarget({tagName:'BODY',closest:()=>null}),false);
  assert.equal(M.isTypingTarget(null),false);
  assert.ok(/const kd=\(e:KeyboardEvent\)=>\{if\(isTypingTarget\(e\.target\)\)return;/.test(lw),'keydown guard runs before preventDefault');
});
test('Up looks up, Down looks down, Left/Right turn a visible step',()=>{
  assert.ok(M.fpLookKeyStep('ArrowUp').pitch>0);assert.ok(M.fpLookKeyStep('ArrowDown').pitch<0);
  assert.ok(M.fpLookKeyStep('PageUp').pitch>0);assert.ok(M.fpLookKeyStep('PageDown').pitch<0);
  assert.ok(M.fpLookKeyStep('ArrowLeft').yaw>=0.15);assert.ok(M.fpLookKeyStep('ArrowRight').yaw<=-0.15);
});
test('look keys bound page-wide, wheel tilts over HUD too, no Math.random',()=>{
  assert.ok(lw.includes("addEventListener('keydown',kd)"));assert.ok(lw.includes("addEventListener('wheel',wheelW,{passive:true})"));
  assert.ok(!/Math\.random/.test(src));
});
