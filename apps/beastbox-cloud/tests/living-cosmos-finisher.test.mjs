import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('talk page uses the shared room shell instead of one-off inline chrome',()=>{
 const s=r('app/beast-cage/talk/page.tsx');
 assert.match(s,/UniverseRoomShell/);
 assert.doesNotMatch(s,/minHeight:'100vh'/);
 assert.match(s,/JourneyLinks/);
 assert.match(r('components/universe-room-shell.tsx'),/UniverseRoomNav/);
});
test('talk scene captions are kid-friendly and centralized',()=>{
 const s=r('components/beast-talk-scene-caption.ts');
 assert.match(s,/Waiting for your message/);
 assert.match(s,/no made-up reply/);
 assert.doesNotMatch(s,/MODEL REQUEST PENDING/);
 assert.match(r('components/beast-cage-talk.tsx'),/SCENE_CAPTION/);
});
test('home exposes the full kid journey rail without page-level overflow',()=>{
 assert.match(r('app/page.tsx'),/KidJourneyRail/);
 const s=r('components/kid-journey-rail.module.css');
 assert.match(s,/overflow-x:auto/);
 assert.match(s,/min-height:44px/);
 const copy=r('lib/kid-journey-copy.ts');
 for(const step of ['Meet','Name','Play','Talk','Rest','Explore','Save'])assert.ok(copy.includes(step),step);
});
test('settings tucks cloud memory into an open-by-default disclosure',()=>{
 const s=r('components/universe-settings.tsx');
 assert.match(s,/SettingsFriendlyWrap/);
 assert.match(s,/CLOUD MEMORY \(OPTIONAL\)/);
 assert.match(r('components/settings-friendly-wrap.tsx'),/open=true/);
});
test('zeref true-3D stage keeps lifecycle, fallback, and cleanup contracts',()=>{
 const s=r('components/zeref-true3d.tsx');
 assert.match(s,/webglcontextlost/);
 assert.match(s,/cancelAnimationFrame/);
 assert.match(s,/disposeZerefRig/);
 assert.match(s,/ZerefMoonwraith/);
 assert.match(s,/data-graphics=\{ready&&!reduced&&!fallback\?'zeref-true3d':'zeref-illustration'\}/);
 assert.match(r('app/beast-cage/turntable/page.tsx'),/data-zeref-3d-toggle/);
});
test('provenance explainer mounts on growth surfaces without inventing receipts',()=>{
 assert.match(r('components/grow-in-cosmos.tsx'),/ProvenanceExplainer variant="growth"/);
 assert.match(r('components/grow-in-cosmos.tsx'),/ProvenanceExplainer variant="genesis"/);
 assert.doesNotMatch(r('lib/provenance-labels.mjs'),/Math\.random|Date\.now/);
});
