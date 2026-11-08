// Classic stays the default. Genesis is a presentation choice and does not write world state.
export const LOOKS=Object.freeze(['classic','genesis'] as const);
export type Look=(typeof LOOKS)[number];
export const LOOK_KEY='beastbox.look.v1';
export const DEFAULT_LOOK:Look='classic';
export const LOOK_EVENT='beastbox:look';

type Store={getItem?(key:string):string|null;setItem?(key:string,value:string):void;removeItem?(key:string):void;key?(index:number):string|null;length?:number}|null|undefined;

export function isLook(v:unknown):v is Look{return v==='classic'||v==='genesis';}
export function readLook(storage:Store):Look{
 try{const v=storage?.getItem?.(LOOK_KEY);return isLook(v)?v:DEFAULT_LOOK;}catch{return DEFAULT_LOOK;}
}
export function writeLook(storage:Store,look:Look):Look{
 const next=isLook(look)?look:DEFAULT_LOOK;
 try{if(next===DEFAULT_LOOK)storage?.removeItem?.(LOOK_KEY);else storage?.setItem?.(LOOK_KEY,next);}catch{}
 return next;
}
export function lookLabel(look:Look){return look==='genesis'?'Look: Genesis':'Look: Classic';}
export function nextLook(look:Look):Look{return look==='genesis'?'classic':'genesis';}

/** The look currently saved on this page. Classic when storage is missing. */
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
