'use client';
import {useEffect,useRef} from 'react';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
import type {GameChatBridge} from './beast-chat-types';
export default function SolGameTalk({active=true,observeGame,applyGameAction,canGuide=false,gameKey=''}:{active?:boolean;observeGame?:()=>Promise<any|null>;applyGameAction?:(button:string,expectedKey:string)=>Promise<boolean>;canGuide?:boolean;gameKey?:string}){
 const {session}=useBeastSession(),{profile}=useCompanion(),token=useRef('');
 const talkName=talkPersona({beast:session?.beast||null,cage:profile}).name;
 useEffect(()=>{
  if(!token.current)token.current=crypto.randomUUID();
  const register=()=>{const detail:GameChatBridge={token:token.current,key:gameKey,canGuide:active&&canGuide,observeGame:active?observeGame:undefined,applyGameAction:active?applyGameAction:undefined};window.dispatchEvent(new CustomEvent('beastbox:game-chat-bridge',{detail}));};
  register();window.addEventListener('beastbox:request-game-chat-bridge',register);
  return()=>{window.removeEventListener('beastbox:request-game-chat-bridge',register);window.dispatchEvent(new CustomEvent('beastbox:game-chat-release',{detail:token.current}));};
 },[active,observeGame,applyGameAction,canGuide,gameKey]);
 return <div data-spark-game-talk><button type="button" aria-controls="beast-chat-overlay" onClick={event=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:event.currentTarget}}))}>TALK TO {talkName}</button></div>;
}
