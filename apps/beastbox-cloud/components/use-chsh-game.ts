'use client';
import {useEffect,useState} from 'react';
import {CHSH_GAME_SRC,CHSH_GAME_DATA,chshGameWorld,historyRows} from '../lib/companion/chsh-game-world.mjs';
const get=(u:string)=>fetch(u,{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null);
/** Latest verified daily result from the data-only branch, falling back to the bundled first batch. */
export function useChshGame(){const [g,setG]=useState<any>(null);
 useEffect(()=>{let live=true;(async()=>{const d=(await get(CHSH_GAME_DATA+'latest.json'))||(await get(CHSH_GAME_SRC));if(live)setG(chshGameWorld(d));})();return()=>{live=false;};},[]);return g;}
export function useChshHistory(){const [h,setH]=useState<any[]|null>(null);
 useEffect(()=>{let live=true;(async()=>{const d=await get(CHSH_GAME_DATA+'history.json');const fb=d?null:await get(CHSH_GAME_SRC);if(live)setH(historyRows(d,fb));})();return()=>{live=false;};},[]);return h;}
