import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,existsSync} from 'node:fs';
import {PIECES,pieceForPath,worldHere,neighborsOf,journeyStep,pieceIndex,WORLD_LABELS} from '../lib/world/world-map.mjs';
import {VIEW_OPTIONS,CONTEXTS,SHARED_LABELS,normalizeView,readView,writeView,pixelFlagForView,viewForPixelFlag,overlayFor,menuModel,viewOptionsFor,MENU_SECTIONS,VIEW_STORAGE} from '../lib/world/world-options.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const stripC=s=>s.replace(/\/\*[\s\S]*?\*\//g,'').replace(/^\s*\/\/.*$/gm,'');
const routeExists=h=>{const p=h.split(/[#?]/)[0];return p==='/'?existsSync(new URL('../app/page.tsx',import.meta.url)):p.endsWith('.html')?existsSync(new URL('../public'+p,import.meta.url)):existsSync(new URL('../app'+p+'/page.tsx',import.meta.url));};

test('the world map is one connected universe of real pages with friendly names',()=>{
 assert.equal(PIECES.length,7);
 const keys=new Set(PIECES.map(p=>p.key));
 for(const p of PIECES){assert.ok(routeExists(p.href),p.href);assert.doesNotMatch(p.name+p.short+p.role,/bb-[0-9a-f]{6}|\b[0-9a-f]{8,}\b|_/);
  assert.ok(p.neighbors.length>=2&&p.neighbors.every(k=>keys.has(k)&&k!==p.key),p.key);
  for(const k of p.neighbors)assert.ok(neighborsOf(k).some(n=>n.key===p.key),`${p.key} <-> ${k} must be mutual`);}
 // connected: every piece reachable from home through neighbours
 const seen=new Set(['home']);const q=['home'];while(q.length){const k=q.pop();for(const n of neighborsOf(k))if(!seen.has(n.key)){seen.add(n.key);q.push(n.key);}}
 assert.equal(seen.size,PIECES.length);
});
test('every route on the site menu belongs to a piece, so every page highlights somewhere on the map',()=>{
 for(const [,h] of read('lib/site-nav.ts').matchAll(/href:'([^']+)'/g)){if(h.endsWith('.html'))continue;assert.ok(pieceForPath(h),h);}
 assert.equal(pieceForPath('/').piece.key,'home');
 assert.equal(pieceForPath('/beast-cage/world').piece.key,'tiny');
 assert.equal(pieceForPath('/beast-cage/play').piece.key,'cage');
 assert.equal(pieceForPath('/beast-cage/field').piece.key,'field');
 assert.equal(pieceForPath('/sol-game').piece.key,'game');
 assert.equal(pieceForPath('/workspace?owner=1').piece.key,'workshop');
 assert.equal(pieceForPath('/brain-bay').sub,'Brain Bay');
 assert.equal(pieceForPath('/nope'),null);
});
test('prev/next arrows wrap and never dead-end',()=>{
 for(const p of PIECES){const h=worldHere(p.href);assert.equal(h.piece.key,p.key);assert.equal(h.index,pieceIndex(p.key)+1);assert.ok(h.prev&&h.next&&h.prev.key!==p.key);}
 assert.equal(journeyStep('workshop',1).key,'home');assert.equal(journeyStep('home',-1).key,'workshop');
 assert.match(WORLD_LABELS.honesty,/SEEDED.*SIMULATED.*RECORDED/);
});
test('one shared view state: same options, saved choice, pixel flag and overlay rule for every page',()=>{
 assert.deepEqual(VIEW_OPTIONS.map(o=>o.label),['Living world','Pocket explorer','Classic pixel sprite']);
 assert.equal(SHARED_LABELS.reset,'Reset 3D camera');assert.equal(SHARED_LABELS.diary('Zeref-Nightcat-Dragon'),'Zeref-Nightcat-Dragon’s Diary');
 assert.deepEqual(viewOptionsFor({hasBeast:false}).map(o=>o.id),['pocket','classic']);
 assert.equal(normalizeView('world',{hasBeast:false}),'pocket');assert.equal(normalizeView('world',{hasBeast:true}),'world');
 assert.equal(normalizeView('junk',{hasBeast:true}),'world');assert.equal(normalizeView(null,{hasBeast:false}),'pocket');
 const mem=new Map();const st={getItem:k=>mem.get(k)??null,setItem:(k,v)=>mem.set(k,v)};
 assert.equal(readView(st,{hasBeast:true}),'world');assert.ok(writeView(st,'classic'));assert.equal(mem.get(VIEW_STORAGE),'classic');
 assert.equal(readView(st,{hasBeast:false}),'classic');assert.equal(writeView(st,'bogus'),false);
 assert.equal(pixelFlagForView('classic'),true);assert.equal(pixelFlagForView('world'),false);
 assert.equal(viewForPixelFlag(true,'world'),'classic');assert.equal(viewForPixelFlag(false,'classic'),'pocket');assert.equal(viewForPixelFlag(false,'world'),'world');
});
test('the 2D sprite is never an overlay unless Classic was chosen',()=>{
 assert.equal(overlayFor('world',{rigAvailable:true}),'none');assert.equal(overlayFor('world',{rigAvailable:false}),'none');
 assert.equal(overlayFor('pocket',{rigAvailable:false}),'none');assert.equal(overlayFor('pocket',{rigAvailable:true}),'rig');
 assert.equal(overlayFor('classic',{rigAvailable:true}),'sprite');
});
test('home and cage share one menu model but frame it for their own page',()=>{
 const h=menuModel('home',{hasBeast:true,beastName:'Nyx'}),c=menuModel('cage',{hasBeast:true,beastName:'Nyx'});
 assert.notEqual(h.ctx.title,c.ctx.title);assert.match(h.ctx.title,/Pocket universe/);assert.match(c.ctx.title,/Habitat/);
 assert.equal(h.reset.label,c.reset.label);assert.equal(h.diary.label,c.diary.label);assert.equal(h.diary.label,'Nyx’s Diary');
 assert.equal(c.diary.href,'#zeref-diary');assert.equal(h.diary.href,'/beast-cage#zeref-diary');
 assert.deepEqual([...MENU_SECTIONS],['view','place','tools','diary','senses','about']);
 assert.ok(CONTEXTS.home&&CONTEXTS.cage);assert.match(c.senses.note,/only when you tap/);
});
test('cage and home use ONE menu: no sprite overlay by default, no loose buttons on the scene, every option still wired',()=>{
 const cage=stripC(read('components/beast-cage-portal.tsx')),home=stripC(read('components/home-pocket.tsx')),menu=read('components/world-menu.tsx');
 assert.match(cage,/<WorldMenu context="cage"/);assert.match(home,/<WorldMenu context="home"/);
 assert.match(cage,/useWorldView\(sameSpark\)/);assert.match(home,/useWorldView\(!!own,\{pixelSync:false\}\)/);
 assert.match(cage,/overlay!=='none'\?<SparkBeastArena/);assert.match(cage,/overlayFor\(view,/);
 assert.doesNotMatch(cage,/className="cage-view-toggle"/);assert.doesNotMatch(home,/data-home-view-toggle|lc-roamer-tools|>🌍 Enter the tiny world</);
 assert.match(cage,/menuHost=\{hosts\.tools\}/);assert.match(cage,/menuHost=\{hosts\.place\} infoHost=\{hosts\.about\}/);
 assert.match(home,/menuHost=\{hosts\.tools\} ignorePixel/);assert.match(home,/setWorld\(true\)/);assert.match(home,/lc-tools-open/);
 for(const k of ['data-world-view','data-menu-reset','data-menu-diary','data-menu-look','data-menu-senses','data-menu-open-map','POCKET_3D_CAMERA_RESET','Escape'])assert.ok(menu.includes(k),k);
 assert.match(menu,/hidden=\{!open\}/);assert.match(menu,/aria-haspopup="dialog"/);
 const css=read('components/world-menu.module.css');assert.match(css,/min-height:44px/);assert.match(css,/max-height:84dvh/);
});
test('scene components portal their controls into the menu only when a host exists, and keep the on-scene fallback otherwise',()=>{
 const lw=read('components/living-world.tsx'),pk=read('components/cage-pocket-dimension.tsx');
 assert.match(lw,/const toMenu=embedded&&!!menuHost&&!spawned/);assert.match(lw,/createPortal\(actions,menuHost!\)/);
 assert.match(lw,/embedded&&infoHost\?createPortal\(/);
 for(const k of ['data-lw-beachcam','data-lw-spawn','data-lw-watch','data-lw-expand','data-lw-roadster','data-lw-fly','data-lw-exit'])assert.ok(lw.includes(k),k);
 assert.match(pk,/if\(menuHost\)return createPortal\(<div role="toolbar" aria-label="Pocket controls" data-pocket-tools-menu>/);
 assert.match(pk,/className=\{styles\.godbar\}/);assert.match(pk,/ignorePixel\?false:deviceClassicPixel\(\)/);
});
test('Senses panel: four clear sections, long text folded away, consent and revocation text kept, every disabled button explains why',()=>{
 const s=read('components/live-senses.tsx');
 for(const k of ['data-senses-section="vision"','data-senses-section="speech"','data-senses-section="collected"','data-senses-section="remember"'])assert.ok(s.includes(k),k);
 assert.ok((s.match(/<details className="senses-more">/g)||[]).length>=4);
 assert.match(s,/I consent to browser speech recognition, including possible off-device audio processing/);
 assert.match(s,/I explicitly approve persisting these selected text observations in COSMOS/);
 assert.match(s,/Stop all sensing and revoke unsent context/);assert.match(s,/Previously saved memories require separate owner correction/);
 for(const m of s.matchAll(/<button type="button"[^>]*disabled=\{[^}]*\}[^>]*>/g)){} // disabled buttons in the capture sections carry a title reason:
 assert.match(s,/title=\{!canSend\?'Connect the host to add observations to a draft'/);assert.match(s,/title=\{!speechOn&&!allowBrowserSpeech\?'Tick the consent box first'/);
 assert.match(s,/title=\{!memoryEnabled\?'Durable sensor text is not enabled on this host'/);
});
test('site menu carries the world map and the piece chip with prev/next neighbours',()=>{
 const n=read('components/site-nav.tsx');
 for(const k of ['data-world-piece','data-world-prev','data-world-next','data-world-map','data-world-piece-link','worldHere(path)','You are here','Next door'])assert.ok(n.includes(k),k);
 assert.match(read('components/site-nav.module.css'),/\.pieceArrow\{[^}]*min-width:36px;min-height:36px/);
});
