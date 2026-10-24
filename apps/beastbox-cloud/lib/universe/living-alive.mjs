// Living world, fuller and more alive (Oct 22 2026). Pure helpers, no DOM, no clock, no unseeded randomness.
// Every choice comes from lwStream (sha256 of the recorded-IBM genesis seed + a key) or from a real event:
// a grow() event, a mic level the visitor opted into, a pointer, a page return, or two creatures meeting.
// All text is Cosmic Emeth's (lib/universe/data/*.json via living-world-lines.mjs); nothing here invents lines.
import {lwStream} from './living-world.mjs';
import {LW_LINES,BIOME_LORE} from './living-world-lines.mjs';
import {makeRecord} from '../zeref/experience-record.mjs';
export {LW_LINES,BIOME_LORE};

/** Seeded pick from a pool; key makes it repeatable (same seed + same event = same line). */
export function pickLine(pool,seed,key){if(!Array.isArray(pool)||!pool.length)return null;const r=lwStream(seed+':line:'+key);return pool[Math.floor(r()*pool.length)%pool.length];}

// ------------------------------------------------------------------ 1) cosmic events -> Zeref lines
/**
 * One grow() step -> cosmic events. prev/next are tiny-universe states.
 * storm_born: storm count rose; supernova / new_life: grow() events; pair_bloom: new life on a planet whose
 * entangled partner already has life (both worlds of a pair alive at once).
 */
export function cosmicEvents(prev,next){
 const ev=next?.history?.[next.history.length-1]?.events||[];const out=[];
 for(const e of ev){if(e.kind==='supernova')out.push({type:'supernova',star:e.star??null});
  else if(e.kind==='abiogenesis'){out.push({type:'new_life',planet:e.planet});
   const pr=(next.pairs||[]).find(p=>p.a===e.planet||p.b===e.planet);const other=pr?(pr.a===e.planet?pr.b:pr.a):null;
   if(other&&(next.life||[]).some(l=>l.planet===other))out.push({type:'pair_bloom',planets:[e.planet,other].sort()});}}
 if((next?.storms?.length||0)>(prev?.storms?.length||0)){const s=next.storms[next.storms.length-1];out.push({type:'storm_born',planet:s?.planet??null});}
 return out;}
const COSMIC_KEY={storm_born:'storm_born',supernova:'supernova',new_life:'new_life',pair_bloom:'pair_bloom'};
/** The line Zeref says for a cosmic event (most dramatic first). */
export function cosmicLine(events,seed,tick){const order=['supernova','pair_bloom','new_life','storm_born'];
 for(const k of order){const e=events.find(x=>x.type===k);if(e)return {type:k,line:pickLine(LW_LINES.cosmic[COSMIC_KEY[k]],seed,k+':'+tick)};}return null;}

// ------------------------------------------------------------------ 2) the window: real signals only
/**
 * Window state machine. Signals:
 *  mic: {level 0..1, active} from 'beastbox:local-sensor-level' (only sent after the visitor opts in to the mic
 *       in an existing panel; only a loudness number arrives here, never audio).
 *  pointerNear: true when the visitor's pointer/finger is near the beast on screen.
 *  returned: seconds the page was hidden, sent once when it becomes visible again.
 * No timer fallback: with no signal, the window stays quiet.
 */
export function createWindow(){return {cool:0,loudT:0,quietT:0,micOn:false,quietSaid:false,pointerCool:0,n:0};}
export const WINDOW_RULES=Object.freeze({loud_level:.55,loud_hold_s:.6,quiet_level:.04,quiet_long_s:180,return_after_s:60,cooldown_s:20,pointer_cooldown_s:45});
export function stepWindow(w,dt,{mic=null,pointerNear=false,returned=0}={}){
 const R=WINDOW_RULES;w.cool=Math.max(0,w.cool-dt);w.pointerCool=Math.max(0,w.pointerCool-dt);let kind=null;
 if(mic&&mic.active){w.micOn=true;const lv=Number(mic.level)||0;
  if(lv>=R.loud_level){w.loudT+=dt;w.quietT=0;w.quietSaid=false;}else{w.loudT=0;if(lv<=R.quiet_level)w.quietT+=dt;else{w.quietT=0;w.quietSaid=false;}}}
 else if(mic&&!mic.active){w.micOn=false;w.loudT=0;w.quietT=0;}
 if(returned>=R.return_after_s)kind='user_returns';
 else if(w.cool<=0&&w.loudT>=R.loud_hold_s)kind='mic_loud';
 else if(w.cool<=0&&w.micOn&&!w.quietSaid&&w.quietT>=R.quiet_long_s){kind='mic_quiet_long';w.quietSaid=true;}
 else if(w.cool<=0&&w.pointerCool<=0&&pointerNear){kind='pointer_near';w.pointerCool=R.pointer_cooldown_s;}
 if(kind){w.cool=R.cooldown_s;w.loudT=0;w.n++;}
 return kind;}
