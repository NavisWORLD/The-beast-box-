'use client';
import {useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import {activeBeastName as activeBeastNameFromStore} from '@/lib/companion/beast-name.mjs';
import {SITE_NAV,activeBeastName,navLabel} from '@/lib/site-nav';
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
 return <>
  <div className={s.bar} data-site-nav-bar><a href="/" className={s.brand}>✦ BEAST BOX</a><button type="button" className={s.barBtn} data-site-nav-toggle aria-expanded={open} aria-controls="site-nav-sheet" onClick={toggle}><span aria-hidden>☰</span> Menu</button></div>
  {float&&!open?<button type="button" className={s.pill} data-site-nav-float aria-label="Open site menu" onClick={toggle}><span aria-hidden>☰</span></button>:null}
  {open?<><button type="button" className={s.scrim} aria-label="Close menu" onClick={()=>setOpen(false)}/>
  <nav id="site-nav-sheet" className={s.sheet} aria-label="Site menu" data-site-nav>
   <div className={s.head}><strong>BEAST BOX</strong><button type="button" onClick={()=>setOpen(false)} aria-label="Close menu" className={s.x}>✕</button></div>
   {SITE_NAV.map(g=><section key={g.key} className={s.group} data-nav-group={g.key}><h2>{g.label}</h2><ul>{g.items.map(i=><li key={i.href}><a href={i.href} aria-current={cur(i.href)?'page':undefined} onClick={()=>setOpen(false)}><span aria-hidden>{i.icon}</span>{navLabel(i,beastName)}{i.note?<small>{i.note}</small>:null}</a></li>)}</ul></section>)}
  </nav></>:null}
 </>;
}
