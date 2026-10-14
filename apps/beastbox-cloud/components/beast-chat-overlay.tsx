'use client';
import {useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {usePathname} from 'next/navigation';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import BeastTalkPanel,{type TalkState} from './beast-talk-panel';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
import {chatViewport} from '../lib/companion/chat-viewport.mjs';
import type {GameChatBridge} from './beast-chat-types';
import styles from './beast-chat-overlay.module.css';
import PixelBeast from './pixel-beast';
import ZerefFigure from './zeref-figure';
import {useUniverseMotion} from './use-universe-motion';

/** One mounted conversation. Visibility never recreates the request, ROM or creature. */
export default function BeastChatOverlay(){
 const {session}=useBeastSession(),{profile}=useCompanion(),path=usePathname();
 const {reduced}=useUniverseMotion();
 const persona=useMemo(()=>talkPersona({beast:session?.beast,cage:profile}),[session?.beast,profile]);
 const [open,setOpen]=useState(false),[expanded,setExpanded]=useState(false),[mobile,setMobile]=useState(false),[focusReturn,setFocusReturn]=useState(0);
 const [geometry,setGeometry]=useState({height:720,bottom:0}),[game,setGame]=useState<GameChatBridge|null>(null);
 const [host,setHost]=useState<HTMLDivElement|null>(null),[modalRoot,setModalRoot]=useState<Element|null>(null);
 const panel=useRef<HTMLElement|null>(null),restore=useRef<HTMLElement|null>(null),marker=useRef('');
 const historyLeaving=useRef(false),reopenQueued=useRef(false);
 useEffect(()=>{
  marker.current=crypto.randomUUID();const target=document.createElement('div');target.dataset.companionChatHost='true';
  const relocate=()=>{const container=document.fullscreenElement||document.body;container.append(target);setModalRoot(container);};relocate();setHost(target);
  document.addEventListener('fullscreenchange',relocate);
  return()=>{document.removeEventListener('fullscreenchange',relocate);target.remove();};
 },[]);
 useEffect(()=>{
  const show=(event:Event)=>{const opener=(event as CustomEvent).detail?.opener,focused=opener instanceof HTMLElement?opener:document.activeElement;if(focused instanceof HTMLElement&&!panel.current?.contains(focused))restore.current=focused;const container=document.fullscreenElement||document.body;if(panel.current?.parentElement)container.append(panel.current.parentElement);setModalRoot(container);if(historyLeaving.current){reopenQueued.current=true;return;}setOpen(true);};
  const back=()=>{if(historyLeaving.current){historyLeaving.current=false;if(reopenQueued.current){reopenQueued.current=false;setOpen(true);}else setFocusReturn(n=>n+1);return;}if(history.state?.beastboxChat!==marker.current)setOpen(false);};
  const bridge=(e:Event)=>{const value=(e as CustomEvent).detail;if(value&&typeof value.token==='string'&&typeof value.key==='string')setGame(value);};
  const release=(e:Event)=>setGame(old=>old?.token===(e as CustomEvent).detail?null:old);
  window.addEventListener('beastbox:open-chat',show);window.addEventListener('beastbox:game-chat-bridge',bridge);window.addEventListener('beastbox:game-chat-release',release);
  window.addEventListener('popstate',back);
  // Recover registration even when the player mounted before this listener.
  window.dispatchEvent(new Event('beastbox:request-game-chat-bridge'));
  return()=>{window.removeEventListener('beastbox:open-chat',show);window.removeEventListener('beastbox:game-chat-bridge',bridge);window.removeEventListener('beastbox:game-chat-release',release);window.removeEventListener('popstate',back);};
 },[]);
 useEffect(()=>{
  const media=window.matchMedia('(max-width:700px)');const resize=()=>{setMobile(media.matches);setGeometry(chatViewport(window.innerHeight,window.visualViewport));};resize();
  media.addEventListener('change',resize);window.addEventListener('resize',resize);window.visualViewport?.addEventListener('resize',resize);window.visualViewport?.addEventListener('scroll',resize);
  return()=>{media.removeEventListener('change',resize);window.removeEventListener('resize',resize);window.visualViewport?.removeEventListener('resize',resize);window.visualViewport?.removeEventListener('scroll',resize);};
 },[]);
 const close=useCallback(()=>{reopenQueued.current=false;setOpen(false);if(panel.current?.contains(document.activeElement)&&(document.activeElement instanceof HTMLElement))document.activeElement.blur();if(history.state?.beastboxChat===marker.current){historyLeaving.current=true;history.back();}},[]);
 useLayoutEffect(()=>{if(open)panel.current?.querySelector<HTMLElement>('button')?.focus({preventScroll:true});},[open]);
 // Inert the background before paint, so the modal never exposes page navigation to assistive technology.
 useLayoutEffect(()=>{
  if(!open||!mobile)return;
  if(history.state?.beastboxChat!==marker.current)history.pushState({...history.state,beastboxChat:marker.current},'');
  const body=document.body,html=document.documentElement,x=window.scrollX,y=window.scrollY,previous={body:body.getAttribute('style'),html:html.style.overflow,behavior:html.style.scrollBehavior};
  // Focus the dialog before hiding siblings, preventing focus inside an aria-hidden ancestor.
  if(!panel.current?.contains(document.activeElement))panel.current?.querySelector<HTMLElement>('button')?.focus({preventScroll:true});
  const container=modalRoot||document.fullscreenElement||body,inert=Array.from(container.children).filter(node=>node!==host&&node instanceof HTMLElement).map(node=>({node:node as HTMLElement,value:(node as HTMLElement).inert,ariaHidden:(node as HTMLElement).getAttribute('aria-hidden')}));
  for(const item of inert){item.node.inert=true;item.node.setAttribute('aria-hidden','true');}
  Object.assign(body.style,{position:'fixed',top:-y+'px',left:-x+'px',width:'100%',overflow:'hidden'});html.style.overflow='hidden';
  return()=>{for(const item of inert){item.node.inert=item.value;if(item.ariaHidden===null)item.node.removeAttribute('aria-hidden');else item.node.setAttribute('aria-hidden',item.ariaHidden);}if(previous.body===null)body.removeAttribute('style');else body.setAttribute('style',previous.body);html.style.overflow=previous.html;html.style.scrollBehavior='auto';window.scrollTo(x,y);html.style.scrollBehavior=previous.behavior;};
 },[open,mobile,host,modalRoot]);
 useLayoutEffect(()=>{if(open||historyLeaving.current||!restore.current)return;const target=restore.current;restore.current=null;if(target.isConnected)target.focus({preventScroll:true});},[open,focusReturn]);
 useEffect(()=>{
  if(!open)return;
  const keyboard=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();close();return;}if(!mobile||event.key!=='Tab')return;
   const nodes=Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),textarea:not(:disabled),input:not(:disabled),a[href],select')||[]).filter(x=>x.getClientRects().length);
   const first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  };window.addEventListener('keydown',keyboard);return()=>window.removeEventListener('keydown',keyboard);
 },[open,mobile,close]);
 const changed=useCallback((state:TalkState)=>window.dispatchEvent(new CustomEvent('beastbox:talk-state',{detail:{state}})),[]);
 return <>
  {path!=='/sol-game'||!game?<button className={styles.launcher} type="button" data-critical-control aria-controls="beast-chat-overlay" aria-expanded={open} disabled={!host} onClick={event=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:event.currentTarget}}))}>TALK TO {persona.name}</button>:null}
  {host?createPortal(<>
   {open&&mobile?<button type="button" className={styles.scrim} aria-label="Dismiss creature chat" onClick={close}/>:null}
   <section ref={panel} id="beast-chat-overlay" role="dialog" aria-modal={mobile||undefined} aria-label={`Talk to ${persona.name}`} data-companion-chat-overlay data-expanded={expanded||undefined} className={styles.panel} hidden={!open} style={{'--chat-vh':geometry.height+'px','--chat-bottom':geometry.bottom+'px'} as React.CSSProperties}>
    <header className={styles.header}>
     <div className={styles.portrait}>{session?.beast?.genome?<PixelBeast genome={session.beast.genome} stage={session.beast.stage} publicSpark label={`${persona.name} sprite`} reduced={reduced}/>:persona.source==='zeref'||profile?.id==='bb-7f9c2a03'?<svg viewBox="0 0 400 400" role="img" aria-label="Moonwraith display persona"><ZerefFigure id="beast-chat-moonwraith"/></svg>:<span aria-label="Select a saved Beast to show its sprite">✦</span>}</div>
     <div className={styles.name}><h2>Talk to {persona.name}</h2><small>{session?.beast?.qbeast?.profile.id||profile?.id||'Moonwraith display persona · choose a saved beast to connect'}</small></div>
     <button type="button" onClick={()=>setExpanded(x=>!x)} aria-label={expanded?'Compact chat':'Expand chat'}>{expanded?'↙':'↗'}</button>
     <button type="button" onClick={close} aria-label="Minimize chat">−</button><button type="button" onClick={close} aria-label="Close chat">×</button>
    </header>
    <BeastTalkPanel surface="panel" compact onState={changed} gameBridge={game}/>
   </section>
  </>,host):null}
 </>;
}
