// Park is the one look (Cory, Nov 12 2026: "we are polishing and upgrading the graphics overall").
// There is no look choice any more: no toggle, no Settings select, and no saved look. Park draws the Genesis ground
// (lib/look/attach.ts) and grades it (lib/look/park.ts). The look is presentation only and never writes world state.
// Classic and Genesis are gone as looks. Genesis lives on only as the ground Park is built on (lib/look/attach.ts).
export const LOOKS=Object.freeze(['park'] as const);
export type Look=(typeof LOOKS)[number];
/** Legacy key from the old look choice. Read only to clear it. */
export const LOOK_KEY='beastbox.look.v1';
export const DEFAULT_LOOK:Look='park';
export const PARK_ONLY=true;

type Store={getItem?(key:string):string|null;setItem?(key:string,value:string):void;removeItem?(key:string):void;key?(index:number):string|null;length?:number}|null|undefined;

export function isLook(v:unknown):v is Look{return v==='park';}
/** Park draws on the Genesis ground. Kept for the lower-level modules; true only for Park. */
export function usesGenesisBase(v:unknown){return v==='park';}
/** Always Park. A look saved by the old chooser is cleared, never applied. */
export function readLook(storage:Store):Look{
 try{if(storage?.getItem?.(LOOK_KEY)!=null)storage?.removeItem?.(LOOK_KEY);}catch{}
 return DEFAULT_LOOK;
}
/** The look on this page: Park. */
export function currentLook():Look{return DEFAULT_LOOK;}

/** World snapshot: every stored key except the legacy look key. */
export function snapshotWorld(storage:Store):Record<string,string|null>{
 const out:Record<string,string|null>={};
 try{
  const n=storage?.length||0;
  for(let i=0;i<n;i++){
   const k=storage?.key?.(i);
   if(!k||k===LOOK_KEY)continue;
   out[k]=storage?.getItem?.(k)??null;
  }
 }catch{}
 return out;
}
/** Pair a world value with the look without mutating the world. */
export function withLook<T>(world:T,look:Look=DEFAULT_LOOK):{world:T;look:Look}{
 return {world,look:isLook(look)?look:DEFAULT_LOOK};
}
