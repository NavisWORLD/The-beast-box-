'use client';
import {useEffect,useState} from 'react';
import {currentWorldClock,whenWorldClock,type WorldClock} from '@/lib/world/one-world-clock.mjs';
/** Subscribe to the one shared world. Returns null until the root provider has the genesis. */
export function useOneWorld(onTick?:(u:any,prev:any)=>void){
 const [u,setU]=useState<any>(()=>currentWorldClock()?.get()??null);const [clock,setClock]=useState<WorldClock|null>(()=>currentWorldClock());
 useEffect(()=>{let off=()=>{};let live=true;whenWorldClock().then(c=>{if(!live)return;setClock(c);setU(c.get());off=c.subscribe((n,p)=>{setU(n);onTick?.(n,p);});});return()=>{live=false;off();};},[]);// eslint-disable-line react-hooks/exhaustive-deps
 return {u,clock};
}
