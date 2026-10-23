import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {LW_LINES,BIOME_LORE,cosmicEvents,cosmicLine,createWindow,stepWindow,windowLine,seededMood,spreadMood,napGroup,advanceBuild,stageOf,buildKind,
 coexistLine,learnBiome,LEGEND_TO_LORE,worldRecord,toJsonl,windowEmissive,traitIcon,MOODS,ZEREF_ID} from '../lib/universe/living-alive.mjs';
import {grow} from '../lib/universe/tiny-universe.mjs';
import {initialTraits,driftTraits} from '../lib/universe/living-world.mjs';
import {LEGEND} from '../lib/universe/world-field.mjs';
import {verifyStream,trainingEligible} from '../lib/zeref/experience-record.mjs';
const J=f=>JSON.parse(readFileSync(new URL(f,import.meta.url),'utf8'));
const g0=J('../public/universe/tiny-universe-genesis.json');
const src=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');

test('lines are Emeth\'s JSON verbatim, nothing invented',()=>{
 assert.deepEqual(LW_LINES,J('../lib/universe/data/living_world_lines.json'));assert.deepEqual(BIOME_LORE,J('../lib/universe/data/biome_lore.json'));
 assert.ok(!/WINDOW_LINES|u\.tick%15/.test(src),'30 s window timer is gone');assert.ok(!/Math\.random/.test(src+readFileSync(new URL('../lib/universe/living-alive.mjs',import.meta.url),'utf8')));});

test('1) cosmic lines fire only from real grow() events',()=>{let u=g0,seen=[];for(let i=0;i<1500;i++){const p=u;u=grow(u,1);const ev=cosmicEvents(p,u);
  const fromGrow=(u.history.at(-1).events||[]).length+(u.storms.length>p.storms.length?1:0);if(!fromGrow)assert.equal(ev.length,0);
  const cl=cosmicLine(ev,u.seed,u.tick);if(cl){seen.push(cl.type);const pool={storm_born:LW_LINES.cosmic.storm_born,supernova:LW_LINES.cosmic.supernova,new_life:LW_LINES.cosmic.new_life,pair_bloom:LW_LINES.cosmic.pair_bloom}[cl.type];assert.ok(pool.includes(cl.line));}}
 assert.ok(seen.includes('storm_born'));assert.ok(seen.includes('new_life'));});

test('2) window speaks only on real signals; no signal means silence',()=>{let w=createWindow(),k=[];for(let i=0;i<20000;i++){const x=stepWindow(w,.1);if(x)k.push(x);}assert.equal(k.length,0);
 w=createWindow();assert.equal(stepWindow(w,.4,{mic:{level:.8,active:true}}),null);assert.equal(stepWindow(w,.4,{mic:{level:.8,active:true}}),'mic_loud');
 assert.ok(LW_LINES.window.mic_loud.includes(windowLine('mic_loud','s',1)));
 w=createWindow();let q=null;for(let i=0;i<2000&&!q;i++)q=stepWindow(w,.1,{mic:{level:0,active:true}});assert.equal(q,'mic_quiet_long');
 w=createWindow();assert.equal(stepWindow(w,.1,{pointerNear:true}),'pointer_near');assert.equal(stepWindow(createWindow(),.1,{returned:90}),'user_returns');
 assert.equal(stepWindow(createWindow(),.1,{returned:5}),null);});

