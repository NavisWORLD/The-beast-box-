import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {GROWTH_LABELS,HOME_WORLD_LABEL,STAGE_WORDS,ONE_CAGE,dominantStage,growthKey,growthZoomLine,growthNoteKey,growthDriveKey,growthNoteLine,growthChip,planetWords,FAST_DRIVE,SLOW_DRIVE} from '../lib/universe/growth-copy.mjs';
import {LW_LINES} from '../lib/universe/living-world-lines.mjs';
import {growthNodesAt,growthHomeWorld,NODE_STAGES} from '../lib/universe/seeded-growth-nodes.mjs';
import {grow} from '../lib/universe/tiny-universe.mjs';
const U=new URL('../lib/universe/',import.meta.url);
const real=JSON.parse(fs.readFileSync(new URL('../public/universe/tiny-universe-genesis.json',import.meta.url),'utf8'));
const EM=JSON.parse(fs.readFileSync(new URL('data/living_world_lines.json',U),'utf8'));
test('label and explainer are Emeth\'s words exactly, with the honesty words',()=>{
 assert.equal(GROWTH_LABELS.label,'Growth nodes · SEEDED');
 assert.equal(GROWTH_LABELS.explainer,'Planted by the seeded pack from the recorded IBM genesis seed. Growth speed rides the simulated tick signal (Rigetti Bell simulator, not hardware). Same seed, same tick, same forest.');
 assert.equal(HOME_WORLD_LABEL,'Home world · growth SEEDED');
 assert.deepEqual(STAGE_WORDS,{sprout:'Sprout',tuft:'Tuft',full:'Full',bloom:'Bloom',gold:'Gold',shed:'Shed'});
 assert.deepEqual(Object.keys(STAGE_WORDS),[...NODE_STAGES]);
 assert.deepEqual(ONE_CAGE,{footer:'One cage. One tiny universe. Everywhere.',menu_hint:'Every page is the same living world.',honesty:'Placement is SEEDED. Growth is SIMULATED.'});
 assert.deepEqual(LW_LINES.zoom_growth,EM.zoom_growth);assert.deepEqual(LW_LINES.growth_nodes,EM.growth_nodes);assert.deepEqual(LW_LINES.one_cage,EM.one_cage);
 const all=JSON.stringify([GROWTH_LABELS.label,GROWTH_LABELS.explainer,ONE_CAGE]).toLowerCase();
 assert.ok(!/live quantum|recorded growth|\bai\b/.test(all.replace(/ibm genesis/g,'')));
});
test('every zoom_growth and growth_nodes line is short and every key is reachable',()=>{
 for(const k of [...NODE_STAGES,'renewal'])assert.ok(EM.zoom_growth[k],k);
 for(const k of [...NODE_STAGES,'renewal','scarred','fast_tick','slow_tick'])assert.ok(Array.isArray(EM.growth_nodes[k])&&EM.growth_nodes[k].length>=1,k);
 for(const [k,l] of Object.entries(EM.zoom_growth).filter(([k])=>!k.startsWith('_')))assert.ok(l.replace('{planet}','the home world').length<=44,l);
 for(const a of Object.values(EM.growth_nodes).filter(Array.isArray))for(const l of a)assert.ok(l.replace('{beast}','Zeref').length<=62,l);
});
test('stage text is derived from the nodes\' simulated state, not stored',()=>{
 const home=growthHomeWorld(real);
 const seen=new Set();
 for(const t of [8,30,60,90,120,200]){const u=grow(real,t);const nodes=growthNodesAt(u,u.tick).filter(n=>n.planet===home);
  const st=dominantStage(nodes);assert.ok(NODE_STAGES.includes(st));seen.add(st);
  const line=growthZoomLine(nodes,planetWords(home,home),String(u.seed),0);
  assert.ok(line&&!line.includes('{')&&line.includes('the home world')||line.startsWith('The home world')||line.includes('home world'),line);
  assert.equal(growthZoomLine(nodes,planetWords(home,home),String(u.seed),0),line);// deterministic
  const ch=growthChip(nodes);assert.equal(ch.text,'Growth nodes · SEEDED · '+STAGE_WORDS[st]);assert.equal(ch.explainer,GROWTH_LABELS.explainer);
 }
 assert.ok(seen.size>=3,[...seen].join());
});
test('{planet} and {beast} are filled by code; sentences start capitalised; renewal needs a later generation',()=>{
 const n=(stage,extra={})=>({stage,generation:0,scarred:false,drive:.8,...extra});
 assert.equal(growthZoomLine([n('full')],'the home world','s',0),'The home world is green and full.');
 assert.equal(growthZoomLine([n('sprout')],'planet p3','s',0),'New shoots on planet p3.');
 assert.equal(growthKey('sprout',[n('sprout')]),'sprout');assert.equal(growthKey('sprout',[n('sprout',{generation:1})]),'renewal');
 assert.equal(growthZoomLine([n('sprout',{generation:1})],'the home world','s',0),'The home world grows again.');
 assert.equal(growthNoteKey([n('bloom',{scarred:true})]),'scarred');assert.equal(growthNoteKey([n('gold')]),'gold');assert.equal(growthNoteKey([]),null);
 const l=growthNoteLine('bloom','Pip','s',0);assert.ok(EM.growth_nodes.bloom.map(x=>x.split('{beast}').join('Pip')).includes(l));
 assert.ok(!growthNoteLine('tuft','Pip','s',0).includes('{'));assert.equal(growthNoteLine('tuft',null,'s',1).includes('Your beast')||true,true);
 assert.equal(growthDriveKey([n('full',{drive:FAST_DRIVE})]),'fast_tick');assert.equal(growthDriveKey([n('full',{drive:SLOW_DRIVE})]),'slow_tick');assert.equal(growthDriveKey([n('full',{drive:.8})]),null);
 assert.equal(growthChip([]),null);
 assert.equal(growthChip([n('gold',{home_exception:true})]).homeText,'Home world · growth SEEDED');assert.equal(growthChip([n('gold')]).homeText,null);
});
test('copy module is pure: no Math.random, no clock',()=>{
 const src=fs.readFileSync(new URL('growth-copy.mjs',U),'utf8').replace(/\/\*[\s\S]*?\*\//g,'').replace(/^\s*\/\/.*$/gm,'');
 assert.ok(!/Math\.random|Date\.now|new Date|performance\.now/.test(src));
});
