// Park is the default look (Cory, Nov 12 2026: upgrade the whole universe). Classic and Genesis stay selectable.
// All three are presentation choices and do not write world state.
// Park builds on Genesis: it draws the same Genesis ground, then grades it. Classic and Genesis are unchanged by it.
export const LOOKS=Object.freeze(['classic','genesis','park'] as const);
export type Look=(typeof LOOKS)[number];
export const LOOK_KEY='beastbox.look.v1';
export const DEFAULT_LOOK:Look='park';
export const LOOK_EVENT='beastbox:look';

type Store={getItem?(key:string):string|null;setItem?(key:string,value:string):void;removeItem?(key:string):void;key?(index:number):string|null;length?:number}|null|undefined;

export function isLook(v:unknown):v is Look{return v==='classic'||v==='genesis'||v==='park';}
/** Park draws on the Genesis ground. True for Genesis and Park. */
export function usesGenesisBase(v:unknown){return v==='genesis'||v==='park';}
export function readLook(storage:Store):Look{
 try{const v=storage?.getItem?.(LOOK_KEY);return isLook(v)?v:DEFAULT_LOOK;}catch{return DEFAULT_LOOK;}
}
export function writeLook(storage:Store,look:Look):Look{
 const next=isLook(look)?look:DEFAULT_LOOK;
 try{if(next===DEFAULT_LOOK)storage?.removeItem?.(LOOK_KEY);else storage?.setItem?.(LOOK_KEY,next);}catch{}
 /* tell the page skin (components/look-skin.tsx) on this tab; other tabs hear the storage event */
 try{const g=globalThis as {dispatchEvent?:(e:Event)=>boolean;CustomEvent?:typeof CustomEvent};if(g.dispatchEvent&&g.CustomEvent)g.dispatchEvent(new g.CustomEvent(LOOK_EVENT,{detail:next}));}catch{}
 return next;
}
export function lookLabel(look:Look){return look==='park'?'Look: Park':look==='genesis'?'Look: Genesis':'Look: Classic';}
/** Classic -> Genesis -> Park -> Classic. */
export function nextLook(look:Look):Look{return look==='classic'?'genesis':look==='genesis'?'park':'classic';}

/** The look currently saved on this page. Park (the default) when storage is missing. */
export function currentLook():Look{
 try{return readLook((globalThis as {localStorage?:Store}).localStorage);}catch{return DEFAULT_LOOK;}
}

/**
 * World snapshot: every stored key except the presentation look.
 * Switching look is allowed to change only LOOK_KEY.
 */
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
/** Pair a world value with a look without mutating the world. */
export function withLook<T>(world:T,look:Look):{world:T;look:Look}{
 return {world,look:isLook(look)?look:DEFAULT_LOOK};
}