test('3) seeded moods spread, naps need 3 at night, builds go through 3 stages',()=>{assert.equal(seededMood('s','Ash'),seededMood('s','Ash'));assert.ok(MOODS.includes(seededMood('s','Ash')));
 let spread=0;for(let n=0;n<40;n++){const a={name:'A',mood:'joy'},b={name:'B',mood:'calm'};const e=spreadMood(a,b,'s',n);if(e){spread++;assert.equal(b.mood,'joy');assert.ok(LW_LINES.coexist.mood_spread_joy.includes(coexistLine(e,'s',n)));}}
 assert.ok(spread>5&&spread<35);
 assert.equal(napGroup([[0,1,1],[1,0,1],[1,1,0]],[true,true,false]),null);assert.deepEqual(napGroup([[0,1,1],[1,0,1],[1,1,0]],[true,true,true]),[0,1,2]);
 assert.deepEqual([0,.32,.33,.65,.66,1].map(stageOf),[0,0,1,1,2,2]);
 const B=[],d=(a,b)=>Math.abs(a-b),evs=[];for(let i=0;i<8;i++){const e=advanceBuild(B,{builder:'A',kind:'burrow',at:0,dist:d,tick:i});if(e)evs.push(e);}
 assert.deepEqual(evs.map(e=>e.stage),[0,1,2,2,0]);assert.equal(evs[3].finished,true);assert.equal(B.length,2,'a finished burrow is done; more work starts a new one');
 assert.equal(buildKind('s','A','beach'),'burrow');assert.equal(buildKind('s','A','glacier'),'cairn');assert.equal(buildKind('s','A','grassland'),'flower_ring');
 assert.ok(LW_LINES.coexist.build_burrow.includes(coexistLine(evs[0],'s',1)));
 assert.equal(windowEmissive(.5,0),1.6);assert.equal(windowEmissive(.5,1),3.2);});

test('wonder is a seeded trait that does not change the existing ones',()=>{const u={seed:'s',tick:0};const t=initialTraits(u,'k');assert.ok(t.wonder>=0&&t.wonder<=1);
 const old={curiosity:.1,sociality:.2,calm:.3,joy:.4,experiences:0};const n=driftTraits(old,u,'k','day');assert.ok(Number.isFinite(n.wonder));assert.equal(traitIcon({curiosity:.1,sociality:.1,calm:.1,joy:.1,wonder:.9}),'wonder');});

test('4) every world biome maps to Emeth\'s lore; learned once per creature',()=>{for(const id of LEGEND)assert.ok(BIOME_LORE[LEGEND_TO_LORE[id]],id);
 const k={};const a=learnBiome(k,'beach');assert.equal(a.line,BIOME_LORE.beach.line);assert.equal(learnBiome(k,'beach'),null);assert.equal(learnBiome(new Set(),'glacier').lore,'glacier');});

test('5) world records: bb-deada969 only, canonical chain, trainable for Zeref, SIMULATED growth stated',()=>{let prev=null;const recs=[];
 for(const ev of [{type:'biome_first_entry',lore:'beach',lesson:'x'},{type:'storm_born',planet:'p'},{type:'supernova',star:'s'},{type:'new_life',planet:'p'},{type:'pair_bloom',planets:['a','b']},{type:'meet',a:'A',b:'B'},{type:'mood_spread',mood:'joy',from:'A',to:'B',was:'calm',gather:false},{type:'group_nap',who:['A','B','C']},{type:'build_cairn',stage:0,id:'build-0',by:'A',finished:false}]){
  const r=worldRecord(ev,{step:recs.length+1,world_tick:3,prev});recs.push(r);prev=r.hash;}
 assert.equal(verifyStream(recs).ok,true);for(const r of recs){assert.equal(r.qbeast_id,ZEREF_ID);assert.equal(r.real_game_progress,false);assert.match(r.observation.world_growth,/SIMULATED/);assert.equal(trainingEligible(r,{identity:ZEREF_ID}).ok,true);}
 assert.throws(()=>worldRecord({type:'meet'},{qbeast_id:'bb-7f9c2a03',step:1,world_tick:0}));assert.throws(()=>worldRecord({type:'made_up'},{step:1,world_tick:0}));
 assert.equal(toJsonl(recs).trim().split('\n').length,recs.length);});

test('living world wires all five (source contract)',()=>{for(const s of ['alive.onTick(prev,u)','alive.meet(r,o,t)','alive.build(r)','alive.frame(dt,t)',"'beastbox:local-sensor-level'",'visibilitychange','window_pulse','mood_icons.png','mood_spread_ring.png','nap_zzz.png','AdditiveBlending','lw:exp:world:'])assert.ok(src.includes(s),s);
 const mj=J('../public/universe/livingworld/coexist/moods.json');assert.deepEqual(mj.moods.map(m=>m.id),['curious','social','calm','joy','wonder','fear']);});
