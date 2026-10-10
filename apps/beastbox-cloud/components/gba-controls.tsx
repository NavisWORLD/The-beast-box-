'use client';
import {useEffect, useRef} from 'react';
import {GBA_KEYS, pressCartridge} from '../lib/companion/go-hud.mjs';
import css from './gba-controls.module.css';

/** Both the web field and the persistent native shell use this input contract. */
export function controllerInput(button:string,down:boolean,source:'legacy'|'pointer'|'keyboard'|'gamepad'|'agent'='legacy') {
 if(!Object.prototype.hasOwnProperty.call(GBA_KEYS,button))return false;
 pressCartridge(button,down,window);
 window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down,source}}));
 return true;
}

export default function GbaControls({enabled=true,onMenu,shoulders=false}:{enabled?:boolean;onMenu?:()=>void;shoulders?:boolean}) {
 const held=useRef(new Map<string,{button:string;release:()=>void}>());
 useEffect(()=>{
  const release=()=>{for(const item of [...held.current.values()])item.release();};
  const hidden=()=>{if(document.hidden)release();};
  for(const event of ['blur','orientationchange','beastbox:gba-release'])window.addEventListener(event,release);
  document.addEventListener('fullscreenchange',release);document.addEventListener('visibilitychange',hidden);
  return()=>{release();for(const event of ['blur','orientationchange','beastbox:gba-release'])window.removeEventListener(event,release);document.removeEventListener('fullscreenchange',release);document.removeEventListener('visibilitychange',hidden);};
 },[]);
 useEffect(()=>{if(!enabled)for(const item of [...held.current.values()])item.release();},[enabled]);
 function hold(button:string,event:React.PointerEvent<HTMLButtonElement>) {
  if(!enabled)return;event.preventDefault();
  const target=event.currentTarget,id=event.pointerId,key=button+':'+id;
  if(held.current.has(key))return;
  controllerInput(button,true,'pointer');
  try{target.setPointerCapture(id);}catch{/* Android/WebView fallback uses matching window releases. */}
  let released=false;
  const release=(raw?:Event)=>{
   const pointer=raw as PointerEvent|undefined;
   if(pointer&&Number.isFinite(pointer.pointerId)&&pointer.pointerId!==id)return;
   if(released)return;released=true;held.current.delete(key);
   if(![...held.current.values()].some(item=>item.button===button))controllerInput(button,false,'pointer');
   target.removeEventListener('pointerup',release);target.removeEventListener('pointercancel',release);target.removeEventListener('lostpointercapture',release);target.removeEventListener('pointermove',move);
   window.removeEventListener('pointerup',release,true);window.removeEventListener('pointercancel',release,true);
   try{if(target.hasPointerCapture(id))target.releasePointerCapture(id);}catch{/* already canceled */}
  };
  const move=(raw:PointerEvent)=>{
   if(raw.pointerId!==id)return;
   const box=target.getBoundingClientRect();
   if(raw.clientX<box.left||raw.clientX>box.right||raw.clientY<box.top||raw.clientY>box.bottom)release(raw);
  };
  held.current.set(key,{button,release});
  target.addEventListener('pointerup',release);target.addEventListener('pointercancel',release);target.addEventListener('lostpointercapture',release);target.addEventListener('pointermove',move);
  window.addEventListener('pointerup',release,true);window.addEventListener('pointercancel',release,true);
 }
 function key(button:string,event:React.KeyboardEvent<HTMLButtonElement>,down:boolean) {
  if(event.key!==' '&&event.key!=='Enter')return;
  event.preventDefault();if(event.repeat)return;controllerInput(button,down,'keyboard');
 }
 const button=(name:keyof typeof GBA_KEYS,label:string,className?:string)=><button type="button" disabled={!enabled} className={className} aria-label={GBA_KEYS[name].label} onPointerDown={event=>hold(name,event)} onKeyDown={event=>key(name,event,true)} onKeyUp={event=>key(name,event,false)} onBlur={()=>controllerInput(name,false,'keyboard')}>{label}</button>;
 return <div className={css.handheld} data-handheld-controls="game-boy" aria-label="Lost COSMOS controls">
  {shoulders?<div className={css.shoulders}>{button('l','L')}<span>BEAST BOY · LOST COSMOS</span>{button('r','R')}</div>:null}
  <div className={css.face}>
   <div className={css.pad} aria-label="D-pad">{button('up','▲',css.up)}{button('left','◀',css.left)}<i aria-hidden="true"/>{button('right','▶',css.right)}{button('down','▼',css.down)}</div>
   <div className={css.actions}>{button('b','B',css.b)}{button('a','A',css.a)}</div>
  </div>
  <div className={css.systemKeys}>{button('select','SELECT')}{button('start','START')}{onMenu?<button type="button" aria-label="Main menu" onClick={onMenu}>☰ MENU</button>:null}</div>
 </div>;
}
