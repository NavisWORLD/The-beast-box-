/**
 * "Grow in the cosmos": the PUBLIC profile a player may opt in to share so the
 * scheduled loop can grow their beast server-side. Shared by the browser (Cage,
 * My Beast) and the API route, so both sides apply the same allowlist.
 *
 * Shared: beast id, display name, seed provenance (recorded backend/job/count
 * digest or classical seed), visual traits and game stats.
 * NEVER shared: chat, owner memory, user id, keeper names, voice/behaviour
 * internals, device data or anything else in the save.
 */
export const COSMOS_PROFILE_SCHEMA='cosmos-beast-public/v1';
const ID_RE=/^[a-z0-9][a-z0-9_-]{5,63}$/i;
const WORD=/^[a-z0-9 _-]{1,24}$/i;
const PRIVATE=/(?:api[_ -]?key|password|secret|token|credential|bearer|https?:|@|\bsk-)/i;
const n=(v,lo,hi)=>Number.isFinite(Number(v))?Math.min(hi,Math.max(lo,Number(v))):null;
const word=v=>typeof v==='string'&&WORD.test(v)?v:null;
const hex=(v,len=64)=>typeof v==='string'&&new RegExp(`^[0-9a-f]{${len}}$`).test(v)?v:null;
const STAT_KEYS=['hp','energy','signal','memory','resonance','agility','chaos','stability','curiosity','evolution'];

export function cosmosIdFor(raw){
 const s=String(raw||'').trim();
 if(ID_RE.test(s))return s.toLowerCase();
 const m=/^seed:([0-9a-f]{12,})$/i.exec(s);return m?('seed-'+m[1].slice(0,24).toLowerCase()):null;
}
function stats(src){
 const out={};for(const k of STAT_KEYS){const v=n(src?.[k],0,100);if(v!=null)out[k]=Math.round(v);}
 return out;
}

/** From a My Beast save (session.beast with a recorded-seed genome). */
export function publicProfileFromBeast(beast,{name}={}){
 if(!beast||!beast.genome)return null;
 const g=beast.genome,q=g.quantum||{};
 const id=cosmosIdFor(beast.qbeast?.profile?.id||beast.id||(g.seed?'seed:'+g.seed:''));
 return {schema:COSMOS_PROFILE_SCHEMA,id,name:String(name||beast.displayName||g.names?.['1']||'Beast').replace(/[^a-z0-9 _-]/gi,'').slice(0,24)||'Beast',
  provenance:{kind:'recorded-quantum-genome',backend:String(q.backend||''),job_id:String(q.job_id||''),counts_sha256:String(q.counts_sha256||''),seed:String(g.seed||'')},
  traits:{island:g.island,element:g.element,body:g.body,ears:g.ears,tail:g.tail,wings:g.wings,pattern:g.pattern,eye_style:g.eye_style,mouth:g.mouth,
   marginals:Array.isArray(q.marginals)?q.marginals.slice(0,8):[],entropy_norm:q.entropy_norm,stats:stats(g.stats)}};
}

/** From a Beast Cage classical-seeded creature. */
export function publicProfileFromCreature(c){
 if(!c||!c.id)return null;
 return {schema:COSMOS_PROFILE_SCHEMA,id:cosmosIdFor(c.id),name:String(c.name||'Beast').replace(/[^a-z0-9 _-]/gi,'').slice(0,24)||'Beast',
  provenance:{kind:'classical-seeded-game-generation',seed:String(c.seed||'').slice(0,64)},
  traits:{family:c.family,base_look:c.baseLook,hue_shift:c.appearance?.hueShift,glow:c.appearance?.glow,stats:stats(c.game?.stats)}};
}

/** Server-side gate: rebuild the profile from allowlisted fields only. -> {ok,profile}|{ok:false,error} */
export function validatePublicProfile(raw){
 if(!raw||typeof raw!=='object'||raw.schema!==COSMOS_PROFILE_SCHEMA)return {ok:false,error:'Not a public cosmos profile.'};
 if(JSON.stringify(raw).length>4000)return {ok:false,error:'Profile too large.'};
 const id=cosmosIdFor(raw.id);if(!id)return {ok:false,error:'Invalid beast id.'};
 const name=typeof raw.name==='string'?raw.name.trim():'';
 if(!WORD.test(name)||PRIVATE.test(name))return {ok:false,error:'Name must be 1-24 letters, numbers, spaces, _ or -.'};
 const pv=raw.provenance||{},t=raw.traits||{};
 let provenance,traits;
 if(pv.kind==='recorded-quantum-genome'){
  const backend=typeof pv.backend==='string'&&/^[a-z0-9._-]{2,40}$/i.test(pv.backend)?pv.backend:null,job=typeof pv.job_id==='string'&&/^[A-Za-z0-9_-]{4,64}$/.test(pv.job_id)?pv.job_id:null;
  const counts=hex(pv.counts_sha256),seed=hex(pv.seed,64)||(typeof pv.seed==='string'&&/^[0-9a-f]{16,128}$/.test(pv.seed)?pv.seed:null);
  if(!backend||!job||!seed)return {ok:false,error:'Recorded provenance needs backend, job id and seed.'};
  provenance={kind:pv.kind,backend,job_id:job,counts_sha256:counts,seed};
  const marg=Array.isArray(t.marginals)?t.marginals.slice(0,8).map(v=>n(v,0,1)).filter(v=>v!=null):[];
  traits={};for(const k of ['island','element','body','ears','tail','wings','pattern','eye_style','mouth']){const v=word(t[k]);if(v)traits[k]=v;}
  traits.marginals=marg;const en=n(t.entropy_norm,0,1);if(en!=null)traits.entropy_norm=en;traits.stats=stats(t.stats);
 }else if(pv.kind==='classical-seeded-game-generation'){
  const seed=typeof pv.seed==='string'&&pv.seed.length>=1&&pv.seed.length<=64&&!/[\u0000-\u001f]/.test(pv.seed)&&!PRIVATE.test(pv.seed)?pv.seed:null;
  if(!seed)return {ok:false,error:'Classical provenance needs its seed.'};
  provenance={kind:pv.kind,seed};
  traits={};for(const k of ['family','base_look']){const v=word(t[k]);if(v)traits[k]=v;}
  for(const k of ['hue_shift','glow']){const v=n(t[k],-360,360);if(v!=null)traits[k]=v;}
  traits.stats=stats(t.stats);
 }else return {ok:false,error:'Unknown provenance.'};
 if(!Object.keys(traits.stats||{}).length)return {ok:false,error:'Profile needs its game stats.'};
 return {ok:true,profile:{schema:COSMOS_PROFILE_SCHEMA,id,name,provenance,traits}};
}
