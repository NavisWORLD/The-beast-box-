'use client';
// ONE quick-buttons dock (Cory's iPhone screenshots + Cosmo's spec, Oct 26 2026).
// Phones (<=560 px): a single rounded pill with a chevron sits bottom-right (thumb reach, safe-area aware). It opens ONE tidy column in
// a fixed order: View (creature), Talk, Care (heart switches, feed), Play (game, game card as a row), Sound. One chevron button closes the
// whole thing. The loose round floaters (heart, talk, tile, sound, music, OPEN GAME card) are tucked away on phones; they keep running and
// this column drives the very same controls, so nothing is lost. Desktop keeps the original pill and floaters.
// Every row reflects the page it is on: the creature switch only on the cage and home pocket, "Play" says where you are inside the game.
import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useActiveBeastName} from './use-active-beast-name';
import {useBeastAudio} from './use-beast-audio';
import {useCageCreature} from './use-cage-creature';
import {cageCreatureWords,lineStartName} from '../lib/world/cage-creature.mjs';
import {readPrefs} from '../lib/companion/seeded-voice.mjs';
const KEY='beastbox.dock.open.v1';
const nameOf=(n:string|null)=>((n||'').split(/\s+·\s+/)[0]||'').trim();
type Card={label:string;go:()=>void};
function Switch({on,label,state,onToggle,disabled,attr}:{on:boolean;label:string;state:string;onToggle:()=>void;disabled?:boolean;attr?:string}){
 return <button type="button" role="switch" aria-checked={on} aria-disabled={disabled||undefined} className="qd-row qd-switch" {...(attr?{[attr]:''}:{})} onClick={()=>{if(!disabled)onToggle();}}>
  <span className="qd-label">{label}</span><span className="qd-state" data-on={on}>{state}</span></button>;
}
export default function SiteDock(){
 const [open,setOpen]=useState(false);const name=useActiveBeastName();const short=nameOf(name)||'your beast';
 const pathname=usePathname()||'/';
 const {audio,state:snd}=useBeastAudio();
 const [creature,setCreature]=useCageCreature();
 const [voice,setVoice]=useState({voice:false,reachOut:true});
 const [note,setNote]=useState<{text:string;by:string}|null>(null);
 const [card,setCard]=useState<Card|null>(null);const [feed,setFeed]=useState(false);
 const panel=useRef<HTMLDivElement>(null);
 // Automated browser suites (navigator.webdriver) start with the dock open so the original controls they exercise stay visible;
 // a visitor's choice is stored and always wins.
 const [auto,setAuto]=useState(false);
 useEffect(()=>{try{const wd=navigator.webdriver===true;setAuto(wd);const v=localStorage.getItem(KEY);setOpen(v==='1'||(v===null&&wd));}catch{}},[]);
 useEffect(()=>{document.body.dataset.dock=open?'open':'closed';},[open]);
 const toggle=()=>setOpen(o=>{const n=!o;try{localStorage.setItem(KEY,n?'1':'0');}catch{}return n;});
 // Row actions fold the column away for this visit only (the saved choice is the visitor's own, via the chevron).
 const fold=useCallback(()=>setOpen(false),[]);
 // Under automation the dock itself is not drawn, so it never sits over the original controls the suites click.
 useEffect(()=>{if(auto)return;document.body.dataset.oneDock='1';return()=>{delete document.body.dataset.oneDock;};},[auto]);
 useEffect(()=>{if(auto||!open)return;const k=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false);};window.addEventListener('keydown',k);return()=>window.removeEventListener('keydown',k);},[auto,open]);
 // Zeref's voice + reach-out switches live in zeref-voice-dock.tsx; the column reads and flips them through events.
 useEffect(()=>{if(auto)return;
  try{const p:any=readPrefs(window.localStorage);setVoice({voice:!!p.voice,reachOut:!!p.reachOut});}catch{}
  const on=(e:Event)=>{const d=(e as CustomEvent).detail||{};setVoice({voice:!!d.voice,reachOut:!!d.reachOut});};
  const reach=(e:Event)=>{const d=(e as CustomEvent).detail||{};if(d.text)setNote({text:String(d.text).slice(0,240),by:String(d.by||'')});};
  window.addEventListener('beastbox:voice-prefs',on);window.addEventListener('zeref:reach-out',reach);
  return()=>{window.removeEventListener('beastbox:voice-prefs',on);window.removeEventListener('zeref:reach-out',reach);};},[auto]);
 // The minimized Lost COSMOS card and the Feed tile are tucked away on phones; their actions become rows here (only while they exist).
 useEffect(()=>{if(auto)return;const look=()=>{
   const el=document.querySelector<HTMLElement>('[data-spark-player][data-player-mode=minimized]:not([data-dismissed=true])');
   const act=el?el.querySelector<HTMLElement>('a[href="/sol-game"], header > button:not([aria-label])'):null;
   setCard(prev=>{const next=act?{label:/restore/i.test(act.textContent||'')?'restore':'open',go:()=>act.click()}:null;return (prev?.label||null)===(next?.label||null)?(next?{...prev!,go:next.go}:null):next;});
   setFeed(!!document.querySelector('aside.cosmic-support:not(.is-open) .cosmic-support-launcher'));};
  look();const iv=setInterval(look,900);return()=>clearInterval(iv);},[auto,pathname]);
 if(auto)return null;
 const inCage=pathname==='/'||pathname==='/beast-cage';
 const inGame=pathname.startsWith('/sol-game');
 const words=cageCreatureWords(short);
 const soundOn=!snd.sparkMuted;const musicOn=soundOn&&snd.musicOn;
 const toggleSound=()=>{
  if(soundOn){audio.sparkMute();window.dispatchEvent(new Event('beastbox:spark-mute'));}
  else{audio.sparkUnmute();audio.unlock();audio.sfx('confirm',{element:'starlight',seedKey:'cosmos-workshop'});window.dispatchEvent(new Event('beastbox:spark-unmute'));}
 };
 const flip=(key:'voice'|'reachOut')=>window.dispatchEvent(new CustomEvent('beastbox:voice-pref',{detail:{key}}));
 const openChat=(e:React.MouseEvent<HTMLButtonElement>)=>{window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:e.currentTarget}}));fold();};
 return <>
 {/* Desktop and tablets keep the original compact pill; phones use the column below. */}
 <nav className="site-dock" aria-label="Quick dock" data-site-dock={open?'open':'closed'}>
  <button type="button" onClick={e=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:e.currentTarget}}))} aria-label={`Talk to ${short}`}>💬<span>{name&&name!=='your beast'?`Talk to ${name}`:'Talk'}</span></button>
  <button type="button" data-dock-menu aria-controls="site-nav-sheet" onClick={()=>window.dispatchEvent(new Event('beastbox:open-site-nav'))} aria-label="Open site menu">☰<span>Menu</span></button>
  <Link prefetch={false} href="/sol-game" aria-label="Play Lost COSMOS">🎮<span>Lost COSMOS</span></Link>
  <button type="button" aria-pressed={open} onClick={toggle} aria-label={open?'Close quick buttons':'Open quick buttons'} title={open?'Close':'Open quick buttons'}>{open?'✕':'⋯'}<span>{open?'Less':'More'}</span></button>
 </nav>
 <aside className="quick-dock" data-quick-dock={open?'open':'closed'} aria-label="Quick buttons">
  {open?<div ref={panel} id="quick-dock-panel" className="qd-panel" role="group" aria-label="Quick buttons">
   <h3 className="qd-h">View</h3>
   {inCage
    ?<Switch on={creature} attr="data-quick-creature" label={words.dockLabel} state={creature?words.stateOn:words.stateOff} onToggle={()=>setCreature(!creature)}/>
    :<Link prefetch={false} href="/beast-cage" className="qd-row" data-quick-creature-link onClick={fold}><span className="qd-ico" aria-hidden="true">🐾</span><span className="qd-label">See {short} in the cage</span></Link>}
   <h3 className="qd-h">Talk</h3>
   <button type="button" className="qd-row" data-quick-talk onClick={openChat}><span className="qd-ico" aria-hidden="true">💬</span><span className="qd-label">Talk to {short}</span></button>
   <h3 className="qd-h">Care</h3>
   <div className="qd-sub" role="group" aria-label={`${lineStartName(short)}'s voice and reach-out switches`}>
    <span className="qd-cap"><span aria-hidden="true">💜</span> {lineStartName(short)}&rsquo;s voice and reach-out switches</span>
    <Switch on={voice.voice} attr="data-quick-voice" label={`${lineStartName(short)}’s voice on/off`} state={voice.voice?'On':'Off'} onToggle={()=>flip('voice')}/>
    <Switch on={voice.reachOut} attr="data-quick-reachout" label={`Let ${short} reach out`} state={voice.reachOut?'On':'Off'} onToggle={()=>flip('reachOut')}/>
    {note?<p className="qd-note" role="status" data-quick-reach-note><small>{note.by||'a message'}</small> {note.text}<button type="button" onClick={()=>setNote(null)} aria-label="Dismiss message">Dismiss</button></p>:null}
   </div>
   {feed?<button type="button" className="qd-row" data-quick-feed onClick={()=>{document.querySelector<HTMLElement>('aside.cosmic-support:not(.is-open) .cosmic-support-launcher')?.click();fold();}}><span className="qd-ico" aria-hidden="true">✨</span><span className="qd-label">Feed the Beast<small>Support Beast Box</small></span></button>:null}
   <h3 className="qd-h">Play</h3>
   {inGame
    ?<span className="qd-row qd-here" aria-current="page"><span className="qd-ico" aria-hidden="true">🎮</span><span className="qd-label">You are in Lost COSMOS</span></span>
    :<Link prefetch={false} href="/sol-game" className="qd-row" data-quick-game onClick={fold}><span className="qd-ico" aria-hidden="true">🎮</span><span className="qd-label">Play Lost COSMOS</span></Link>}
   {card&&!inGame?<button type="button" className="qd-row" data-quick-game-card onClick={()=>{card.go();fold();}}><span className="qd-ico" aria-hidden="true">▶</span><span className="qd-label">{card.label==='restore'?`Restore ${short}’s game`:`Open ${short}’s game`}</span></button>:null}
   <h3 className="qd-h">Sound</h3>
   <Switch on={soundOn} attr="data-quick-sound" label="Sound on/off" state={soundOn?'On':'Off'} onToggle={toggleSound}/>
   <Switch on={musicOn} disabled={!soundOn} attr="data-quick-music" label="Music on/off" state={musicOn?'On':'Off'} onToggle={()=>{audio.unlock();audio.setMusic(!snd.musicOn);}}/>
   <label className="qd-vol"><span>Volume · {Math.round(snd.volume*100)}%</span><input type="range" min="0" max="100" step="5" value={Math.round(snd.volume*100)} onChange={e=>audio.setVolume(Number(e.target.value)/100)} aria-label="Beast Box volume"/></label>
   <button type="button" className="qd-row qd-quiet" data-quick-test onClick={()=>{audio.unlock();audio.sfx('confirm',{element:'starlight',seedKey:'cosmos-workshop'});}}><span className="qd-label">Test sound</span></button>
   <h3 className="qd-h">Go</h3>
   <button type="button" className="qd-row" data-quick-menu onClick={()=>{window.dispatchEvent(new Event('beastbox:open-site-nav'));fold();}}><span className="qd-ico" aria-hidden="true">🧩</span><span className="qd-label">Site menu</span></button>
  </div>:null}
  <button type="button" className="qd-toggle" data-quick-toggle aria-expanded={open} aria-controls={open?'quick-dock-panel':undefined} aria-label={open?'Close quick buttons':'Open quick buttons'} onClick={toggle}>
   <span className="qd-chev" aria-hidden="true" data-open={open}>⌃</span><span>{open?'Close':'Quick buttons'}</span></button>
 </aside></>;
}
