'use client';
import {useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import {activeBeastName as activeBeastNameFromStore} from '@/lib/companion/beast-name.mjs';
import {SITE_NAV,activeBeastName,navLabel} from '@/lib/site-nav';
import {ONE_CAGE} from '@/lib/universe/growth-copy.mjs';
import {PIECES,worldHere,WORLD_LABELS} from '@/lib/world/world-map.mjs';
import s from './site-nav.module.css';
/** The one site menu: a slim top bar (+ a floating ☰ once scrolled) opening a grouped bottom sheet (phone) / side panel (desktop). */
export default function SiteNav(){
 const path=usePathname()||'/';const [open,setOpen]=useState(false),[float,setFloat]=useState(false);
 useEffect(()=>{const f=()=>setFloat(window.scrollY>140);f();window.addEventListener('scroll',f,{passive:true});return()=>window.removeEventListener('scroll',f);},[]);
 useEffect(()=>{setOpen(false);},[path]);
 useEffect(()=>{const o=()=>setOpen(true);window.addEventListener('beastbox:open-site-nav',o);return()=>window.removeEventListener('beastbox:open-site-nav',o);},[]);
 useEffect(()=>{if(!open)return;const k=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false);};window.addEventListener('keydown',k);return()=>window.removeEventListener('keydown',k);},[open]);
 const cur=(h:string)=>h===path;
 const [beastName,setBeastName]=useState<string|null>(null);
 useEffect(()=>{if(open){try{setBeastName(activeBeastNameFromStore(localStorage).name);}catch{}}},[open]);
 const toggle=()=>setOpen(o=>!o);
 const here=worldHere(path);
 // the world map opens from any piece chip (and from the pocket menu's 'where am I' row)
 return <>
  <div className={s.bar} data-site-nav-bar><a href="/" className={s.brand}>✦ BEAST BOX</a>{here?<div className={s.piece} data-world-piece={here.piece.key} role="group" aria-label={'You are in the '+here.piece.name+' piece of the one world'}><a href={here.prev!.href} className={s.pieceArrow} data-world-prev aria-label={'Previous piece: '+here.prev!.name}>‹</a><button type="button" className={s.pieceBtn} data-world-piece-button aria-label={'World map. You are in '+here.piece.name+(here.sub?' · '+here.sub:'')+', piece '+here.index+' of '+here.total} onClick={()=>setOpen(true)}><span aria-hidden>{here.piece.icon}</span><span className={s.pieceName}>{here.piece.short}</span><span className={s.pieceNum} aria-hidden>{here.index}/{here.total}</span></button><a href={here.next!.href} className={s.pieceArrow} data-world-next aria-label={'Next piece: '+here.next!.name}>›</a></div>:null}<button type="button" className={s.barBtn} data-site-nav-toggle aria-expanded={open} aria-controls="site-nav-sheet" onClick={toggle}><span aria-hidden>☰</span> Menu</button></div>
  {float&&!open?<button type="button" className={s.pill} data-site-nav-float aria-label="Open site menu" onClick={toggle}><span aria-hidden>☰</span></button>:null}
  {open?<><button type="button" className={s.scrim} aria-label="Close menu" onClick={()=>setOpen(false)}/>
  <nav id="site-nav-sheet" className={s.sheet} aria-label="Site menu" data-site-nav>
   <div className={s.head}><strong>BEAST BOX</strong><button type="button" onClick={()=>setOpen(false)} aria-label="Close menu" className={s.x}>✕</button></div>
   {here?<section className={s.map} data-world-map aria-label="World map"><h2>{WORLD_LABELS.title} · you are here</h2>
    <p className={s.mapLine}><strong>{here.piece.icon} {here.piece.name}{here.sub?' · '+here.sub:''}</strong> · piece {here.index} of {here.total}. {here.piece.role}</p>
    <ul className={s.pieces}>{PIECES.map(p=><li key={p.key}><a href={p.href} data-world-piece-link={p.key} aria-current={p.key===here.piece.key?'page':undefined} data-neighbor={here.piece.neighbors.includes(p.key)?'':undefined} onClick={()=>setOpen(false)}><span aria-hidden>{p.icon}</span><span>{p.name}<small>{p.key===here.piece.key?'You are here':here.piece.neighbors.includes(p.key)?'Next door':p.short}</small></span></a></li>)}</ul>
    <p className={s.mapNote}>{WORLD_LABELS.line} {WORLD_LABELS.honesty}</p></section>:null}
   <p className={s.hint} data-one-cage-hint>{ONE_CAGE.menu_hint}</p>
   {SITE_NAV.map(g=><section key={g.key} className={s.group} data-nav-group={g.key}><h2>{g.label}</h2><ul>{g.items.map(i=><li key={i.href}><a href={i.href} aria-current={cur(i.href)?'page':undefined} onClick={()=>setOpen(false)}><span aria-hidden>{i.icon}</span>{navLabel(i,beastName)}{i.note?<small>{i.note}</small>:null}</a></li>)}</ul></section>)}
   <footer className={s.foot} data-one-cage-footer><strong>{ONE_CAGE.footer}</strong><small>{ONE_CAGE.honesty}</small></footer>
  </nav></>:null}
 </>;
}
