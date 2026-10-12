'use client';
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {usePathname} from 'next/navigation';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import BeastTalkPanel,{type TalkState} from './beast-talk-panel';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
import {chatViewport} from '../lib/companion/chat-viewport.mjs';
import type {GameChatBridge} from './beast-chat-types';
import styles from './beast-chat-overlay.module.css';

/** One mounted conversation. Visibility never recreates the request, ROM or creature. */
export default function BeastChatOverlay(){
 const {session}=useBeastSession(),{profile}=useCompanion(),path=usePathname();
 const persona=useMemo(()=>talkPersona({beast:session?.beast,cage:profile}),[session?.beast,profile]);
 const [open,setOpen]=useState(false),[expanded,setExpanded]=useState(false),[mobile,setMobile]=useState(false);
 const [geometry,setGeometry]=useState({height:720,bottom:0}),[game,setGame]=useState<GameChatBridge|null>(null);
 const [host,setHost]=useState<HTMLDivElement|null>(null);
 const panel=useRef<HTMLElement|null>(null),restore=useRef<HTMLElement|null>(null),marker=useRef('');
 useEffect(()=>{
  marker.current=crypto.randomUUID();const target=document.createElement('div');target.dataset.companionChatHost='true';document.body.append(target);setHost(target);
  const relocate=()=>{(document.fullscreenElement||document.body).append(target);};
  document.addEventListener('fullscreenchange',relocate);
  return()=>{document.removeEventListener('fullscreenchange',relocate);target.remove();};
 },[]);
 useEffect(()=>{
  const show=()=>{if(document.activeElement instanceof HTMLElement&&!panel.current?.contains(document.activeElement))restore.current=document.activeElement;setOpen(true);};
  const bridge=(e:Event)=>{const value=(e as CustomEvent).detail;if(value&&typeof value.token==='string'&&typeof value.key==='string')setGame(value);};
  const release=(e:Event)=>setGame(old=>old?.token===(e as CustomEvent).detail?null:old);
  window.addEventListener('beastbox:open-chat',show);window.addEventListener('beastbox:game-chat-bridge',bridge);window.addEventListener('beastbox:game-chat-release',release);
  // Recover registration even when the player mounted before this listener.
  window.dispatchEvent(new Event('beastbox:request-game-chat-bridge'));
  return()=>{window.removeEventListener('beastbox:open-chat',show);window.removeEventListener('beastbox:game-chat-bridge',bridge);window.removeEventListener('beastbox:game-chat-release',release);};
 },[]);
 useEffect(()=>{
  const media=window.matchMedia('(max-width:700px)');const resize=()=>{setMobile(media.matches);setGeometry(chatViewport(window.innerHeight,window.visualViewport));};resize();
  media.addEventListener('change',resize);window.addEventListener('resize',resize);window.visualViewport?.addEventListener('resize',resize);window.visualViewport?.addEventListener('scroll',resize);
  return()=>{media.removeEventListener('change',resize);window.removeEventListener('resize',resize);window.visualViewport?.removeEventListener('resize',resize);window.visualViewport?.removeEventListener('scroll',resize);};
 },[]);
 const close=useCallback(()=>{setOpen(false);if(panel.current?.contains(document.activeElement)&&(document.activeElement instanceof HTMLElement))document.activeElement.blur();if(history.state?.beastboxChat===marker.current)history.back();restore.current?.focus({preventScroll:true});},[]);
 useEffect(()=>{
  if(!open||!mobile)return;
  if(history.state?.beastboxChat!==marker.current)history.pushState({...history.state,beastboxChat:marker.current},'');
  const back=()=>{if(history.state?.beastboxChat!==marker.current)setOpen(false);};window.addEventListener('popstate',back);
  const body=document.body,html=document.documentElement,previous={body:body.style.overflow,html:html.style.overflow};body.style.overflow='hidden';html.style.overflow='hidden';
  return()=>{window.removeEventListener('popstate',back);body.style.overflow=previous.body;html.style.overflow=previous.html;};
 },[open,mobile]);
 useEffect(()=>{
  if(!open)return;panel.current?.querySelector<HTMLElement>('button')?.focus({preventScroll:true});
  const keyboard=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();close();return;}if(!mobile||event.key!=='Tab')return;
   const nodes=Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),textarea:not(:disabled),input:not(:disabled),a[href],select')||[]).filter(x=>x.getClientRects().length);
   const first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  };window.addEventListener('keydown',keyboard);return()=>window.removeEventListener('keydown',keyboard);
 },[open,mobile,close]);
 const changed=useCallback((state:TalkState)=>window.dispatchEvent(new CustomEvent('beastbox:talk-state',{detail:{state}})),[]);
 return <>
  {path!=='/sol-game'||!game?<button className={styles.launcher} type="button" data-critical-control aria-controls="beast-chat-overlay" aria-expanded={open} onClick={()=>window.dispatchEvent(new Event('beastbox:open-chat'))}>TALK TO {persona.name}</button>:null}
  {host?createPortal(<>
   {open&&mobile?<button type="button" className={styles.scrim} aria-label="Dismiss creature chat" onClick={close}/>:null}
   <section ref={panel} id="beast-chat-overlay" role="dialog" aria-modal={mobile||undefined} aria-label={`Talk to ${persona.name}`} data-companion-chat-overlay data-expanded={expanded||undefined} className={styles.panel} hidden={!open} style={{'--chat-vh':geometry.height+'px','--chat-bottom':geometry.bottom+'px'} as React.CSSProperties}>
    <header className={styles.header}>
     <div className={styles.name}><strong>{persona.name}</strong><small>{session?.beast?.qbeast?.profile.id||profile?.id||'Moonwraith display persona · choose a saved beast to connect'}</small></div>
     <button type="button" onClick={()=>setExpanded(x=>!x)} aria-label={expanded?'Compact chat':'Expand chat'}>{expanded?'↙':'↗'}</button>
     <button type="button" onClick={close} aria-label="Minimize chat">−</button><button type="button" onClick={close} aria-label="Close chat">×</button>
    </header>
    <BeastTalkPanel surface="panel" compact onState={changed} gameBridge={game}/>
   </section>
  </>,host):null}
 </>;
}
