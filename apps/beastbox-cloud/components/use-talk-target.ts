'use client';
import {useEffect,useMemo,useState} from 'react';
import {talkPersona} from '../lib/companion/beast-talk.mjs';

const TARGET_KEY='beastbox.talkTarget.v1',COMPANION_KEY='beastbox.guestCompanionKey.v1',EVT='beastbox:talk-target';
export type TalkTarget='companion'|'zeref';
function read(k:string){try{return localStorage.getItem(k);}catch{return null;}}
function write(k:string,v:string){try{localStorage.setItem(k,v);}catch{/* optional */}}

/** Which creature the guest is talking to: their own companion or Zeref (bb-deada969). Shared across all talk surfaces. */
export function useTalkTarget(){
 const [target,setTarget]=useState<TalkTarget>('companion');
 useEffect(()=>{const sync=()=>setTarget(read(TARGET_KEY)==='zeref'?'zeref':'companion');sync();window.addEventListener(EVT,sync);window.addEventListener('storage',sync);return()=>{window.removeEventListener(EVT,sync);window.removeEventListener('storage',sync);};},[]);
 const choose=(t:TalkTarget)=>{write(TARGET_KEY,t);setTarget(t);window.dispatchEvent(new Event(EVT));};
 return [target,choose] as const;
}

/** One stable companion per guest: the first companion seen on this device stays theirs across pages. */
export function stableCompanionPersona(beast:any,profile:any){
 const a=beast?.genome?talkPersona({beast}):null,b=profile?talkPersona({cage:profile}):null;
 if(!a&&!b)return null;
 const stored=read(COMPANION_KEY);
 if(stored&&a?.key===stored)return a;if(stored&&b?.key===stored)return b;
 const pick=(a||b)!;
 if(typeof window!=='undefined')write(COMPANION_KEY,pick.key);
 return pick;
}

export function useTalkPersona(beast:any,profile:any){
 const [target,choose]=useTalkTarget();
 const companion=useMemo(()=>stableCompanionPersona(beast,profile),[beast,profile]);
 const zeref=useMemo(()=>talkPersona({}),[]);
 const persona=target==='zeref'||!companion?zeref:companion;
 return {persona,companion,zeref,target:companion?target:'zeref' as TalkTarget,choose};
}
