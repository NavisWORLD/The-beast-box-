'use client';
import {useEffect,useMemo,useState} from 'react';
import {talkPersona} from '../lib/companion/beast-talk.mjs';

const TARGET_KEY='beastbox.talkTarget.v1',COMPANION_KEY='beastbox.guestCompanionKey.v1',EVT='beastbox:talk-target';
export type TalkTarget='companion'|'zeref';
function read(k:string){try{return localStorage.getItem(k);}catch{return null;}}
function write(k:string,v:string){try{localStorage.setItem(k,v);}catch{/* optional */}}

/** Which creature the guest is talking to: their own companion or Zeref (bb-deada969). Shared across all talk surfaces. */
export function useTalkTarget(){
 // null = the guest never chose. Explicit choices are stored and always win.
 const [target,setTarget]=useState<TalkTarget|null>(null);
 useEffect(()=>{const sync=()=>{const v=read(TARGET_KEY);setTarget(v==='zeref'||v==='companion'?v:null);};sync();window.addEventListener(EVT,sync);window.addEventListener('storage',sync);return()=>{window.removeEventListener(EVT,sync);window.removeEventListener('storage',sync);};},[]);
 const choose=(t:TalkTarget)=>{write(TARGET_KEY,t);setTarget(t);window.dispatchEvent(new Event(EVT));};
 return [target,choose] as const;
}

/** One companion per guest: their saved Spark Beast (the one with memory) always wins; otherwise
 * the first Beast Cage creature this device picked stays theirs across pages. */
export function stableCompanionPersona(beast:any,profile:any){
 const a=beast?.genome?talkPersona({beast}):null;
 if(a){if(typeof window!=='undefined')write(COMPANION_KEY,a.key);return a;}
 return profile?talkPersona({cage:profile}):null;
}

export function useTalkPersona(beast:any,profile:any){
 const [target,choose]=useTalkTarget();
 const companion=useMemo(()=>stableCompanionPersona(beast,profile),[beast,profile]);
 const zeref=useMemo(()=>talkPersona({}),[]);
 // Unchosen default: a guest's own saved Spark Beast (it has their memory) talks to them;
 // a passing Beast Cage creature never impersonates the chat. Otherwise it is Zeref (bb-deada969).
 const effective:TalkTarget=target??(companion?.source==='spark'?'companion':'zeref');
 const persona=effective==='zeref'||!companion?zeref:companion;
 return {persona,companion,zeref,target:companion?effective:'zeref' as TalkTarget,choose};
}
