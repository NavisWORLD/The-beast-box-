import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('old names are gone from visible text and aria-labels (Oct 26 sweep, Emeth live check)',()=>{
 const gone={'app/page.tsx':[/own Spark Beast/],'components/gba-guest-lab.tsx':[/\/\/ GAME LAB/,/Lost Cosmos field/,/same Spark Beast/,/Spark Beast game companion/,/owner workstation/],
  'components/beast-go.tsx':[/Lost Cosmos field</],'components/cosmic-companion-dock.tsx':[/Pet dragon Spark Beast/,/owner workstation/],'components/companion-provider.tsx':[/pet dragon Spark Beast/],
  'components/spark-wanderer.tsx':[/Spark Beast wandering/],'components/spark-beast-companion.tsx':[/label='Spark Beast companion'/],
  'components/beast-cage-portal.tsx':[/Active Spark Beast companion/,/Customizable Spark Beast preview/,/original Spark Beast;/,/owner workstation/],
  'components/brain-bay-workshop.tsx':[/Open owner workstation/],'app/try/page.tsx':[/owner workstation/],'components/universe-settings.tsx':[/[Oo]wner workstation/],
  'components/zeref-diary-panel.tsx':[/since recorded tick/,/last recorded tick/],'components/tiny-universe-view.tsx':[/Hearth/]};
 for(const [f,res] of Object.entries(gone)){const s=r(f);for(const re of res)assert.doesNotMatch(s,re,f+' '+re);}
 assert.match(r('components/gba-guest-lab.tsx'),/THE LITTLE BEAST · CATCH A STAR/);assert.match(r('components/gba-guest-lab.tsx'),/Lost COSMOS Field/);
 assert.match(r('components/zeref-diary-panel.tsx'),/since diary tick/);assert.match(r('components/zeref-diary-panel.tsx'),/LIVE · SIMULATED/);
 assert.match(r('components/brain-bay-workshop.tsx'),/Open the owner Workshop/);assert.match(r('components/tiny-universe-view.tsx'),/Threads SIMULATED</);
});
test('the unnamed life world is not given a final name on /universe',()=>{assert.doesNotMatch(r('components/tiny-universe-view.tsx'),/'Hearth'|· Hearth/);});

test('end-game wording: guest eyebrow, game-lab link, sol-game and Beast Go no longer say GAME LAB / GBA Game Lab / Spark Beast; research card has no Moonwraith line',()=>{
 const r=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
 assert.doesNotMatch(r('components/gba-guest-lab.tsx'),/GAME LAB/);
 assert.doesNotMatch(r('components/beast-cage-portal.tsx'),/GBA Game Lab|Take this creature/);
 assert.match(r('components/beast-cage-portal.tsx'),/Take \{creatureName\} to the game lab ↗/);
 for(const f of ['app/sol-game/page.tsx','components/sol-spark-player.tsx','components/beast-go.tsx'])assert.doesNotMatch(r(f),/Spark Beast/,f);
 assert.match(r('app/sol-game/page.tsx'),/title:'LOST COSMOS · Your Beast'/);
 assert.doesNotMatch(r('components/zeref-research-card.tsx'),/Moonwraith/);
 assert.match(r('components/zeref-research-card.tsx'),/Zeref's display form <code>/);
 for(const f of ['tests/player-shell.cjs','tests/genesis_3d_browser.py'])assert.doesNotMatch(r(f),/Spark Beast|GBA Game Lab/,f);
});
