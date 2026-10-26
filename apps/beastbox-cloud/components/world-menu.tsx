'use client';
// ONE clean menu for the pocket dimensional world (Cory, Oct 25 2026). A single corner button opens a sheet that holds every option
// that used to sit on top of the scene: the view switch, camera/place actions, pocket tools, reset camera, diary, senses pointer and the
// honesty info. Nothing floats over the creatures. The scene components portal their own controls into the hosts below, so every
// option keeps its real state and handler. Home and Cage use the same component with their own context (framing) and share view state.
import {useCallback,useEffect,useId,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {POCKET_3D_CAMERA_RESET} from '../lib/companion/pocket-3d-settings.mjs';
import {menuModel,type ViewId} from '../lib/world/world-options.mjs';
import css from './world-menu.module.css';
export type MenuHosts={place:HTMLElement|null;tools:HTMLElement|null;about:HTMLElement|null};
export default function WorldMenu({context,view,onView,hasBeast,beastName,onHosts,extra,hideViews=[]}:{hideViews?:ViewId[];
 context:'cage'|'home';view:ViewId;onView:(v:ViewId)=>void;hasBeast:boolean;beastName?:string|null;onHosts:(h:MenuHosts)=>void;
 /** page-specific extra rows (e.g. Home's "Enter the tiny world") rendered in the place section */
 extra?:{label:string;href?:string;onClick?:()=>void;icon?:string;attr?:string}[]}){
 const model=menuModel(context,{hasBeast,beastName});
 const [open,setOpen]=useState(false);const [mounted,setMounted]=useState(false);
 const [place,setPlace]=useState<HTMLElement|null>(null),[tools,setTools]=useState<HTMLElement|null>(null),[about,setAbout]=useState<HTMLElement|null>(null);
 const fab=useRef<HTMLButtonElement>(null);const id=useId();
 useEffect(()=>{setMounted(true);},[]);
 useEffect(()=>{onHosts({place,tools,about});},[place,tools,about,onHosts]);
 const close=useCallback((refocus=true)=>{setOpen(false);if(refocus)fab.current?.focus();},[]);
 useEffect(()=>{if(!open)return;const k=(e:KeyboardEvent)=>{if(e.key==='Escape')close();};window.addEventListener('keydown',k);return()=>window.removeEventListener('keydown',k);},[open,close]);
 const sheetId='world-menu-'+id.replace(/:/g,'');
 const sheet=<>
  <button type="button" className={css.scrim} data-world-menu-scrim hidden={!open} aria-label="Close menu" tabIndex={open?0:-1} onClick={()=>close()}/>
  <section id={sheetId} className={css.sheet} role="dialog" aria-label={model.ctx.menuLabel} data-world-menu-sheet={context} hidden={!open}>
   <header className={css.head}><strong>{model.ctx.title}</strong><button type="button" className={css.x} aria-label="Close menu" onClick={()=>close()}>✕</button></header>
   <section className={css.sec} data-menu-section="view"><h3>View</h3><p className={css.note}>{model.ctx.frame}</p>
    <div className={css.views} role="group" aria-label="View">{model.views.filter(o=>!hideViews.includes(o.id)).map(o=><button key={o.id} type="button" aria-pressed={view===o.id} data-world-view={o.id} onClick={()=>onView(o.id)}><span aria-hidden="true">{o.icon}</span><span>{o.label}<small>{o.hint}</small></span></button>)}</div></section>
   <section className={css.sec} data-menu-section="place"><h3>{context==='home'?'In the pocket universe':'In this habitat'}</h3>
    {extra&&extra.length?<div className={css.links}>{extra.map(x=>x.onClick?<button key={x.label} type="button" {...(x.attr?{[x.attr]:''}:{})} onClick={()=>{close(false);x.onClick?.();}}><span aria-hidden="true">{x.icon||'→'}</span>{x.label}</button>:<a key={x.label} href={x.href} onClick={()=>close(false)}><span aria-hidden="true">{x.icon||'→'}</span>{x.label}</a>)}</div>:null}
    <div ref={setPlace} data-menu-host="place" className={css.host}/></section>
   <section className={css.sec} data-menu-section="tools"><h3>Pocket tools</h3><div ref={setTools} data-menu-host="tools" className={css.host}/></section>
   <section className={css.sec} data-menu-section="diary"><h3>Camera &amp; diary</h3>
    <div className={css.links}>
     <button type="button" aria-label={model.reset.aria} data-menu-reset onClick={()=>{window.dispatchEvent(new Event(POCKET_3D_CAMERA_RESET));}}><span aria-hidden="true">🎥</span>{model.reset.label}</button>
     <a href={model.diary.href} data-menu-diary onClick={()=>close(false)}><span aria-hidden="true">📔</span>{model.diary.label}</a>
     <a href={model.look.href} data-menu-look onClick={()=>close(false)}><span aria-hidden="true">🔍</span>{model.look.label}</a>
    </div></section>
   <section className={css.sec} data-menu-section="senses"><h3>Senses &amp; privacy</h3><p className={css.note}>{model.senses.note}</p>
    <div className={css.links}><a href={model.senses.href} data-menu-senses onClick={()=>close(false)}><span aria-hidden="true">🎙️</span>{model.senses.label}</a><a href="/privacy" onClick={()=>close(false)}><span aria-hidden="true">🔒</span>Privacy and info</a></div></section>
   <section className={css.sec} data-menu-section="about"><h3>About this world</h3>
    <div ref={setAbout} data-menu-host="about" className={css.host}/>
    <button type="button" className={css.mapBtn} data-menu-open-map onClick={()=>{close(false);window.dispatchEvent(new Event('beastbox:open-site-nav'));}}><span aria-hidden="true">🧩</span>Where am I in the one world? Open the world map</button></section>
  </section></>;
 return <div className={css.root} data-world-menu={context}>
  <button ref={fab} type="button" className={css.fab} data-world-menu-button aria-haspopup="dialog" aria-expanded={open} aria-controls={sheetId} aria-label={model.ctx.menuLabel} onClick={()=>setOpen(o=>!o)}><span aria-hidden="true">☰</span><span className={css.fabText}>{context==='cage'?'Habitat':'Universe'}</span></button>
  {mounted?createPortal(sheet,document.body):null}
 </div>;
}