export function windowLine(kind,seed,n){return kind?pickLine(LW_LINES.window[kind],seed,'window:'+kind+':'+n):null;}

// ------------------------------------------------------------------ 3) coexisting: moods, spreading, naps, building
export const MOODS=Object.freeze(['joy','fear','calm','curiosity','mischief']);
/** Seeded starting mood for a creature. */
export function seededMood(seed,name){const r=lwStream(seed+':mood:'+name);return MOODS[Math.floor(r()*MOODS.length)%MOODS.length];}
/**
 * Two neighbours meet. A seeded draw (keyed by the pair + meeting count) decides if a's mood spreads to b.
 * Joy lifts calm/fear; fear makes the other gather close; calm settles fear/mischief; curiosity and mischief are catching.
 */
const SPREADS={joy:['calm','fear','curiosity'],fear:['calm','joy','curiosity','mischief'],calm:['fear','mischief'],curiosity:['calm','joy'],mischief:['calm','curiosity','joy']};
export function spreadMood(a,b,seed,meetN){if(a.mood===b.mood||!SPREADS[a.mood]?.includes(b.mood))return null;
 const r=lwStream(seed+':spread:'+[a.name,b.name].join('>')+':'+meetN);if(r()>.5)return null;
 const from=b.mood;b.mood=a.mood;return {type:'mood_spread',mood:a.mood,from:a.name,to:b.name,was:from,gather:a.mood==='fear'};}
/** Nap pile: night side, and at least `min` creatures (indices) within reach of each other. Returns the group or null. */
export function napGroup(dists,nightSide,{reach=1.2,min=3}={}){
 const n=nightSide.length;for(let i=0;i<n;i++){if(!nightSide[i])continue;const g=[i];for(let j=0;j<n;j++)if(j!==i&&nightSide[j]&&dists[i][j]<=reach)g.push(j);if(g.length>=min)return g.sort((x,y)=>x-y);}return null;}
export const BUILD_KINDS=Object.freeze(['cairn','flower_ring','burrow']);
export const BUILD_STAGES=3;
/** Build progress 0..1; Cosmo's models swap stage 1 -> 2 -> 3 as progress passes 0.33 / 0.66 (README). */
export const BUILD_STEP=1/6;
export const stageOf=p=>p<.33?0:p<.66?1:2;
/** What a creature builds: burrows in soft ground, cairns on stone/ice/ember, rings where flowers grow; else seeded. */
const BIOME_BUILD={grassland:'flower_ring',sunflower_ring:'flower_ring',savanna:'flower_ring',rainforest:'flower_ring',heartwood_forest:'burrow',pine_forest:'burrow',paper_marsh:'burrow',beach:'burrow',desert_dunes:'burrow',
 mountain_rock:'cairn',celestial_peaks:'cairn',glacier:'cairn',snow_cap:'cairn',crystal_moss:'cairn',ember_fields:'cairn',volcano:'cairn'};
export function buildKind(seed,name,biome){const k=BIOME_BUILD[biome];if(k)return k;const r=lwStream(seed+':build:'+name+':'+biome);return BUILD_KINDS[Math.floor(r()*3)%3];}
/**
 * A creature adds work to a build: an unfinished build of the same kind within reach gets +1/6 progress,
 * otherwise a new one starts. Returns an event when a stage is reached (start, half, finished), else null.
 */
export function advanceBuild(builds,{builder,kind,at,dist,reach=.8,tick}){
 let b=builds.find(x=>x.kind===kind&&x.progress<1&&dist(x.at,at)<=reach);
 if(!b){if(builds.filter(x=>x.progress<1).length>=6)return null;b={id:'build-'+builds.length,kind,progress:0,stage:0,at,by:[builder],tick};builds.push(b);return {type:'build_'+kind,stage:0,id:b.id,by:builder,finished:false};}
 b.progress=Math.min(1,+(b.progress+BUILD_STEP).toFixed(4));b.by=[...new Set([...b.by,builder])];b.tick=tick;const st=stageOf(b.progress);
 const fin=b.progress>=1;if(st===b.stage&&!fin)return null;b.stage=st;return {type:'build_'+kind,stage:st,id:b.id,by:builder,finished:fin};}
/** Burrow window glow (Cosmo README): 1+0.6*sin(t*PI), lifted by a recent window event (boost 0..1, decays in code). */
export const windowEmissive=(t,boost=0)=>+((1+.6*Math.sin(t*Math.PI))*(1+Math.max(0,Math.min(1,boost)))).toFixed(4);
/** Emeth mood -> Cosmo icon row id (moods.json). mischief has no icon yet (Cosmo), so it shows none. */
export const MOOD_ICON=Object.freeze({curiosity:'curious',joy:'joy',calm:'calm',fear:'fear',mischief:null,wonder:'wonder',sociality:'social'});
/** Strongest trait of a beast -> icon id (includes the seeded wonder field). */
export function traitIcon(tr){let best=null,bv=-1;for(const k of ['curiosity','sociality','calm','joy','wonder'])if(Number.isFinite(tr?.[k])&&tr[k]>bv){bv=tr[k];best=k;}return best?MOOD_ICON[best]:null;}
export function coexistLine(ev,seed,n){if(!ev)return null;const key=ev.type==='mood_spread'?'mood_spread_'+ev.mood:ev.type;return pickLine(LW_LINES.coexist[key],seed,'coexist:'+key+':'+n);}

