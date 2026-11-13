// Presentation tier for the Genesis look. Reads the existing pack; does not edit it.
// Phones default to MED. Desktops default to HIGH (a GOD machine stays GOD).
// A saved override still wins. Software GL does not pin the default: a real
// frame-time average drops the live tier, and that drop is not saved.
import {autoTier,readTierOverride,TIERS} from '../universe/post-tiers.mjs';

export type Tier='LOW'|'MED'|'HIGH'|'GOD';
export const GENESIS_BUDGET=Object.freeze({
 LOW:{dpr:1,tris:60000,rings:3,shadow:0},
 MED:{dpr:1.5,tris:150000,rings:4,shadow:1024},
 HIGH:{dpr:2,tris:400000,rings:5,shadow:2048},
 GOD:{dpr:2,tris:1000000,rings:6,shadow:2048},
});

type Hints={phone?:boolean;cores?:number;memoryGB?:number;reducedMotion?:boolean;softGL?:boolean};
type Store={getItem?(key:string):string|null}|null|undefined;

export function budgetFor(tier:string){
 const t=(TIERS as readonly string[]).includes(tier)?tier as Tier:'MED';
 return GENESIS_BUDGET[t];
}

/** Saved override wins. Otherwise a phone is MED and a desktop is HIGH, or GOD when the machine already is. */
export function presentationTier(storage:Store,hints:Hints={}):Tier{
 const saved=readTierOverride(storage);
 if(saved)return saved as Tier;
 if(hints.phone)return 'MED';
 const auto=autoTier({...hints,phone:false,reducedMotion:false,softGL:false});
 if(auto==='GOD')return 'GOD';
 return 'HIGH';
}

const ORDER:Tier[]=['LOW','MED','HIGH','GOD'];
/** Drop one tier when a 3s average exceeds 20ms. Never raises, and never above the user pick. */
export function dropTierIfSlow(tier:string,avgMs:number,userPick:string):Tier{
 const cap=(TIERS as readonly string[]).includes(userPick)?userPick as Tier:tier as Tier;
 const cur=(TIERS as readonly string[]).includes(tier)?tier as Tier:'MED';
 if(!(avgMs>20))return cur;
 if(cur==='MED'&&!(avgMs>34))return cur; /* Cory Nov 12: MED is the floor for a modern phone; only a really slow run (avg over 34 ms, under ~30 fps) drops MED to LOW */
 const dropped=ORDER[Math.max(0,ORDER.indexOf(cur)-1)];
 return ORDER.indexOf(dropped)>ORDER.indexOf(cap)?cap:dropped;
}

/** Apply dropTierIfSlow once a real frame sample covers the window. Does not write storage. */
export function considerDrop(tier:string,userPick:string,frameMs:number[],windowMs=3000):{tier:Tier;consumed:boolean}{
 let total=0;
 for(const ms of frameMs)total+=ms;
 const cur=(TIERS as readonly string[]).includes(tier)?tier as Tier:'MED';
 if(!(total>=windowMs)||frameMs.length<20)return {tier:cur,consumed:false};
 return {tier:dropTierIfSlow(cur,total/frameMs.length,userPick),consumed:true};
}
