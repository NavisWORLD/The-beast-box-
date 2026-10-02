import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import ts from 'typescript';
const text=readFileSync(new URL('../lib/companion-roaming.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2020}}).outputText;
const {rectanglesIntersect,selectSafeRoamSpot}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
test('rectangles detect exact control-area overlap',()=>{
 const a={left:20,top:20,width:65,height:65};
 assert.equal(rectanglesIntersect(a,{left:35,top:35,width:40,height:40}),true);
 assert.equal(rectanglesIntersect(a,{left:260,top:200,width:20,height:20}),false);
 assert.equal(rectanglesIntersect(a,{left:NaN,top:0,width:20,height:20}),true);
});
test('bounded 320 through desktop movement avoids user controls',()=>{
 for(const width of [320,375,390,430,1440]){
  const height=width===1440?900:760,restricted=[
   {left:10,top:10,width:width-20,height:145},
   {left:10,top:260,width:width-20,height:115},
   {left:10,top:height-65,width:width-20,height:65}
  ];
  const candidate=selectSafeRoamSpot(width,height,restricted,0);
  if(candidate){
   assert.ok(candidate.left>=0&&candidate.left+candidate.width<=width);
   assert.ok(candidate.top>=0&&candidate.top+candidate.height<=height);
   for(const blocked of restricted)assert.equal(rectanglesIntersect(candidate,blocked),false);
   assert.deepEqual(candidate,selectSafeRoamSpot(width,height,restricted,0));
  }
 }
});
test('no invented safe perch when visible UI occupies the screen',()=>{
 const all={left:0,top:0,width:500,height:800};
 assert.equal(selectSafeRoamSpot(500,800,[all],0),null);
 assert.equal(selectSafeRoamSpot(310,800,[],0),null);
 assert.equal(selectSafeRoamSpot(500,800,[],-1),null);
});
test('different bounded ticks rotate only between allowed spots',()=>{
 const candidates=Array.from({length:14},(_,i)=>selectSafeRoamSpot(1440,900,[],i));
 assert.ok(new Set(candidates.map(c=>c?.id)).size>2);
});
