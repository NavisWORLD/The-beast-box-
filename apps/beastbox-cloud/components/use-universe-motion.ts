'use client';
import {useEffect,useState} from 'react';

export const REDUCED_MOTION_KEY='beastbox-reduced-motion-v1';
export const MOTION_EVENT='beastbox:motion-changed';

/** Browser preference only. The OS request always takes precedence. */
export function useUniverseMotion(){
 const [state,setState]=useState({reduced:false,systemReduced:false,preference:false});
 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const update=(event?:Event)=>{
   let preference=false;
   try{preference=localStorage.getItem(REDUCED_MOTION_KEY)==='true';}catch{/* optional persistence */}
   if(event instanceof CustomEvent&&typeof event.detail?.preference==='boolean')preference=event.detail.preference;
   const reduced=media.matches||preference;
   document.documentElement.dataset.beastboxReducedMotion=String(reduced);
   setState({reduced,systemReduced:media.matches,preference});
  };
  const storage=(event:StorageEvent)=>{if(event.key===REDUCED_MOTION_KEY)update();};
  update();media.addEventListener('change',update);
  window.addEventListener(MOTION_EVENT,update);window.addEventListener('storage',storage);
  return()=>{media.removeEventListener('change',update);window.removeEventListener(MOTION_EVENT,update);window.removeEventListener('storage',storage);};
 },[]);
 const save=(preference:boolean)=>{
  let saved=true;
  try{localStorage.setItem(REDUCED_MOTION_KEY,String(preference));}catch{saved=false;}
  const systemReduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  setState({preference,systemReduced,reduced:systemReduced||preference});
  document.documentElement.dataset.beastboxReducedMotion=String(systemReduced||preference);
  window.dispatchEvent(new CustomEvent(MOTION_EVENT,{detail:{preference,reduced:systemReduced||preference}}));
  return saved;
 };
 return {...state,save};
}
