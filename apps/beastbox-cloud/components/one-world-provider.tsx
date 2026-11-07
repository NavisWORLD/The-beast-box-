'use client';
// Mounted once in the root layout: fetches the RECORDED genesis once and starts the ONE world clock.
// It survives route changes, so Home, Tiny Universe and the Cage all read the same universe at the same tick.
import {useEffect} from 'react';
import {grow} from '@/lib/universe/tiny-universe.mjs';
import {oneWorldClock,currentWorldClock} from '@/lib/world/one-world-clock.mjs';
export default function OneWorldProvider(){
 useEffect(()=>{if(currentWorldClock())return;let live=true;
  fetch('/universe/tiny-universe-genesis.json').then(r=>r.json()).then(g=>{if(!live||currentWorldClock())return;let st:any=null;try{st=localStorage;}catch{}
   oneWorldClock({genesis:g,grow,storage:st});window.dispatchEvent(new Event('beastbox:one-world'));}).catch(()=>{});
  return()=>{live=false;};},[]);
 return null;
}
