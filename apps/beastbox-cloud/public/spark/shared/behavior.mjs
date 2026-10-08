/** Bounded deterministic companion behavior. All runtime actions are classical software. */
export const BEHAVIOR_SCHEMA='beastbox-behavior-v1';
export const ACTIONS=['rest','explore','inspect','play','wander','listen','idle'];
const clamp=(n,lo=0,hi=100)=>Math.max(lo,Math.min(hi,Number.isFinite(Number(n))?Number(n):lo));
const round=n=>Math.round(n*1000)/1000;
const hash=s=>{let h=2166136261;for(const c of String(s))h=Math.imul(h^c.charCodeAt(0),16777619);return h>>>0;};
const seedOf=b=>String(b?.genome?.seed||b?.seed||'');
export function createBehavior(beast){
 const seed=seedOf(beast);
 if(!/^[a-f0-9]{16,128}$/i.test(seed))throw Error('Verified genesis seed required');
 const t=beast?.genome?.t||{};
 return {schema:BEHAVIOR_SCHEMA,seed,tick:0,energy:clamp(beast?.energy??100),curiosity:round(clamp(25+clamp(t.spark??50)*.5+clamp(t.focus??50)*.2)),preferences:{grove:0,nest:0,shore:0,observatory:0},position:{x:.5,y:.5},lastAction:'idle',memory:[],events:[]};
}
export function validateBehavior(value,beast){
 return value?.schema===BEHAVIOR_SCHEMA && value.seed===seedOf(beast) ? value : createBehavior(beast);
}
export function stepBehavior(value,beast,environment={}){
 const s=structuredClone(validateBehavior(value,beast));
 const place=['grove','nest','shore','observatory'].includes(environment.place)?environment.place:'grove';
 const sound=clamp(environment.sound,0,1),toy=clamp(environment.toy,0,1),attention=clamp(environment.attention,0,1),comfort=clamp(environment.comfort??.5,0,1);
 const memoryBonus=clamp(s.preferences[place]??0,-8,8)/8,energy=s.energy,curiosity=s.curiosity;
 const scores={rest:1+(100-energy)/30+comfort,explore:1+curiosity/45+memoryBonus,inspect:1+curiosity/65+toy*2,play:1+toy*2+attention+memoryBonus/2,wander:1+energy/75,listen:1+sound*3+attention,idle:1};
 const weights=ACTIONS.map(a=>Math.max(.05,scores[a])),total=weights.reduce((a,b)=>a+b,0);
 const roll=hash(s.seed+':behavior:'+s.tick)/4294967296*total;
 let running=0,action='idle';for(let i=0;i<weights.length;i++){running+=weights[i];if(roll<running){action=ACTIONS[i];break;}}
 const delta={rest:7,explore:-2.4,inspect:-1.2,play:-2,wander:-1.5,listen:-.6,idle:.25};
 s.energy=round(clamp(energy+delta[action]));
 s.curiosity=round(clamp(curiosity+(action==='explore'||action==='inspect'?-1.6:.5)));
 if(['explore','wander','inspect','play'].includes(action)){
  const dx=((hash(s.seed+':x:'+s.tick)%201)-100)/2000,dy=((hash(s.seed+':y:'+s.tick)%201)-100)/2000;
  s.position={x:round(clamp(s.position.x+dx,.05,.95)),y:round(clamp(s.position.y+dy,.05,.95))};
 }
 const event={tick:s.tick,kind:'behavior',place,action,input:{energy,curiosity,sound,toy,attention,comfort,memoryBonus},scores:Object.fromEntries(ACTIONS.map(a=>[a,round(scores[a])])),result:{energy:s.energy,curiosity:s.curiosity,position:{...s.position}}};
 s.tick++;s.lastAction=action;s.events=[...s.events,event].slice(-32);
 return {state:s,event};
}
export function feedbackBehavior(value,beast,{place='grove',reward=0,kind='interaction'}={}){
 const s=structuredClone(validateBehavior(value,beast));
 if(!['grove','nest','shore','observatory'].includes(place))throw Error('Unknown environment');
 const r=clamp(reward,-1,1);
 s.preferences[place]=round(clamp(s.preferences[place]+r,-8,8));
 s.memory=[...s.memory,{tick:s.tick,kind:String(kind).slice(0,32),place,reward:r}].slice(-24);
 return s;
}
export function advanceCreature(session,environment){
 if(!session?.beast)return {ok:false,reason:'no beast'};
 const b=session.beast,id=b.qbeast?.profile?.id;
 const result=stepBehavior(b.behavior,b,environment);b.behavior=result.state;
 if(b.qbeast?.profile?.id!==id)throw Error('QBEAST identity changed');
 return {ok:true,...result};
}
export function recordCreatureExperience(session,feedback){
 if(!session?.beast)return {ok:false,reason:'no beast'};
 session.beast.behavior=feedbackBehavior(session.beast.behavior,session.beast,feedback);
 return {ok:true,preferences:session.beast.behavior.preferences};
}
