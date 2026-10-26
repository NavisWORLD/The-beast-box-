'use client';
import {useEffect,useState} from 'react';
import {listCreations,type Creation} from '../lib/companion/creations.mjs';
import {SESSION_KEY} from '../lib/companion/beast-name.mjs';
/** Every creation (active beast, saved beasts, artist residents) from the same saved session the rest of the site reads. */
export function readCreations():Creation[]{try{const raw=localStorage.getItem(SESSION_KEY);return listCreations(raw?JSON.parse(raw):null);}catch{return listCreations(null);}}
export function useCreations():Creation[]{
 const [list,setList]=useState<Creation[]>(()=>listCreations(null));
 useEffect(()=>{const sync=()=>setList(readCreations());sync();
  const evs=['storage','beastbox:spark-selected','beastbox:session-changed','beastbox:beast-name','focus'];evs.forEach(e=>window.addEventListener(e,sync));
  return()=>{evs.forEach(e=>window.removeEventListener(e,sync));};},[]);
 return list;}
