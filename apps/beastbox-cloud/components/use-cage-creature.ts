'use client';
import {useCallback,useEffect,useState} from 'react';
import {CAGE_CREATURE_EVENT,CAGE_CREATURE_KEY,readCageCreature,writeCageCreature} from '../lib/world/cage-creature.mjs';
/** The shared "Creature" switch: ON by default, remembered on this device, the same everywhere it is shown. */
export function useCageCreature():[boolean,(on:boolean)=>void]{
 const [on,setOn]=useState(true);
 useEffect(()=>{
  const sync=()=>setOn(readCageCreature(window.localStorage));
  sync();
  const onStorage=(e:StorageEvent)=>{if(!e.key||e.key===CAGE_CREATURE_KEY)sync();};
  window.addEventListener(CAGE_CREATURE_EVENT,sync);window.addEventListener('storage',onStorage);
  return()=>{window.removeEventListener(CAGE_CREATURE_EVENT,sync);window.removeEventListener('storage',onStorage);};
 },[]);
 useEffect(()=>{document.documentElement.setAttribute('data-cage-creature',on?'on':'off');},[on]);
 const set=useCallback((v:boolean)=>{writeCageCreature(window.localStorage,v);setOn(v);window.dispatchEvent(new Event(CAGE_CREATURE_EVENT));},[]);
 return [on,set];
}