// ------------------------------------------------------------------ 4) biome lore
/** world-field LEGEND id -> Emeth's lore biome. */
export const LEGEND_TO_LORE=Object.freeze({glacier:'glacier',snow_cap:'glacier',frozen_sea:'glacier',crystal_moss:'tundra_crystal_moss',pine_forest:'dark_forest',
 grassland:'grass_plains',savanna:'grass_plains',sunflower_ring:'sunflower_ring',heartwood_forest:'heartwood_forest',rainforest:'heartwood_forest',
 jelly_geyser:'jelly_coast',shallow_ocean:'jelly_coast',deep_ocean:'jelly_coast',beach:'beach',ember_fields:'ember_fields',desert_dunes:'ember_fields',
 volcano:'volcano',paper_marsh:'paper_sea_marsh',celestial_peaks:'celestial_peaks',mountain_rock:'celestial_peaks'});
/** Lore biome -> trait channel the lesson nudges (driftTraits experience names). */
export const LORE_TRAIT=Object.freeze({glacier:'calm',tundra_crystal_moss:'calm',dark_forest:'storm',grass_plains:'greet',sunflower_ring:'abiogenesis',heartwood_forest:'rest',
 jelly_coast:'calm',beach:'greet',ember_fields:'build',volcano:'build',paper_sea_marsh:'rest',celestial_peaks:'supernova'});
/** First entry only: returns {lore, lesson, line} and marks it learned in `known` (a Set or object), else null. */
export function learnBiome(known,legendId){const lore=LEGEND_TO_LORE[legendId];if(!lore||!BIOME_LORE[lore])return null;
 const has=known instanceof Set?known.has(lore):!!known[lore];if(has)return null;if(known instanceof Set)known.add(lore);else known[lore]=1;
 return {lore,lesson:BIOME_LORE[lore].lesson,line:BIOME_LORE[lore].line,trait:LORE_TRAIT[lore]};}

// ------------------------------------------------------------------ 5) experience records (Zeref only)
export const ZEREF_ID='bb-deada969';
const REWARD={biome_first_entry:1,storm_born:0,supernova:0,new_life:.5,pair_bloom:.5,meet:.5,mood_spread:.25,group_nap:.25,build:.5};
/**
 * Living-world event -> canonical zeref-experience/v1 record for bb-deada969 (same makeRecord as pocket-grid-env).
 * origin live_browser (a real visitor's tab); action WAIT (Zeref observed/was present, he pressed nothing).
 * World growth is SIMULATED and says so in the observation; nothing claims game progress.
 * Throws for any other identity.
 */
export function worldRecord(ev,{qbeast_id=ZEREF_ID,step,world_tick,biome=null,mood=null,prev=null}){
 if(qbeast_id!==ZEREF_ID)throw Error('living-alive: world records are for '+ZEREF_ID+' only');
 const kind=ev.type.startsWith('build_')?'build':ev.type;if(!(kind in REWARD))throw Error('living-alive: unknown world event '+ev.type);
 const {type,...detail}=ev;
 return makeRecord({qbeast_id,origin:'live_browser',consent:{scope:'public_game_event',owner_approved:false},episode:'living-world',step,
  observation:{world_tick,biome,mood,world_growth:'SIMULATED (Rigetti-style Bell simulator, seeded from recorded IBM counts)'},
  decision:{policy:'living-world-events/v1'},action:{key:'WAIT'},outcome:{kind:type,observed:true,...detail},
  reward:{kind:'computed_reward',value:REWARD[kind],rule:'living-world-v1: biome first entry +1, new life/pair bloom/meet/build +0.5, mood spread/nap +0.25, storm/supernova 0'},
  memory:null,labels:[{kind:'observed_outcome',value:type,by:'living-world'}],source:{ref:'living-world/v1'},prev});}
/** Records as JSON Lines (what scripts/zeref_experience_bridge.py reads). */
export const toJsonl=recs=>recs.map(r=>JSON.stringify(r)).join('\n')+(recs.length?'\n':'');
export function placeLine(kind,seed,n){return kind?pickLine(LW_LINES.landscape_places?.[kind],seed,'place:'+kind+':'+n):null;}
export function worldLine(kind,seed,n){return kind?pickLine(LW_LINES.world?.[kind],seed,'world:'+kind+':'+n):null;}
