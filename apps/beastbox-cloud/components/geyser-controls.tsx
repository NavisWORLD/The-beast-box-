'use client';
// Geyser Jelly controls (PR 4/4): compact, closable panel; a bottom sheet on phones (fixed, no page scroll).
// Buttons dispatch 'beastbox:geyser'; tapping the geyser, volcano, whale or boat in 3D does the same.
import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import css from './geyser-controls.module.css';
export const GJ_HIDDEN_KEY='beastbox-geyser-controls-hidden';
const ACTIONS=[['erupt','🌋','Erupt'],['tremor','〰️','Tremor'],['breach','🐋','Breach'],['castoff','⛵','Cast off']] as const;
export default function GeyserControls(){
 const [ready,setReady]=useState(false);const [hidden,setHidden]=useState(false);const [last,setLast]=useState('');
 useEffect(()=>{try{setHidden(sessionStorage.getItem(GJ_HIDDEN_KEY)==='1');}catch{}
  const onReady=()=>setReady(true);const onEv=(e:any)=>{const a=String(e?.detail?.action||'');if(a)setLast(a);};
  window.addEventListener('beastbox:geyser-ready',onReady);window.addEventListener('beastbox:geyser',onEv);if((window as any).__geyserReady)setReady(true);
  return()=>{window.removeEventListener('beastbox:geyser-ready',onReady);window.removeEventListener('beastbox:geyser',onEv);};},[]);
 const hide=(v:boolean)=>{setHidden(v);try{v?sessionStorage.setItem(GJ_HIDDEN_KEY,'1'):sessionStorage.removeItem(GJ_HIDDEN_KEY);}catch{}};
 if(!ready)return null;
 if(hidden)return createPortal(<button type="button" className={css.tab} aria-label="Show Geyser Jelly controls" onClick={()=>hide(false)}>🌋</button>,document.body);
 return createPortal(<section className={css.panel} role="region" aria-label="Geyser Jelly controls">
  <header className={css.head}><strong>Geyser Jelly</strong><small>tap the geyser, volcano, whale or boat</small>
   <button type="button" className={css.close} aria-label="Close Geyser Jelly controls" onClick={()=>hide(true)}>×</button></header>
  <div className={css.row}>{ACTIONS.map(([a,ic,label])=><button key={a} type="button" aria-pressed={last===a} onClick={()=>window.dispatchEvent(new CustomEvent('beastbox:geyser',{detail:{action:a}}))}><span aria-hidden="true">{ic}</span>{label}</button>)}</div>
 </section>,document.body);
}
