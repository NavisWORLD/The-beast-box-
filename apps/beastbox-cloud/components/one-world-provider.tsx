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
 useEffect(()=>beginSurfaceRead({
  on:oneUniverseStateOn(browserSources()),
  whenClock:()=>whenWorldClock(),
  readNode:()=>document.documentElement,
  nodesFor:()=>{const nodes=[];for(const sel of ['[data-look-pedestal]','[data-pocket-dimension]','[data-ar-canvas]','[data-living-world]']){const el=document.querySelector(sel);if(el)nodes.push(el);}return nodes;},
  surfaceFor:()=>surfacesForPath(window.location.pathname).join('+'),
  subscribe:(clock:any,apply:()=>void)=>clock.subscribe(apply),
  observe:(apply:()=>void)=>{let queued=false;const schedule=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;apply();});};const watch=new MutationObserver(schedule);watch.observe(document.documentElement,{childList:true,subtree:true});return()=>watch.disconnect();},
 }),[]);
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
