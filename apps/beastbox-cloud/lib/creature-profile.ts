/**
 * Cosmic Genesis v1: deliberately GAME-ONLY generated characters.
 *
 * No user profile, backend memory, model weights, physical sensors, quantum
 * measurements or privileged permissions are consumed by this module.
 * The randomness is classical, deterministic, versioned and domain-separated.
 */
export const GENESIS_VERSION=1 as const;
export const GENESIS_SCHEMA='beast-cage-creature-v1' as const;
export const FAMILIES=['nebula','aurora','void','plasma','memory','signal','starlight'] as const;
export type Family=typeof FAMILIES[number];
export type BaseLook='nebula'|'aurora'|'starlight';
export const STAT_NAMES=[
 'hp','energy','signal','memory','resonance','agility',
 'chaos','stability','curiosity','evolution'
] as const;
export type StatName=typeof STAT_NAMES[number];
export type GameStats=Record<StatName,number>;
export type Temperament={
 curiosity:number; energy:number; playfulness:number; caution:number; independence:number
};
export type CreatureProfile={
 schema:typeof GENESIS_SCHEMA;
 version:typeof GENESIS_VERSION;
 id:string;
 seed:string;
 name:string;
 family:Family;
 baseLook:BaseLook;
 appearance:{
  hueShift:number;
  glow:number;
  finPattern:number;
  haloPattern:number;
  constellation:number;
 };
 temperament:Temperament;
 game:{stats:GameStats;level:number;experience:number};
 provenance:'classical-seeded-game-generation';
};

