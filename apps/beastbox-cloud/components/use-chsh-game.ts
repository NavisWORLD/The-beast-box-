'use client';
import {useEffect,useState} from 'react';
import {CHSH_GAME_SRC,chshGameWorld} from '../lib/companion/chsh-game-world.mjs';
export function useChshGame(){const [g,setG]=useState<any>(null);
 useEffect(()=>{let live=true;fetch(CHSH_GAME_SRC).then(r=>r.ok?r.json():null).then(d=>{if(live)setG(chshGameWorld(d));}).catch(()=>{});return()=>{live=false;};},[]);return g;}
