'use client';
import {useEffect,useRef} from 'react';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import type {GameChatBridge} from './beast-chat-types';
export default function SolGameTalk({active=true,observeGame,applyGameAction,canGuide=false,gameKey=''}:{active?:boolean;observeGame?:()=>Promise<any|null>;applyGameAction?:(button:string,expectedKey:string)=>Promise<boolean>;canGuide?:boolean;gameKey?:string}){
 const {session}=useBeastSession(),token=useRef('');
 useEffect(()=>{
  if(!token.current)token.current=crypto.randomUUID();
  const register=()=>{const detail:GameChatBridge={token:token.current,key:gameKey,canGuide:active&&canGuide,observeGame:active?observeGame:undefined,applyGameAction:active?applyGameAction:undefined};window.dispatchEvent(new CustomEvent('beastbox:game-chat-bridge',{detail}));};
  register();window.addEventListener('beastbox:request-game-chat-bridge',register);
  return()=>{window.removeEventListener('beastbox:request-game-chat-bridge',register);window.dispatchEvent(new CustomEvent('beastbox:game-chat-release',{detail:token.current}));};
 },[active,observeGame,applyGameAction,canGuide,gameKey]);
 return <div data-spark-game-talk><button type="button" onClick={()=>window.dispatchEvent(new Event('beastbox:open-chat'))}>TALK TO {shownName(session?.beast)||'Zeref'}</button></div>;
}