// Domain separation: altering art rules cannot silently reroll stats.
function hash(input:string):number{
 let result=2166136261;
 const bytes=new TextEncoder().encode(input);
 for(const byte of bytes){result^=byte;result=Math.imul(result,16777619);}
 return result>>>0;
}
function generator(seed:string,domain:string){
 let state=hash(GENESIS_VERSION+'|'+domain+'|'+seed)||0x6d2b79f5;
 return function():number{
  state^=state<<13;state^=state>>>17;state^=state<<5;
  return (state>>>0)/4294967296;
 };
}
export function normalizeSeed(input:string):string{
 if(typeof input!=='string')throw new Error('Seed must be text');
 const seed=input.trim().normalize('NFC');
 if(seed.length<1||seed.length>64)throw new Error('Seed must have 1–64 characters');
 if(/[\u0000-\u001f\u007f]/u.test(seed))throw new Error('Control characters cannot be used as seeds');
 return seed;
}
export function stableCreatureId(seed:string){
 return 'bb-'+hash('identity|'+GENESIS_VERSION+'|'+normalizeSeed(seed)).toString(16).padStart(8,'0');
}
const LOOK:Record<Family,BaseLook>={
 nebula:'nebula',aurora:'aurora',void:'nebula',plasma:'starlight',
 memory:'starlight',signal:'aurora',starlight:'starlight'
};
const HUES:Record<Family,number>={
 nebula:0,aurora:0,void:83,plasma:-92,memory:29,signal:45,starlight:0
};
const STEMS=['Neb','Lum','Ori','Vexa','Astr','Phera','Glima','Zori','Mira','Cosmi'];
const ENDS=['by','io','ix','a','on','ora','u','ra','yx','iri'];
export function generateCreature(input:string,chosenFamily?:Family):CreatureProfile{
 const seed=normalizeSeed(input);
 if(chosenFamily!==undefined&&!FAMILIES.includes(chosenFamily))throw new Error('Unknown family');
 const art=generator(seed,'appearance');
 const statsRandom=generator(seed,'stats');
 const traitsRandom=generator(seed,'temperament');
 const family=chosenFamily??FAMILIES[Math.floor(art()*FAMILIES.length)];
 const look=LOOK[family];
 const hueShift=Math.max(-180,Math.min(180,HUES[family]+Math.floor(art()*21)-10));
 const stats={} as GameStats;
 for(const key of STAT_NAMES)stats[key]=50;
 // Conservation of a balanced 500-point budget: no unbounded power from rarity.
 for(let i=0;i<270;i++){
  const from=Math.floor(statsRandom()*STAT_NAMES.length);
  const to=Math.floor(statsRandom()*STAT_NAMES.length);
  if(from!==to&&stats[STAT_NAMES[from]]>20&&stats[STAT_NAMES[to]]<80){
   stats[STAT_NAMES[from]]--;stats[STAT_NAMES[to]]++;
  }
 }
 const traits=()=>Math.floor(20+traitsRandom()*61);
 const temperament:Temperament={
  curiosity:traits(),energy:traits(),playfulness:traits(),caution:traits(),independence:traits()
 };
 const naming=generator(seed,'name');
 const name=STEMS[Math.floor(naming()*STEMS.length)]+ENDS[Math.floor(naming()*ENDS.length)];
 return {
  schema:GENESIS_SCHEMA,version:GENESIS_VERSION,id:stableCreatureId(seed),seed,name,
  family,baseLook:look,
  appearance:{
   hueShift,glow:Math.round(40+art()*60),finPattern:Math.floor(art()*4),
   haloPattern:Math.floor(art()*3),constellation:Math.floor(art()*65536)
  },
  temperament,game:{stats,level:1,experience:0},provenance:'classical-seeded-game-generation'
 };
}
export function validCreature(value:unknown):value is CreatureProfile{
 if(!value||typeof value!=='object'||Array.isArray(value))return false;
 const x=value as Partial<CreatureProfile>;
 if(x.schema!==GENESIS_SCHEMA||x.version!==GENESIS_VERSION||!x.seed||typeof x.seed!=='string'||!FAMILIES.includes(x.family as Family))return false;
 let expected:CreatureProfile;
 try{expected=generateCreature(x.seed,x.family);}catch{return false;}
 if(x.id!==expected.id||x.baseLook!==expected.baseLook||typeof x.name!=='string'||x.name.length>40)return false;
 if(x.provenance!==expected.provenance)return false;
 if(!x.appearance||!Number.isInteger(x.appearance.hueShift)||Math.abs(x.appearance.hueShift)>180)return false;
 const game=x.game;if(!game)return false;
 const stats=game.stats;
 if(!stats||!Number.isInteger(game.level)||game.level<1||game.level>100)return false;
 if(!Number.isInteger(game.experience)||game.experience<0||game.experience>1000000)return false;
 if(STAT_NAMES.some(k=>!Number.isInteger(stats[k])||stats[k]<20||stats[k]>80))return false;
 if(STAT_NAMES.reduce((n,k)=>n+stats[k],0)!==500)return false;
 const t=x.temperament;
 if(!t||(['curiosity','energy','playfulness','caution','independence'] as const).some(k=>!Number.isInteger(t[k])||t[k]<20||t[k]>80))return false;
 return true;
}
export type AmbientAction='hover'|'orbit'|'perch'|'rest';
/**
 * A classical, stateless weighted game-animation selector; no quantum claim
 * or authority. Source key includes tick so repeated replay is reproducible.
 */
export function pickAmbientAction(profile:CreatureProfile,tick:number):AmbientAction{
 if(!validCreature(profile))throw new Error('Invalid character');
 if(!Number.isSafeInteger(tick)||tick<0)throw new Error('Invalid behavior tick');
 const random=generator(profile.seed,'behavior|'+tick);
 const t=profile.temperament;
 const weights=[
  30+t.energy,
  20+t.playfulness,
  20+t.curiosity,
  20+t.caution+t.independence
 ];
 const total=weights.reduce((a,b)=>a+b,0);
 let selected=random()*total;
 const actions:AmbientAction[]=['hover','orbit','perch','rest'];
 for(let i=0;i<actions.length;i++){selected-=weights[i];if(selected<0)return actions[i];}
 return 'rest';
}
