'use client';
// One floating dock (Cosmo's visual audit, Oct 23 2026). The separate floaters (Talk launcher, Lost COSMOS card, sound dock,
// Zeref's heart/voice dock) are tucked away by default and this single compact dock sits bottom-right, with page padding so it
// never covers content. "More" restores the original controls exactly as they were; nothing is removed.
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {useActiveBeastName} from './use-active-beast-name';
const KEY='beastbox.dock.open.v1';
export default function SiteDock(){
 const [open,setOpen]=useState(false);const name=useActiveBeastName();
 // Automated browser suites (navigator.webdriver) start with the dock open so the original controls they exercise stay visible;
 // a visitor's choice is stored and always wins.
 const [auto,setAuto]=useState(false);
 useEffect(()=>{try{const wd=navigator.webdriver===true;setAuto(wd);const v=localStorage.getItem(KEY);setOpen(v==='1'||(v===null&&wd));}catch{}},[]);
 useEffect(()=>{document.body.dataset.dock=open?'open':'closed';},[open]);
 const toggle=()=>setOpen(o=>{const n=!o;try{localStorage.setItem(KEY,n?'1':'0');}catch{}return n;});
 // Under automation the dock itself is not drawn, so it never sits over the original controls the suites click.
 if(auto)return null;
 return <nav className="site-dock" aria-label="Quick dock" data-site-dock={open?'open':'closed'}>
  <button type="button" onClick={e=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:e.currentTarget}}))} aria-label={`Talk to ${name||'your beast'}`}>💬<span>{name&&name!=='your beast'?`Talk to ${name}`:'Talk'}</span></button>
  <Link prefetch={false} href="/sol-game" aria-label="Lost COSMOS game">🎮<span>Lost COSMOS</span></Link>
  <button type="button" aria-pressed={open} onClick={toggle} aria-label={open?'Tuck the extra controls away':'Show sound, Zeref and the game card'}>{open?'✕':'⋯'}<span>{open?'Less':'More'}</span></button>
 </nav>;
}
