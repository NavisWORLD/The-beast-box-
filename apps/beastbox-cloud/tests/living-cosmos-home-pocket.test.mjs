import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('home renders the Cage pocket view-only from the saved Beast state, no new identity',()=>{
 const h=r('components/home-pocket.tsx');assert.match(r('app/page.tsx'),/<HomePocket\/>/);
 assert.match(h,/CagePocketDimension/);assert.match(h,/visualStateFromBeast\(beast\)/);assert.doesNotMatch(h,/bb-deada969|bb-7f9c2a03|quantumSeed|receipt/);
 assert.match(r('app/globals.css'),/\.home-pocket-layer>\*\{pointer-events:none!important\}/);});
test('home 3D toggles stay reachable inside a View menu',()=>{const s=r('components/homepage-creature.tsx');
 assert.match(s,/<details className="cosmos-home-viewmenu">/);for(const k of ['3D model','Rotate 360°','Front','Side','Back','My Beast'])assert.ok(s.includes(k),k);});
test('bridge keeps PLAY prominent and tucks technical controls into Advanced settings',()=>{const s=r('components/quantum-beast-transfer.tsx');
 const adv=s.indexOf('Advanced settings');assert.ok(adv>0);assert.ok(s.indexOf('PLAY THIS BEAST IN LOST COSMOS')<adv);
 for(const k of ['DOWNLOAD QUANTUM BEAST','IMPORT QUANTUM BEAST','Lineage','Verify a trusted publisher','Quantum-inspired game identity'])assert.ok(s.indexOf(k)>adv,k);});
