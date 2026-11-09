'use client';
// Mounted once in the root layout: fetches the RECORDED genesis once and starts the ONE world clock.
// It survives route changes, so Home, Tiny Universe and the Cage all read the same universe at the same tick.
import {useEffect} from 'react';
import {grow} from '@/lib/universe/tiny-universe.mjs';
import {oneWorldClock,currentWorldClock,whenWorldClock} from '@/lib/world/one-world-clock.mjs';
import {oneUniverseStateOn,browserSources,attachOneWorldRead,surfacesForPath} from '@/public/universe/one-universe-state.mjs';
export default function OneWorldProvider(){
 useEffect(()=>{if(currentWorldClock())return;let live=true;
  fetch('/universe/tiny-universe-genesis.json').then(r=>r.json()).then(g=>{if(!live||currentWorldClock())return;let st:any=null;try{st=localStorage;}catch{}
   oneWorldClock({genesis:g,grow,storage:st});window.dispatchEvent(new Event('beastbox:one-world'));}).catch(()=>{});
  return()=>{live=false;};},[]);
 useEffect(()=>{
  if(!oneUniverseStateOn(browserSources()))return;
  let stop=()=>{};let extraStop=()=>{};let dead=false;let queued=false;
  whenWorldClock().then(clock=>{
   if(dead)return;
   const apply=()=>{
    const surface=surfacesForPath(window.location.pathname).join('+');
    const nodes=[];
    for(const sel of ['[data-look-pedestal]','[data-pocket-dimension]','[data-ar-canvas]','[data-living-world]']){
     const el=document.querySelector(sel);if(el)nodes.push(el);
    }
    attachOneWorldRead({on:true,getClock:()=>clock.get(),node:document.documentElement,nodes,surface});
   };
   const schedule=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;if(!dead)apply();});};
   apply();
   stop=clock.subscribe(schedule);
   const watch=new MutationObserver(schedule);
   watch.observe(document.documentElement,{childList:true,subtree:true});
   extraStop=()=>watch.disconnect();
  });
  return()=>{dead=true;stop();extraStop();};
 },[]);
 return null;
}
