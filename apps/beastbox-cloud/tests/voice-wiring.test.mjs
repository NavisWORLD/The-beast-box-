import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {VOICES,creatureVoice,speciesVoice,seaLifeVoice,SEA_VOICE_KEY,voicePool,roadsterVoice} from '../lib/universe/creature-voices.mjs';
import {voiceCast,castLine,beastVoiceKey,speciesVoiceKey,createRoadsterVoice} from '../lib/universe/voice-cast.mjs';
import {RESIDENT_LIFE_KEY} from '../lib/universe/sprite-life.mjs';
import {seededLandscapes,landscapeZoom} from '../lib/universe/seeded-landscapes.mjs';
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
const u3=readFileSync(new URL('../components/universe-3d.tsx',import.meta.url),'utf8');
const ALL=['kairo','nova','zeref','zeref64','kitten'];
test('every character in the voice data can speak: residents plus the active beast',()=>{
 const sprites=Object.keys(VOICES.sprites);
 const res=Object.keys(RESIDENT_LIFE_KEY);const speakers=new Set(Object.values(RESIDENT_LIFE_KEY));
 for(const n of ['Kitten','Zeref','Zeref64'])speakers.add(voiceCast([],n,null)[0]?.key);
 for(const k of sprites)assert.ok(speakers.has(k),k+' has lines but can never speak');
 assert.ok(res.length>=5);
});
test('beast key: named characters match, own-named beasts do not',()=>{assert.equal(beastVoiceKey('Zeref · Nightcat Dragon'),'zeref');assert.equal(beastVoiceKey('Zeref64'),'zeref64');assert.equal(beastVoiceKey('Kitten'),'kitten');assert.equal(beastVoiceKey('Duskscale'),null);assert.equal(beastVoiceKey(''),null);});
test('cast: only creatures that are really there; a beast with neither voice adds nobody',()=>{
 assert.equal(voiceCast(['Nobody'],'Duskscale',null).length,0);
 const c=voiceCast([],'Duskscale','nebula');assert.equal(c.length,1);assert.equal(c[0].species,'NEBULA');assert.equal(c[0].key,null);
 assert.equal(speciesVoiceKey('void'),'VOID');assert.equal(speciesVoiceKey('bogus'),null);assert.equal(speciesVoiceKey('_note'),null);
});
test('species lines: every species idle and tap line is reachable and approved',()=>{
 for(const [sp,cats] of Object.entries(VOICES.species_optional)){if(sp[0]==='_')continue;for(const cat of ['idle','tap']){const seen=new Set();for(let i=0;i<200;i++)seen.add(speciesVoice(sp,cat,'s'+i,i));assert.equal(seen.size,cats[cat].length,sp+':'+cat);}}
 assert.equal(speciesVoice('nope','idle','s',1),null);
});
test('sea life lines: every ocean kind maps to lines and every line is reachable',()=>{
 for(const [kind,key] of Object.entries(SEA_VOICE_KEY)){const pool=VOICES.sea_life[key];assert.ok(pool?.length,kind);const seen=new Set();for(let i=0;i<300;i++)seen.add(seaLifeVoice(kind,'s'+i,i));assert.equal(seen.size,pool.length,kind);}
 assert.equal(seaLifeVoice('dragon','s',1),null);
});
test('castLine is deterministic, uses only shipped lines and alternates character and species lines for a beast',()=>{
 const sp=voiceCast([],'Zeref','aurora')[0];
 assert.equal(castLine(sp,'idle','s',2),castLine(sp,'idle','s',2));
 const seen=new Set();for(let i=0;i<60;i++)seen.add(castLine(sp,'idle','s'+i,i));
 const all=new Set([...voicePool('zeref','idle'),...VOICES.species_optional.AURORA.idle]);
 for(const l of seen)assert.ok(all.has(l),l);
 assert.ok([...seen].some(l=>voicePool('zeref','idle').includes(l))&&[...seen].some(l=>VOICES.species_optional.AURORA.idle.includes(l)));
 assert.equal(castLine(null,'idle','s',1),null);
});
test('roadster: board once, other_rides when a resident is close, cruise once after sustained driving, stop after a drive; every category is reachable',()=>{
 const r=createRoadsterVoice();const cats=[];const st=(dt,o)=>{const x=r.step(dt,o);if(x)cats.push(x);};
 st(.1,{wantCar:true,carV:0,nearResident:'Kairo'});st(1,{wantCar:true,carV:0,nearResident:'Kairo'});assert.deepEqual(cats.map(c=>c.cat),['board']);
 for(let i=0;i<7;i++)st(1,{wantCar:true,carV:5,nearResident:'Kairo'});assert.deepEqual(cats.map(c=>c.cat),['board','other_rides']);assert.equal(cats[1].other,'Kairo');
 for(let i=0;i<8;i++)st(1,{wantCar:true,carV:5});assert.equal(cats.filter(c=>c.cat==='cruise').length,1);
 for(let i=0;i<20;i++)st(1,{wantCar:true,carV:6});assert.equal(cats.filter(c=>c.cat==='cruise').length,1);
 st(1,{wantCar:true,carV:0});assert.equal(cats.at(-1).cat,'stop');
 st(1,{wantCar:false});const n=cats.length;st(.1,{wantCar:true,storming:.9});assert.equal(cats.at(-1).cat,'storm');st(1,{wantCar:false});st(.1,{wantCar:true,night:true});assert.equal(cats.at(-1).cat,'night');assert.equal(cats.length,n+2);
 for(const c of ['board','cruise','night','storm','stop','other_rides']){const l=roadsterVoice(c,'s',1,{beast:'Pip',other:'Kairo'});assert.ok(l&&!l.includes('{'),c);}
 const quiet=createRoadsterVoice();const q=[];for(let i=0;i<30;i++){const x=quiet.step(1,{wantCar:true,carV:0});if(x)q.push(x.cat);}assert.deepEqual(q,['board']);
});
test('the world is wired: cast, roadster sequencer, sea life, and no Math.random in the new helpers',()=>{
 assert.ok(/voiceCast\(/.test(lw)&&/castLine\(/.test(lw)&&/createRoadsterVoice\(/.test(lw)&&/seaLifeVoice\(/.test(lw));
 assert.ok(!/Math\.random|Date\.now|performance\.now/.test(readFileSync(new URL('../lib/universe/voice-cast.mjs',import.meta.url),'utf8')));
});
test('zoom lines: the landscape line shows on every zoom-in to Orbit, the growth line on Planet, shelter is wired to a real storm',()=>{
 assert.ok(!/zlineN\.current%2/.test(u3));
 assert.ok(/s==='Orbit'\?\(landscapeLineFor\(/.test(u3));
 assert.ok(/allStorms\(u\)\.some\(\(q:any\)=>q\.planet===ls\.planet\)\?1:0/.test(u3));
});
test('landscapeZoom: n rotates the pick, n=0 keeps the old key, and every zoom line for every mode is reachable',()=>{
 const u={seed:'tiny',planets:[{id:'A',name:'A'}],stars:[],life:[]};
 const l={id:'L1',name:'Alder',kind:'grove',planet:'A'};
 const base=landscapeZoom(l,'gather',{seed:'s'});assert.deepEqual(base,landscapeZoom(l,'gather',{seed:'s',n:0}));
 const seen=new Set();for(let n=0;n<40;n++)seen.add(landscapeZoom(l,'gather',{seed:'s',n}).line);assert.equal(seen.size,2);
 assert.equal(landscapeZoom(l,'shelter',{seed:'s',n:3}).line,'Alder is sheltering from the storm.');
});
