'use client';
import {useEffect,useState} from 'react';
import {listCreations,type Creation} from '../lib/companion/creations.mjs';
import {SESSION_KEY} from '../lib/companion/beast-name.mjs';
import {applyPopulation,browserPopulationOn} from '../lib/cosmos/one-population.mjs';
type Listed=Creation&{source?:string|null;mood?:string|null;diaryTick?:number|null};
/** Every creation (active beast, saved beasts, artist residents) from the same saved session the rest of the site reads. Azure state.json rows join only when the population flag is on. */
export function readCreations():Listed[]{try{const raw=localStorage.getItem(SESSION_KEY);return listCreations(raw?JSON.parse(raw):null);}catch{return listCreations(null);}}
export function useCreations():Listed[]{
 const [list,setList]=useState<Listed[]>(()=>listCreations(null));
 useEffect(()=>{
  let live=true;let feed:Listed[]|null=null;let asked=false;
  const sync=()=>{
   const base=readCreations();const on=browserPopulationOn();
   setList(on&&feed?applyPopulation({on:true,creations:base,feed}):base);
   if(!on||asked)return;
   asked=true;
   fetch('/api/cosmos/population',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(body=>{
    if(!live)return;feed=Array.isArray(body?.creatures)?body.creatures:[];sync();
   }).catch(()=>{if(!live)return;feed=[];sync();});
  };
  sync();
  const evs=['storage','beastbox:spark-selected','beastbox:session-changed','beastbox:beast-name','focus'];evs.forEach(e=>window.addEventListener(e,sync));
  return()=>{live=false;evs.forEach(e=>window.removeEventListener(e,sync));};
 },[]);
 return list;}
