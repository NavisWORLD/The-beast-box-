import assert from 'node:assert/strict';
import {readFileSync,readdirSync,statSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const walk=d=>readdirSync(new URL('../'+d,import.meta.url)).flatMap(f=>{const p=d+'/'+f;return statSync(new URL('../'+p,import.meta.url)).isDirectory()?walk(p):[p];});
test('the menu uses one name per place',()=>{
 const nav=read('lib/site-nav.ts');
 for(const w of [/label:'Beast Cage'/,/label:'Adventure walk'/,/label:'Star field'/,/label:'Lost Cosmos Field'/,/label:'Guest model'/,/Workshop \(owner unlock\)/])assert.match(nav.replace('Lost COSMOS Field','Lost Cosmos Field'),w,String(w));
 assert.doesNotMatch(nav,/Pocket cage|Field game|label:'Try it'/);
});
test('no tab title still says COSMIC CHAOS or COSMOS Lab, and titles use the "· Beast Box" pattern',()=>{
 const pages=walk('app').filter(f=>/(page|layout)\.tsx$/.test(f));
 for(const f of pages){const s=read(f);const m=s.match(/title:\s*['"]([^'"]+)['"]/);if(!m||!/export const metadata/.test(s))continue;
  assert.doesNotMatch(m[1],/COSMIC CHAOS|COSMOS Lab|\/\/|BEAST BOX/,f+': '+m[1]);}
 assert.match(read('app/layout.tsx'),/title: 'Beast Box'/);
 assert.match(read('app/workspace/page.tsx'),/Workshop · Beast Box/);assert.match(read('app/try/layout.tsx'),/Guest model · Beast Box/);
 assert.match(read('app/beast-cage/go/page.tsx'),/Star field · Beast Box/);
});
test('the owner area is called Workshop in visible links',()=>{
 for(const f of ['app/page.tsx','app/sol-game/page.tsx','components/beast-cage-portal.tsx','components/universe-settings.tsx','components/beast-talk-panel.tsx'])assert.doesNotMatch(read(f).replace(/aria-label="Workstation"/g,''),/>Workstation|Workstation →|<strong>Workstation/,f);
 assert.doesNotMatch(read('components/studio.tsx'),/COSMIC CHAOS/);
});
test('/guest redirects to /beast-cage/guest',()=>{assert.match(read('next.config.ts'),/source: '\/guest', destination: '\/beast-cage\/guest'/);});
