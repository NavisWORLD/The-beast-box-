/** Bounded deterministic companion behavior. All runtime actions are classical software. */
import {recallAssociations,observeText} from './learn.mjs';
export const BEHAVIOR_SCHEMA='beastbox-behavior-v1';
export const ACTIONS=['rest','explore','inspect','play','wander','listen','idle'];
export const PLACES=['grove','nest','shore','observatory'];
const clamp=(n,lo=0,hi=100)=>Math.max(lo,Math.min(hi,Number.isFinite(Number(n))?Number(n):lo));
const round=n=>Math.round(n*1000)/1000;
const hash=s=>{let h=2166136261;for(const c of String(s))h=Math.imul(h^c.charCodeAt(0),16777619);return h>>>0;};
const seedOf=b=>String(b?.genome?.seed||b?.seed||'');
const bounded=(n,lo,hi)=>typeof n==='number'&&Number.isFinite(n)&&n>=lo&&n<=hi;
const DELTA={rest:7,explore:-2.4,inspect:-1.2,play:-2,wander:-1.5,listen:-.6,idle:.25};
function scoresFor({energy,curiosity,memoryBonus,sound,toy,attention,comfort,associations=[]}){
 const scores={rest:1+(100-energy)/30+comfort,explore:1+curiosity/45+memoryBonus,inspect:1+curiosity/65+toy*2,play:1+toy*2+attention+memoryBonus/2,wander:1+energy/75,listen:1+sound*3+attention,idle:1};
 for(const hit of associations)scores[hit.word]+=round(clamp(hit.score/8,0,1));return scores;
}
function actionFor(seed,tick,scores){
 const weights=ACTIONS.map(a=>Math.max(.05,scores[a])),total=weights.reduce((a,b)=>a+b,0),roll=hash(seed+':behavior:'+tick)/4294967296*total;
 let running=0;for(let i=0;i<weights.length;i++){running+=weights[i];if(roll<running)return ACTIONS[i];}return 'idle';
}
function validDecision(e,seed){
 const input=e?.input;if(!input||!e.result||!e.scores)return false;
 if(!bounded(input.energy,0,100)||!bounded(input.curiosity,0,100)||!bounded(input.memoryBonus,-1,1)||!['sound','toy','attention','comfort'].every(k=>bounded(input[k],0,1)))return false;
 const associations=input.associations||[];
 if(!Array.isArray(associations)||associations.length>ACTIONS.length||associations.some(h=>!ACTIONS.includes(h?.word)||!bounded(h.score,0,200)))return false;
 const expected=scoresFor({...input,associations});
 return ACTIONS.every(a=>e.scores[a]===round(expected[a]))&&e.action===actionFor(seed,e.tick,expected)
  &&e.result.energy===round(clamp(input.energy+DELTA[e.action]))
  &&e.result.curiosity===round(clamp(input.curiosity+(['explore','inspect'].includes(e.action)?-1.6:.5)))
  &&bounded(e.result.position?.x,.05,.95)&&bounded(e.result.position?.y,.05,.95);
}
export function environmentFor(input={}){
 return {place:PLACES.includes(input.place)?input.place:'grove',sound:clamp(input.sound,0,1),toy:clamp(input.toy,0,1),attention:clamp(input.attention,0,1),comfort:clamp(input.comfort??.5,0,1)};
}
export function createBehavior(beast){
 const seed=seedOf(beast);
 if(!/^[a-f0-9]{16,128}$/i.test(seed))throw Error('Verified genesis seed required');
 const t=beast?.genome?.inputs?.traits||beast?.genome?.t||{};
 return {schema:BEHAVIOR_SCHEMA,seed,tick:0,energy:clamp(beast?.energy??100),curiosity:round(clamp(25+clamp(t.spark??50)*.5+clamp(t.focus??50)*.2)),preferences:{grove:0,nest:0,shore:0,observatory:0},position:{x:.5,y:.5},lastAction:'idle',memory:[],events:[]};
}
export function validateBehavior(value,beast){
 const valid=value?.schema===BEHAVIOR_SCHEMA&&value.seed===seedOf(beast)
  &&Number.isSafeInteger(value.tick)&&value.tick>=0&&value.tick<1e12
  &&bounded(value.energy,0,100)&&bounded(value.curiosity,0,100)
  &&value.preferences&&PLACES.every(p=>bounded(value.preferences[p],-8,8))
  &&bounded(value.position?.x,0,1)&&bounded(value.position?.y,0,1)
  &&ACTIONS.includes(value.lastAction)&&Array.isArray(value.memory)&&value.memory.length<=24
  &&value.memory.every(e=>Number.isSafeInteger(e?.tick)&&e.tick>=0&&typeof e.kind==='string'&&e.kind.length<=32&&PLACES.includes(e.place)&&bounded(e.reward,-1,1))
  &&Array.isArray(value.events)&&value.events.length<=32
  &&value.events.every((e,i)=>Number.isSafeInteger(e?.tick)&&e.tick===value.tick-value.events.length+i&&e.kind==='behavior'&&ACTIONS.includes(e.action)&&PLACES.includes(e.place)&&validDecision(e,value.seed))
  &&(!value.events.length||(value.lastAction===value.events.at(-1).action&&value.position.x===value.events.at(-1).result.position.x&&value.position.y===value.events.at(-1).result.position.y))
  &&(!value.lastFeedback||(Number.isSafeInteger(value.lastFeedback.tick)&&value.lastFeedback.tick>=0&&value.lastFeedback.tick<=value.tick&&typeof value.lastFeedback.kind==='string'&&value.lastFeedback.kind.length<=32));
 return valid ? value : createBehavior(beast);
}
export function stepBehavior(value,beast,environment={}){
 const s=structuredClone(validateBehavior(value,beast));
 const place=['grove','nest','shore','observatory'].includes(environment.place)?environment.place:'grove';
 const sound=clamp(environment.sound,0,1),toy=clamp(environment.toy,0,1),attention=clamp(environment.attention,0,1),comfort=clamp(environment.comfort??.5,0,1);
 const memoryBonus=clamp(s.preferences[place]??0,-8,8)/8,energy=s.energy,curiosity=s.curiosity;
 // Learned graph evidence is supplied only by the existing session adapter below.
 // The contribution is capped; homeostatic state and the original decision rule remain.
 const associations=Array.isArray(environment.associations)?environment.associations.filter(h=>ACTIONS.includes(h?.word)&&bounded(h.score,0,200)).slice(0,ACTIONS.length):[];
 const scores=scoresFor({energy,curiosity,memoryBonus,sound,toy,attention,comfort,associations});
 const action=actionFor(s.seed,s.tick,scores);
 s.energy=round(clamp(energy+DELTA[action]));
 s.curiosity=round(clamp(curiosity+(action==='explore'||action==='inspect'?-1.6:.5)));
 if(['explore','wander','inspect','play'].includes(action)){
  const dx=((hash(s.seed+':x:'+s.tick)%201)-100)/2000,dy=((hash(s.seed+':y:'+s.tick)%201)-100)/2000;
  s.position={x:round(clamp(s.position.x+dx,.05,.95)),y:round(clamp(s.position.y+dy,.05,.95))};
 }
 const event={tick:s.tick,kind:'behavior',place,action,input:{energy,curiosity,sound,toy,attention,comfort,memoryBonus,associations:structuredClone(associations)},scores:Object.fromEntries(ACTIONS.map(a=>[a,round(scores[a])])),result:{energy:s.energy,curiosity:s.curiosity,position:{...s.position}}};
 s.tick++;s.lastAction=action;s.events=[...s.events,event].slice(-32);
 return {state:s,event};
}
export function feedbackBehavior(value,beast,{place='grove',reward=0,kind='interaction'}={}){
 const s=structuredClone(validateBehavior(value,beast));
 if(!['grove','nest','shore','observatory'].includes(place))throw Error('Unknown environment');
 const r=clamp(reward,-1,1);
 s.preferences[place]=round(clamp(s.preferences[place]+r,-8,8));
 s.memory=[...s.memory,{tick:s.tick,kind:String(kind).slice(0,32),place,reward:r}].slice(-24);
 s.lastFeedback={tick:s.tick,kind:String(kind).slice(0,32)};
 // Operational behavior needs, separate from care XP and signed/native progress.
 const needDelta={'care:feed':12,'care:rest':18,'training':-4}[kind]||0;
 s.energy=round(clamp(s.energy+needDelta));
 return s;
}
export function advanceCreature(session,environment){
 if(!session?.beast)return {ok:false,reason:'no beast'};
 const b=session.beast,id=b.qbeast?.profile?.id;
 const env=environmentFor(environment),cues=env.place+' '+(env.toy?'toy play':'')+' '+(env.sound?'sound listen':'');
 const associations=recallAssociations(session.mind,cues,12).filter(h=>ACTIONS.includes(h.word));
 const result=stepBehavior(b.behavior,b,{...env,associations});b.behavior=result.state;
 if(b.qbeast?.profile?.id!==id)throw Error('QBEAST identity changed');
 return {ok:true,...result};
}
export function recordCreatureExperience(session,feedback){
 if(!session?.beast)return {ok:false,reason:'no beast'};
 session.beast.behavior=feedbackBehavior(session.beast.behavior,session.beast,feedback);
 return {ok:true,preferences:session.beast.behavior.preferences};
}
/** Explicit keeper feedback about an action actually recorded by this core. */
export function encourageCurrentBehavior(session){
 const b=session?.beast,event=b?.behavior?.events?.at(-1);
 if(!event||!ACTIONS.includes(event.action)||!PLACES.includes(event.place))return {ok:false,reason:'Wait for a recorded activity first.'};
 recordCreatureExperience(session,{place:event.place,reward:1,kind:'keeper-encouragement'});
 observeText(session.mind,`${event.place} ${event.action}`,{seed:b.seed});
 b.behavior.memory.at(-1).action=event.action;
 return {ok:true,action:event.action,place:event.place};
}
