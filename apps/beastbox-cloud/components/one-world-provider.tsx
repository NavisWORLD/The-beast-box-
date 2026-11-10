'use client';
// Mounted once in the root layout: fetches the RECORDED genesis once and starts the ONE world clock.
// It survives route changes, so Home, Tiny Universe and the Cage all read the same universe at the same tick.
import {useEffect} from 'react';
import {grow} from '@/lib/universe/tiny-universe.mjs';
import {oneWorldClock,currentWorldClock,whenWorldClock} from '@/lib/world/one-world-clock.mjs';
import {oneUniverseStateOn,browserSources,beginSurfaceRead,surfacesForPath} from '@/public/universe/one-universe-state.mjs';
import {pageTickOn,pageCamerasOn} from '@/public/universe/one-universe-gate.mjs';
export default function OneWorldProvider(){
 useEffect(()=>{if(currentWorldClock())return;let live=true;
  fetch('/universe/tiny-universe-genesis.json').then(r=>r.json()).then(g=>{if(!live||currentWorldClock())return;let st:any=null;try{st=localStorage;}catch{}
   oneWorldClock({genesis:g,grow,storage:st});window.dispatchEvent(new Event('beastbox:one-world'));}).catch(()=>{});
  return()=>{live=false;};},[]);
 useEffect(()=>{
  // The page root carries the live read on each clock tick. Surface nodes are stamped when they
  // appear. Rewriting them on every mutation forced a layout of the cage on the same frames the
  // pocket paints, so a smooth scroll to the forge never finished and the creator grid took the hit.
  const surfaceSelectors=['[data-look-pedestal]','[data-pocket-dimension]','[data-ar-canvas]','[data-living-world]'];
  let stampSurfaces=false;
  return beginSurfaceRead({
   on:oneUniverseStateOn(browserSources()),
   whenClock:()=>whenWorldClock(),
   readNode:()=>document.documentElement,
   nodesFor:()=>{
    if(!stampSurfaces)return [];
    const nodes=[];
    for(const sel of surfaceSelectors){const el=document.querySelector(sel);if(el)nodes.push(el);}
    return nodes;
   },
   surfaceFor:()=>surfacesForPath(window.location.pathname).join('+'),
   subscribe:(clock:any,apply:()=>void)=>clock.subscribe(()=>{stampSurfaces=false;apply();}),
   observe:(apply:()=>void)=>{
    const stamp=()=>{stampSurfaces=true;try{apply();}finally{stampSurfaces=false;}};
    const watch=new MutationObserver((records)=>{
     for(const record of records){
      for(const node of record.addedNodes){
       if(!(node instanceof Element))continue;
       const found=surfaceSelectors.some(sel=>node.matches(sel)||(node.firstElementChild&&node.querySelector(sel)));
       if(found){stamp();return;}
      }
     }
    });
    watch.observe(document.documentElement,{childList:true,subtree:true});
    stamp();
    return()=>watch.disconnect();
   },
  });
 },[]);
 useEffect(()=>{
  const sources=browserSources();
  const envOn=String(sources.env||'').split(',').some(part=>part.trim()==='tick');
  if(!envOn&&!pageTickOn(sources))return;
  let live=true;let stop=()=>{};
  import('@/public/universe/one-universe-tick.mjs').then(mod=>{
   if(!live||!mod.browserTickOn())return;
   stop=mod.followUniverseTick({
    on:true,
    node:document.documentElement,
    readClock:()=>currentWorldClock()||mod.storedUniverseClock(sources.storage),
    listen:(bind:()=>void)=>{const onReady=()=>bind();window.addEventListener('beastbox:one-world',onReady);return()=>window.removeEventListener('beastbox:one-world',onReady);},
   });
  }).catch(()=>{});
  return()=>{live=false;stop();};
 },[]);
 useEffect(()=>{
  const sources=browserSources();
  const envOn=String(sources.env||'').split(',').some(part=>part.trim()==='cameras');
  if(!envOn&&!pageCamerasOn(sources))return;
  let live=true;let stop=()=>{};
  import('@/public/universe/one-universe-cameras.mjs').then(mod=>{
   if(!live||!mod.browserCamerasOn())return;
   const apply=()=>{
    let stored:string|null=null;
    try{stored=localStorage.getItem(mod.CAMERA_STORAGE);}catch{}
    mod.publishUniverseCamera({on:true,path:location.pathname,stored,node:document.documentElement,clock:currentWorldClock()});
   };
   apply();
   let unsub=()=>{};
   const bind=()=>{unsub();const clock=currentWorldClock();unsub=clock&&typeof clock.subscribe==='function'?clock.subscribe(apply):()=>{};apply();};
   bind();
   const onReady=()=>bind();
   window.addEventListener('beastbox:one-world',onReady);
   window.addEventListener('beastbox:universe-camera',onReady);
   stop=()=>{unsub();window.removeEventListener('beastbox:one-world',onReady);window.removeEventListener('beastbox:universe-camera',onReady);};
  }).catch(()=>{});
  return()=>{live=false;stop();};
 },[]);
 return null;
}
