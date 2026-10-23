'use client';
import {useEffect,useState} from 'react';
import {activeBeastName} from '../lib/companion/beast-name.mjs';
/** The active beast's display name from the single source of truth; updates on spark selection, storage and session changes. */
export function useActiveBeastName():string|null{
 const [name,setName]=useState<string|null>(null);
 useEffect(()=>{const sync=()=>{try{setName(activeBeastName(localStorage).name);}catch{}};sync();
  const evs=['storage','beastbox:spark-selected','beastbox:session-changed','focus'];evs.forEach(e=>window.addEventListener(e,sync));const iv=setInterval(sync,4000);
  return()=>{evs.forEach(e=>window.removeEventListener(e,sync));clearInterval(iv);};},[]);
 return name;}
