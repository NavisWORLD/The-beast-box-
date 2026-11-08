// Presentation tier for the Genesis look. Reads the existing pack; does not edit it.
// Phones default to MED. Software GL stays LOW. Reduced motion freezes motion elsewhere, not this default.
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

/** Saved override wins. Otherwise phones are MED and a desktop LOW pick lifts to HIGH. */
export function presentationTier(storage:Store,hints:Hints={}):Tier{
 const saved=readTierOverride(storage);
 if(saved)return saved as Tier;
 if(hints.softGL)return 'LOW';
 if(hints.phone)return 'MED';
 const auto=autoTier({...hints,phone:false,reducedMotion:false,softGL:false});
 if(auto==='LOW')return 'HIGH';
 return auto as Tier;
}

const ORDER:Tier[]=['LOW','MED','HIGH','GOD'];
/** Drop one tier when a 3s average exceeds 20ms. Never raises, and never above the user pick. */
export function dropTierIfSlow(tier:string,avgMs:number,userPick:string):Tier{
 const cap=(TIERS as readonly string[]).includes(userPick)?userPick as Tier:tier as Tier;
 const cur=(TIERS as readonly string[]).includes(tier)?tier as Tier:'MED';
 if(!(avgMs>20))return cur;
 const dropped=ORDER[Math.max(0,ORDER.indexOf(cur)-1)];
 return ORDER.indexOf(dropped)>ORDER.indexOf(cap)?cap:dropped;
}
