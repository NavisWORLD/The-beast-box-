'use client';
// Brain / Workbench chat on phones (Cory's iPhone shot, Nov 7 2026): while the Brain chat is on screen the body carries
// data-brain-chat so the global overlays (share card, quick buttons, bottom bar, floating docks) step aside, and --vvh tracks
// the visual viewport so the pinned composer rides above the on-screen keyboard. Layout only: no chat behaviour changes.
import {useEffect} from 'react';
export default function BrainChatMode(){
 useEffect(()=>{
  const b=document.body;b.dataset.brainChat='1';
  const vv=window.visualViewport;
  const set=()=>{const h=vv?vv.height:window.innerHeight;b.style.setProperty('--vvh',Math.round(h)+'px');b.style.setProperty('--vvtop',Math.round(vv?vv.offsetTop:0)+'px');};
  set();vv?.addEventListener('resize',set);vv?.addEventListener('scroll',set);window.addEventListener('resize',set);
  return()=>{delete b.dataset.brainChat;b.style.removeProperty('--vvh');b.style.removeProperty('--vvtop');vv?.removeEventListener('resize',set);vv?.removeEventListener('scroll',set);window.removeEventListener('resize',set);};
 },[]);
 return null;
}
