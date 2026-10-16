'use client';
import { useEffect, useState } from 'react';

/** One small corner launcher that tucks the secondary floating widgets
 * (voice dock, TALK pill, companion mini-widget, floating toolbars) on phones.
 * Sound + support stay as compact chips; everything else opens on demand. */
export default function CornerLauncher(){
 const [open,setOpen]=useState(false);
 useEffect(()=>{
  const html=document.documentElement;
  if(open)html.setAttribute('data-docks-open','');else html.removeAttribute('data-docks-open');
  const close=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false);};
  window.addEventListener('keydown',close);
  const chat=()=>setOpen(false);window.addEventListener('beastbox:open-chat',chat);
  return()=>{window.removeEventListener('keydown',close);window.removeEventListener('beastbox:open-chat',chat);};
 },[open]);
 return <button type="button" className="corner-launcher" data-corner-launcher aria-expanded={open}
  aria-label={open?'Hide Beast widgets':'Show Beast widgets'} onClick={()=>setOpen(v=>!v)}>
  <span aria-hidden="true">{open?'×':'✦'}</span></button>;
}
