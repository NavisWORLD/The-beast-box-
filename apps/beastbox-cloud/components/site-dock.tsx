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
 // One floating control: the dock also opens the site menu, so the separate Menu tab / ☰ pill step aside (not under automation).
 useEffect(()=>{if(auto)return;document.body.dataset.oneDock='1';return()=>{delete document.body.dataset.oneDock;};},[auto]);
 // On phones the dock tucks away while the page is scrolling (so it never sits over the buttons you are trying to read or tap) and slides back when scrolling stops.
 useEffect(()=>{if(auto)return;let last=window.scrollY,tm:any=0;const nav=()=>document.querySelector<HTMLElement>('[data-site-dock]');const on=()=>{const y=window.scrollY,d=y-last;last=y;const el=nav();if(!el||window.innerWidth>560)return;if(d>4&&y>160)el.dataset.away='1';clearTimeout(tm);tm=setTimeout(()=>{const e=nav();if(e)delete e.dataset.away;},650);};window.addEventListener('scroll',on,{passive:true});return()=>{window.removeEventListener('scroll',on);clearTimeout(tm);};},[auto]);
 // Phones: after ~3 s without a touch or scroll the dock shrinks to a small round handle (it never sits over content); the first tap on it only expands it.
 const [compact,setCompact]=useState(false);
 useEffect(()=>{if(auto)return;let tm:any=0;const arm=()=>{setCompact(false);clearTimeout(tm);tm=setTimeout(()=>{if(window.innerWidth<=560)setCompact(true);},3200);};arm();const evs=['touchstart','scroll','keydown'];evs.forEach(e=>window.addEventListener(e,arm,{passive:true}));return()=>{evs.forEach(e=>window.removeEventListener(e,arm));clearTimeout(tm);};},[auto,open]);
 const expandFirst=(e:React.MouseEvent)=>{if(compact){e.preventDefault();e.stopPropagation();setCompact(false);}};
 if(auto)return null;
 return <nav className="site-dock" aria-label="Quick dock" data-site-dock={open?'open':'closed'} data-compact={compact?'':undefined} onClickCapture={expandFirst}>
  <button type="button" onClick={e=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:e.currentTarget}}))} aria-label={`Talk to ${name||'your beast'}`}>💬<span>{name&&name!=='your beast'?`Talk to ${name}`:'Talk'}</span></button>
  <button type="button" data-dock-menu aria-controls="site-nav-sheet" onClick={()=>window.dispatchEvent(new Event('beastbox:open-site-nav'))} aria-label="Open site menu">☰<span>Menu</span></button>
  <Link prefetch={false} href="/sol-game" aria-label="Lost COSMOS game">🎮<span>Lost COSMOS</span></Link>
  <button type="button" aria-pressed={open} onClick={toggle} aria-label={open?'Tuck the extra controls away':'Show sound, Zeref and the game card'}>{open?'✕':'⋯'}<span>{open?'Less':'More'}</span></button>
 </nav>;
}
