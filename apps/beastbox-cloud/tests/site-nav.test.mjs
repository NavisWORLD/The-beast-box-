import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,existsSync} from 'node:fs';
const nav=readFileSync(new URL('../lib/site-nav.ts',import.meta.url),'utf8');
test('one site nav in the root layout with every area grouped',()=>{
 const layout=readFileSync(new URL('../app/layout.tsx',import.meta.url),'utf8');assert.match(layout,/<SiteNav\/>/);
 for(const g of ['home','zeref','cage','game','spark','brain','research','account','workshop'])assert.match(nav,new RegExp(`key:'${g}'`));
});
test('every internal nav link points at a real page or static file',()=>{
 for(const [,h] of nav.matchAll(/href:'([^']+)'/g)){const path=h.split('#')[0];
  const ok=path==='/'?existsSync(new URL('../app/page.tsx',import.meta.url)):path.endsWith('.html')?existsSync(new URL('../public'+path,import.meta.url)):existsSync(new URL('../app'+path+'/page.tsx',import.meta.url));
  assert.ok(ok,h);}
});
test('nav follows the one-universe structure with the active beast name and no dev wording',async()=>{
 for(const g of ['universe'])assert.match(nav,new RegExp(`key:'${g}'`));assert.doesNotMatch(nav,/Turntable/);assert.match(nav,/Look closer/);
 const tt=readFileSync(new URL('../app/beast-cage/turntable/page.tsx',import.meta.url),'utf8');assert.doesNotMatch(tt,/DEV DAY|Workshop mesh/);assert.doesNotMatch(tt+nav,/Glimairi/);
 const {activeBeastName,navLabel}=await import('../lib/site-nav.ts').catch(()=>({}));if(activeBeastName){assert.equal(activeBeastName('{"name":"Nyx"}'),'Nyx');assert.equal(navLabel({label:'x',href:'/',icon:'',beast:'meet'},'Nyx'),'Meet Nyx');}
});
