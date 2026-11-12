/** Deterministic creature emotions. Classical software, no model, no hidden time.
 * Inputs: the creature's recorded seed (genome derived from recorded historical IBM counts),
 * its own recorded experiences (keeper feedback memory, chat turns, energy) and archived
 * Rigetti QVM SIMULATOR growth. Same inputs always give the same emotions. Nothing here reads
 * the clock, so time passing while the page is closed cannot create feelings. */
export const EMOTION_SCHEMA='beastbox-emotion-v1';
export const EMOTIONS=['joy','curiosity','fear','calm','mischief'];
const clamp=n=>Math.max(0,Math.min(100,Math.round(Number.isFinite(n)?n:0)));
const EVENT={
 'care:pet':{joy:4,calm:2,fear:-3},'care:feed':{joy:3,calm:2,fear:-1},'care:rest':{calm:5,mischief:-2,fear:-1},'care:spark':{mischief:4,joy:2},
 'keeper-encouragement':{joy:3,fear:-1},
};
/** Visible choices each emotion makes. state is a habitat motion state already supported by habitatPose. */
export const CHOICES={
 joy:{state:'celebrate',motion:'bouncy hop',tone:'cheerful',line:'is bouncing with joy!'},
 curiosity:{state:'listen',motion:'lean-in and sniff',tone:'questioning',line:'wants to know what that was.'},
 fear:{state:'rest',motion:'curl up and hide',tone:'shy and quiet',line:'is a little scared and curls up.'},
 calm:{state:'idle',motion:'slow sway',tone:'soft and steady',line:'feels calm and steady.'},
 mischief:{state:'celebrate',motion:'zig-zag zoomies',tone:'teasing',line:'has a mischievous glint…'},
};
export function deriveEmotions(beast,{simGrowth=0,chatTurns=0}={}){
 const g=beast?.genome||{},q=g.quantum||{},t=g.inputs?.traits||{},temper=g.temperament||'';
 const ent=Math.max(0,Math.min(1,Number(q.entropy_norm)||0)),m0=Number(q.marginals?.[0]??.5);
 const why=[],e={joy:0,curiosity:0,fear:0,calm:0,mischief:0};
 const add=(k,v,reason)=>{if(!v)return;e[k]+=v;why.push({emotion:k,delta:Math.round(v*10)/10,reason});};
 // 1. Seed: recorded historical IBM hardware counts (fixed, not live).
 add('curiosity',30+40*ent,`seed counts are ${Math.round(ent*100)}% spread out (recorded IBM counts)`);
 add('calm',25+30*(1-ent)+(Number(t.calm)||0)*.2,`seed counts are ${Math.round((1-ent)*100)}% concentrated + calm drive ${t.calm??0}`);
 add('joy',30+(Number(t.spark)||0)*.2,`spark drive ${t.spark??0} at birth`);
 add('fear',10+30*Math.abs(m0-.5),`seed qubit 0 leaned ${m0>=.5?'1':'0'} (${Math.round(m0*100)}%)`);
 add('mischief',15+(['fang','w'].includes(g.mouth)?10:0),`born with a ${g.mouth||'plain'} mouth`);
 const tb={Playful:['mischief',12],Curious:['curiosity',10],Serene:['calm',12],Gentle:['joy',8],Fierce:['mischief',8],Bold:['joy',6],Dreamy:['fear',6],Steadfast:['calm',8]}[temper];
 if(tb)add(tb[0],tb[1],`${temper} temperament`);
 // 2. Its own recorded experiences, oldest first.
 const mem=Array.isArray(beast?.behavior?.memory)?beast.behavior.memory:[];
 for(const m of mem){
  if(m.kind==='training'){const r=Math.max(0,Math.min(1,Number(m.reward)||0));add('curiosity',3*r,'training round');add('joy',2*r,`training went ${Math.round(r*100)}%`);if(r<.5)add('fear',2,'training was hard');}
  else for(const [k,v] of Object.entries(EVENT[m.kind]||{}))add(k,v,m.kind.replace('care:','care: '));
 }
 const turns=Math.max(0,Math.min(20,Math.floor(Number(chatTurns)||0)));
 if(turns)add('curiosity',turns,`${turns} recorded chat turns`);
 const energy=Number(beast?.energy??100);
 if(energy<30){add('fear',6,`energy is low (${energy})`);add('calm',-6,'tired');}
 // 3. Archived Rigetti QVM SIMULATOR runs (SIMULATED, not hardware).
 const sg=Math.max(0,Math.min(1,Number(simGrowth)||0));
 if(sg){add('curiosity',10*sg,`SIMULATED Rigetti QVM growth ${Math.round(sg*100)}%`);add('mischief',6*sg,'SIMULATED Rigetti QVM growth');}
 const out=Object.fromEntries(EMOTIONS.map(k=>[k,clamp(e[k])]));
 const dominant=EMOTIONS.reduce((a,b)=>out[b]>out[a]?b:a);
 const top=why.filter(w=>w.emotion===dominant).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)).slice(0,3);
 return {schema:EMOTION_SCHEMA,...out,dominant,choice:CHOICES[dominant],why,topWhy:top,sources:{seed:'recorded historical IBM counts',experiences:mem.length,chatTurns:turns,simulator:sg?'SIMULATED Rigetti QVM':'none'}};
}
export function emotionLine(name,em){return `${name} ${em.choice.line}`;}
/** Diary entry for a real event only. Returns null if nothing changed. */
export function diaryEntry(before,after,event){
 if(!after||!event)return null;
 const changed=EMOTIONS.filter(k=>before&&before[k]!==after[k]).map(k=>`${k} ${before[k]}→${after[k]}`);
 return {event:String(event).slice(0,40),dominant:after.dominant,choice:after.choice.motion,changed,why:after.topWhy.map(w=>w.reason)};
}
/* ---------------- opt-in feeling rule: confused (owner-named, 2026-10-29) ----------------
 * PROVISIONAL until Cory's full_system.py definition arrives (emotional_api/full_system.py is not in
 * phera-ra/QC67_cosmo yet; no "confused" definition exists there). Replace the trigger with his when it lands.
 * Cory defined "confused" as one of Zeref's feeling states. Like the other new CST rules it is
 * OPT-IN: deriveEmotions() and EMOTIONS are unchanged, and confusedState() returns null unless
 * the caller passes {confused:true}. Deterministic: no clock, no randomness.
 * Trigger: a drill marked 'miss', OR a target word that does not appear (whole word,
 * case-insensitive) in his reply. Label DERIVED: computed from his own sensor rules, not measured. */
export const OPT_IN_FEELINGS=Object.freeze(['confused']);
const wordIn=(word,text)=>{
 const w=String(word||'').trim().toLowerCase();if(!w)return null;
 const esc=w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 return new RegExp(`(^|[^\\p{L}\\p{N}])${esc}($|[^\\p{L}\\p{N}])`,'u').test(String(text||'').toLowerCase());
};
/** @param {{reply?:string,target?:string|null,drill?:string|null}} [input] @param {{confused?:boolean}|null} [opts] */
export function confusedState({reply='',target=null,drill=null}={},opts=null){
 if(!opts||opts.confused!==true)return null;
 const why=[];
 if(drill==='miss')why.push('drill marked a miss');
 const has=wordIn(target,reply);
 if(has===false)why.push(`target word "${String(target).trim().toLowerCase()}" not in his reply`);
 return {feeling:'confused',active:why.length>0,why,label:'DERIVED',
  source:'Zeref\'s own feeling rules (lib/companion/emotion.mjs confusedState)'};
}
