import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('home cleanup folds (never deletes): hero Talk into Quick buttons, caption + LIVE chip into How this look is made',()=>{
 const p=r('app/page.tsx');
 assert.match(p,/<details className="home-quick" data-home-quick><summary>Quick buttons<\/summary>/);
 const q=p.indexOf('data-home-quick'),t=p.indexOf('data-talk-entry');assert.ok(q>0&&t>q,'talk link lives inside Quick buttons');
 assert.match(p,/href="\/beast-cage\/talk"/);assert.match(p,/data-home-open-world/);
 assert.match(p,/<summary>How this look is made<\/summary>/);
 for(const k of ['IBM seed RECORDED · growth SIMULATED','Clock: CST · SEEDED sun','Water, wind and motion · SIMULATED','Your own little universe · visual preview'])assert.ok(p.includes(k),k);
 assert.doesNotMatch(p,/\bAI\b|Math\.random/);
 assert.match(r('app/globals.css'),/\.home-pocket-layer \[class\*=cage-pocket-dimension\]\[class\*=__live\]\{display:none!important\}/);
});
