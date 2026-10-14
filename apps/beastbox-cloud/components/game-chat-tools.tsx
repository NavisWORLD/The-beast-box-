'use client';
import {useEffect,useRef,useState} from 'react';
import {useBeastSession} from './beast-session';
import {care} from '../lib/companion/adventure.mjs';
import {gameBeastKey} from '../lib/companion/sol-game-talk.mjs';
import {gameObservationLine} from '../lib/companion/native-optics.mjs';
import {proposeGuidedGameAction,MAX_GUIDED_STEPS} from '../lib/companion/guided-game.mjs';
import type {GameChatBridge} from './beast-chat-types';
export default function GameChatTools({bridge,busy,route,optedIn}:{bridge:GameChatBridge;busy:boolean;route:string;optedIn:boolean}){
 const {session,change}=useBeastSession(),[status,setStatus]=useState(''),[guiding,setGuiding]=useState(false);
 const pending=useRef<AbortController|null>(null),current=useRef({key:gameBeastKey(session),bridge});current.current={key:gameBeastKey(session),bridge};
 useEffect(()=>()=>pending.current?.abort(),[]);useEffect(()=>{if(!bridge.canGuide)pending.current?.abort();},[bridge.canGuide]);
 async function inspect(){try{setStatus(gameObservationLine(await bridge.observeGame?.())||'No readable native frame. No screen description was invented.');}catch{setStatus('The game observation was unavailable.');}}
 async function guide(){if(guiding||busy||!bridge.canGuide||!optedIn||!bridge.observeGame||!bridge.applyGameAction)return;
  const key=bridge.key,controller=new AbortController();pending.current=controller;setGuiding(true);const timeout=setTimeout(()=>controller.abort(),90000),actual:string[]=[];
  try{for(let step=0;step<MAX_GUIDED_STEPS;step++){
   if(controller.signal.aborted||current.current.key!==key||!current.current.bridge.canGuide)break;
   const observation=await bridge.observeGame();const proposal=await proposeGuidedGameAction({session,observation,fetchImpl:fetch,signal:controller.signal,model:route==='connected-brain-bay'?'connected':'guest'});
   if(controller.signal.aborted||current.current.key!==key||!current.current.bridge.canGuide)break;
   if(!proposal.ok||!('command' in proposal)||typeof proposal.command!=='string'){setStatus('Guided trial stopped: '+(proposal.reason||'No valid model action.'));return;}
   if(proposal.button&&!await bridge.applyGameAction(proposal.button,key)){setStatus('Game or identity changed. No further key was injected.');return;}actual.push(proposal.command);
  }setStatus('Actual bounded decisions: '+(actual.join(' → ')||'none')+'. Objective progress is unverified.');}
  catch(error){setStatus('Guided trial stopped: '+(error instanceof Error?error.message:'Observation unavailable'));}finally{clearTimeout(timeout);pending.current=null;setGuiding(false);}
 }
 return <div><button type="button" disabled={busy||guiding||!bridge.observeGame} onClick={()=>void inspect()}>LOOK AT GAME</button><button type="button" disabled={busy||guiding||!bridge.canGuide||!optedIn||!['guest-rawrphos','connected-brain-bay'].includes(route)} onClick={()=>void guide()}>TRY 3 GUIDED STEPS · EXPERIMENTAL</button>{guiding?<button type="button" onClick={()=>pending.current?.abort()}>STOP & RELEASE</button>:null}<button type="button" onClick={()=>void change(draft=>{if(gameBeastKey(draft)===bridge.key)care(draft,'pet');})}>PET</button><button type="button" onClick={()=>void change(draft=>{if(gameBeastKey(draft)===bridge.key)care(draft,'rest');})}>REST</button><p role="status">{status}</p><p>Care XP {session?.beast?.xp||0} · Energy {session?.beast?.energy??100}. Native evolution is earned in the cartridge.</p></div>;
}
