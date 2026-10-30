'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import Link from 'next/link';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
import {createGameHandoff} from '../lib/companion/game-handoff.mjs';
import {GBA_KEYS,gamepadButtons} from '../lib/companion/go-hud.mjs';
import {applyGameReturn,shownName} from '../lib/companion/session.mjs';
import {importIdFromSearch,readImportedBeast} from '../lib/companion/game-import.mjs';
import {createPlayerDisplay} from '../lib/companion/player-display.mjs';
import GbaControls,{controllerInput} from './gba-controls';
import SolGameTalk from './sol-game-talk';
import {gameBeastKey} from '../lib/companion/sol-game-talk.mjs';
import css from './sol-spark-player.module.css';
export const MINI_HIDDEN_KEY='beastbox-mini-player-hidden';

const ROOT='https://navisworld.github.io';
const GAME=ROOT+'/Cosmic-synapse-the-living-universe-sim-engine-/arcade/sol-spark-gate/?mode=handheld&controller=previeworigin41&player=shell45&bridge=return44&audiofix=42&optical=01';
type Mode='normal'|'fullscreen'|'immersive'|'minimized';

export default function SolSparkPlayer({active=true,stage=true}:{active?:boolean;stage?:boolean}) {
 const {ready,session,change}=useBeastSession();
 const {profile:cageProfile}=useCompanion();
 const frame=useRef<HTMLIFrameElement>(null),shell=useRef<HTMLElement>(null);
 const display=useRef<ReturnType<typeof createPlayerDisplay>|null>(null);
 // Bind once on SEND BEAST. Care, navigation and layout never resend a starter save.
 const [visiting,setVisiting]=useState<any>(null);
 // Floating mini-player card can be closed (per session) and reopened from a small tab; the cartridge stays mounted.
 const [cardHidden,setCardHidden]=useState(false);
 useEffect(()=>{try{setCardHidden(sessionStorage.getItem(MINI_HIDDEN_KEY)==='1');}catch{}},[]);
 const hideCard=(v:boolean)=>{setCardHidden(v);try{v?sessionStorage.setItem(MINI_HIDDEN_KEY,'1'):sessionStorage.removeItem(MINI_HIDDEN_KEY);}catch{}};
 const [bound,setBound]=useState<any>(null),[admitted,setAdmitted]=useState(false),[running,setRunning]=useState(false);
 const [menuOpen,setMenuOpen]=useState(false);
 const [mode,setMode]=useState<Mode>('normal'),[note,setNote]=useState('Your Beast has a cartridge to explore.');
 const [paused,setPaused]=useState(false),[pausePending,setPausePending]=useState(false),[reloading,setReloading]=useState(false),[bridgeStatus,setBridgeStatus]=useState('No saved companion has been sent.');
 const [stalled,setStalled]=useState(false),[frameKey,setFrameKey]=useState(0),[starting,setStarting]=useState(false),[returning,setReturning]=useState(false),[audio,setAudio]=useState({wanted:false,running:false});
 const sources=useRef(new Map<string,Set<string>>()),pressed=useRef(new Set<string>()),keyboardHeld=useRef(new Set<string>()),returnTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const pendingReturn=useRef<{id:string;event:string}|null>(null),sent=useRef(false);
 const modelHeld=useRef<string|null>(null);
 const observationWait=useRef<{requestId:string;beastId:string;timer:ReturnType<typeof setTimeout>;resolve:(value:any)=>void}|null>(null);
 const minimized=mode==='minimized'||(!stage&&!bound&&mode==='normal');
 // The minimized pill steps aside while the page scrolls, so it never sits on a row you are reading or tapping mid-scroll.
 useEffect(()=>{if(!minimized)return;let timer=0;const el=shell.current;const on=()=>{if(!el)return;el.dataset.scrolling='true';window.clearTimeout(timer);timer=window.setTimeout(()=>{el.dataset.scrolling='false';},650);};window.addEventListener('scroll',on,{passive:true});return()=>{window.removeEventListener('scroll',on);window.clearTimeout(timer);if(el)el.dataset.scrolling='false';};},[minimized]);
 const expanded=mode==='fullscreen'||mode==='immersive';
 const inputEnabled=running&&!paused&&!pausePending&&!reloading&&!minimized&&active;
 const inputLive=useRef(inputEnabled);inputLive.current=inputEnabled;
 // Header names the same creature the Talk launcher and chat use (Cory 825654e1: header said 'Beast' while chat said Mirayx).
 const name=(bound||session?.beast)?shownName(bound||session?.beast):talkPersona({beast:null,cage:cageProfile}).name,id=bound?.qbeast?.profile.id||session?.beast?.qbeast?.profile.id||'';
 const post=useCallback((data:Record<string,unknown>)=>frame.current?.contentWindow?.postMessage(data,ROOT),[]);
 // Optical state comes only from the running native framebuffer on explicit tap.
 // Never treat these numbers as semantic recognition, gameplay authority or a save.
 const observeGame=useCallback(()=>new Promise<any|null>(resolve=>{
  if(!running||!bound?.qbeast?.profile?.id||!frame.current?.contentWindow){resolve(null);return;}
  if(observationWait.current){resolve(null);return;}
  const requestId=crypto.randomUUID();
  const beastId=bound.qbeast.profile.id;
  const timer=setTimeout(()=>{
   if(observationWait.current?.requestId===requestId){observationWait.current=null;resolve(null);}
  },4000);
  observationWait.current={requestId,beastId,timer,resolve};
  post({type:'sol-spark-observe-request',requestId,qbeast_id:beastId});
 }),[post,running,bound]);
 useEffect(()=>()=>{const wait=observationWait.current;if(wait){clearTimeout(wait.timer);wait.resolve(null);observationWait.current=null;}},[]);
 const release=useCallback(()=>{
  window.dispatchEvent(new Event('beastbox:gba-release'));
  for(const button of pressed.current)post({type:'sol-spark-input',button,down:false});
  if(modelHeld.current){controllerInput(modelHeld.current,false,'agent');modelHeld.current=null;}
  pressed.current.clear();sources.current.clear();
  keyboardHeld.current.clear();
 },[post]);
 useEffect(()=>{
  const node=shell.current;if(!node)return;
  const controller=createPlayerDisplay({document,shell:node,changed:(next:Mode)=>setMode(next),release});
  display.current=controller;
  return()=>{controller.dispose();display.current=null;};
 },[release]);
 useEffect(()=>{if(!inputEnabled)release();},[inputEnabled,release]);
 useEffect(()=>{if(!stage&&bound)void display.current?.minimize();},[stage,bound]);
 // One overlay placement system: publish the player mode so fixed docks (sound, Talk launcher,
 // companion pill) move out of the controls instead of each guessing.
 useEffect(()=>{const root=document.documentElement;root.dataset.gamePlayer=minimized?'minimized':mode;return()=>{delete root.dataset.gamePlayer;};},[minimized,mode]);
 useEffect(()=>{
  if(mode!=='immersive')return;
  const body=document.body,html=document.documentElement,x=window.scrollX,y=window.scrollY;
  const old={overflow:body.style.overflow,position:body.style.position,top:body.style.top,left:body.style.left,width:body.style.width,html:html.style.overflow};
  body.style.overflow='hidden';body.style.position='fixed';body.style.top=`-${y}px`;body.style.left=`-${x}px`;body.style.width='100%';html.style.overflow='hidden';
  return()=>{Object.assign(body.style,{overflow:old.overflow,position:old.position,top:old.top,left:old.left,width:old.width});html.style.overflow=old.html;window.scrollTo(x,y);};
 },[mode]);
 useEffect(()=>{
  const update=()=>post({type:'sol-spark-player-state',active:active&&!minimized&&!document.hidden});
  update();document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update);
 },[active,minimized,bound,post]);
 useEffect(()=>{
  window.dispatchEvent(new CustomEvent('beastbox:gba-running',{detail:running&&active&&!minimized&&audio.wanted}));
  return()=>{window.dispatchEvent(new CustomEvent('beastbox:gba-running',{detail:false}));};
 },[running,active,minimized,audio.wanted]);
 useEffect(()=>{
  const forward=(event:Event)=>{
   const detail=(event as CustomEvent<{button?:unknown;down?:unknown;source?:unknown}>).detail;
   const button=typeof detail?.button==='string'?detail.button.toLowerCase():'';
   if(!Object.prototype.hasOwnProperty.call(GBA_KEYS,button)||typeof detail?.down!=='boolean')return;
   if(detail.down&&!inputLive.current)return;
   const source=['pointer','keyboard','gamepad','agent'].includes(String(detail.source))?String(detail.source):'legacy';
   const held=sources.current.get(button)||new Set<string>();
   if(detail.down)held.add(source);else held.delete(source);
   if(held.size)sources.current.set(button,held);else sources.current.delete(button);
   const down=held.size>0;
   if(!frame.current?.contentWindow||pressed.current.has(button)===down)return;
   if(down)pressed.current.add(button);else pressed.current.delete(button);
   // The legacy local fallback can emit the same edge. Forward each native edge once.
   post({type:'sol-spark-input',button,down});
  };
  const hidden=()=>{if(document.hidden)release();};
  window.addEventListener('beastbox:gba-input',forward);window.addEventListener('blur',release);window.addEventListener('orientationchange',release);document.addEventListener('visibilitychange',hidden);
  return()=>{release();window.removeEventListener('beastbox:gba-input',forward);window.removeEventListener('blur',release);window.removeEventListener('orientationchange',release);document.removeEventListener('visibilitychange',hidden);};
 },[post,release]);
 useEffect(()=>{
  if(!inputEnabled)return;
  const onKey=(event:KeyboardEvent)=>{
   const target=event.target;
   const entry=Object.entries(GBA_KEYS).find(([,spec])=>spec.key.toLowerCase()===event.key.toLowerCase());
   if(event.isTrusted&&event.type==='keyup'&&entry&&keyboardHeld.current.has(entry[0])){keyboardHeld.current.delete(entry[0]);controllerInput(entry[0],false,'keyboard');return;}
   if(!event.isTrusted||target instanceof HTMLElement&&target.closest('textarea,input,select,[contenteditable="true"],[data-companion-chat-overlay]'))return;
   if(target instanceof HTMLElement&&target.closest('button')&&(event.key==='Enter'||event.key===' '))return;
   if(event.key==='Escape'&&mode==='immersive'){void display.current?.normal();return;}
   if(!entry)return;event.preventDefault();if(event.repeat)return;
   if(event.type==='keydown')keyboardHeld.current.add(entry[0]);controllerInput(entry[0],event.type==='keydown','keyboard');
  };
  // Some browsers route the final keyup to the newly focused editor (or drop it).
  // Release ONLY the keyboard source when focus enters an editable field, keeping
  // simultaneous pointer/gamepad holds intact and preventing a stuck native key.
  const releaseKeyboard=()=>{
   // Consult the actual input-source map. KeyboardHeld is a convenience cache,
   // but the source map owns the native press and must never remain stuck.
   const active=new Set([...keyboardHeld.current,...[...sources.current].filter(([,held])=>held.has('keyboard')).map(([button])=>button)]);
   for(const button of active)controllerInput(button,false,'keyboard');
   keyboardHeld.current.clear();
  };
  const onFocus=(event:FocusEvent)=>{
   const target=event.target;
   if(target instanceof HTMLElement&&target.closest('textarea,input,select,[contenteditable="true"],[data-companion-chat-overlay]'))releaseKeyboard();
  };
  const onFocusOut=(event:FocusEvent)=>{
   const next=event.relatedTarget;
   if(next instanceof HTMLElement&&next.closest('textarea,input,select,[contenteditable="true"],[data-companion-chat-overlay]'))releaseKeyboard();
  };
  window.addEventListener('keydown',onKey);window.addEventListener('keyup',onKey);
  document.addEventListener('focusin',onFocus,true);
  document.addEventListener('focusout',onFocusOut,true);
  return()=>{window.removeEventListener('keydown',onKey);window.removeEventListener('keyup',onKey);document.removeEventListener('focusin',onFocus,true);document.removeEventListener('focusout',onFocusOut,true);release();};
 },[inputEnabled,mode,release]);
 useEffect(()=>{
  if(!inputEnabled||typeof navigator.getGamepads!=='function')return;
  let raf=0,held=new Set<string>();
  const reset=()=>{for(const button of held)controllerInput(button,false,'gamepad');held.clear();};
  const poll=()=>{
   raf=window.requestAnimationFrame(poll);const next=new Set<string>();
   if(!document.hidden)for(const pad of navigator.getGamepads())if(pad&&pad.connected!==false)for(const button of gamepadButtons(pad))next.add(button);
   for(const button of next)if(!held.has(button))controllerInput(button,true,'gamepad');
   for(const button of held)if(!next.has(button))controllerInput(button,false,'gamepad');held=next;
  };
  raf=window.requestAnimationFrame(poll);window.addEventListener('gamepaddisconnected',reset);window.addEventListener('beastbox:gba-release',reset);
  return()=>{window.cancelAnimationFrame(raf);reset();window.removeEventListener('gamepaddisconnected',reset);window.removeEventListener('beastbox:gba-release',reset);};
 },[inputEnabled]);
 const send=useCallback(()=>{
  if(!bound||sent.current)return;
  try{post(createGameHandoff(bound));post({type:'sol-spark-player-state',active:active&&!document.hidden});}
  catch(error){setNote(error instanceof Error?error.message:'Your Beast could not be verified.');}
 },[bound,active,post]);
 useEffect(()=>{
  const message=(event:MessageEvent)=>{
   if(event.origin!==ROOT||event.source!==frame.current?.contentWindow)return;
   const data=event.data;
   if(data?.type==='sol-spark-observation'){
    const waiting=observationWait.current;
    if(!waiting||data.requestId!==waiting.requestId||data.qbeast_id!==waiting.beastId)return;
    clearTimeout(waiting.timer);observationWait.current=null;
    waiting.resolve(data.observation?.status==='observed'?data.observation:null);
    return;
   }
   if(data?.type==='sol-spark-ready'){send();return;}
   if(data?.type==='sol-spark-admitted'){
    if(data.id!==bound?.qbeast?.profile.id||data.seed!==bound?.seed){setNote('The game could not verify this Beast.');return;}
    sent.current=true;setAdmitted(true);setBridgeStatus('Verified local QBEAST mailbox. Native roster import is not confirmed yet.');setNote(`${shownName(bound)} · identity validated. Ready to start Lost COSMOS.`);return;
   }
   if(data?.type==='sol-spark-identity-status'){
    if(data.qbeast_id!==bound?.qbeast?.profile.id||data.seed!==bound?.seed)return;
    const label=data.status==='imported'?'Native saved roster matches this exact QBEAST.':data.status==='mailbox-ready'?'Local mailbox ready; native companion import pending.':data.status==='missing'?'No matching native companion: choose CONTINUE for an existing journey, or recover the compatible saved beast.':'Native identity validation failed; recover the original save.';
    setBridgeStatus(label+' '+String(data.message||'').slice(0,180));return;
   }
   if(data?.type==='sol-spark-pause-state'){setPausePending(false);if(data.applied===true){setPaused(data.paused===true);setNote(data.paused?'Cartridge paused by your action.':'Cartridge resumed.');}else setNote('The native core could not change pause state.');return;}
   if(data?.type==='sol-spark-reloading'){setReloading(true);setNote('Reloading the current identity-checked battery…');return;}
   if(data?.type==='sol-spark-reload-error'){setReloading(false);setNote('Reload stopped: '+String(data.message||'The current save could not be verified.').slice(0,180));return;}
   if(data?.type==='sol-spark-start-error'){setStarting(false);setNote('Lost COSMOS could not start: '+String(data.message||'Please try START LOST COSMOS again.').slice(0,180));return;}
   if(data?.type==='sol-spark-running'&&sent.current){setStarting(false);setReloading(false);setPaused(false);setRunning(true);setNote(`${shownName(bound)} · cartridge running. ${data.resumed?'Choose CONTINUE to keep your journey.':'Choose NEW GAME to begin your journey.'}`);return;}
   if(data?.type==='sol-spark-audio-state'){setAudio({wanted:data.wanted===true,running:data.running===true});return;}
   if(data?.type==='sol-spark-input-ack'&&data.down===true&&data.applied!==true){setNote('The cartridge is still starting. Try again when the picture moves.');return;}
   if(data?.type==='sol-spark-return'){
    const payload=data.payload;
    if(!returning||!payload||payload.schema!=='lost-cosmos-return-v1'||payload.qbeast_id!==bound?.qbeast?.profile.id||payload.qbeast_id!==session?.beast?.qbeast?.profile.id||!/^native-[0-9a-f]{64}$/.test(payload.event_id||'')||typeof payload.native_save!=='string'||payload.native_save.length!==43692){setReturning(false);setNote('This journey does not match your selected Beast. Nothing was changed.');return;}
    pendingReturn.current={id:payload.qbeast_id,event:payload.event_id};void change(draft=>{const result=applyGameReturn(draft,payload);if(!result.ok)throw Error('Journey did not match this Beast.');}).then(saved=>{if(!saved.ok){pendingReturn.current=null;setReturning(false);setNote(saved.reason||'This journey could not be saved. Try SAVE JOURNEY again.');}});return;
   }
   if(data?.type==='sol-spark-return-error'){setReturning(false);setNote('Journey save: '+String(data.message||'Try saving after entering the game.').slice(0,180));return;}
   if(data?.type==='sol-spark-rejected'&&!sent.current)setNote('Beast verification: '+String(data.message).slice(0,180));
  };
  window.addEventListener('message',message);return()=>window.removeEventListener('message',message);
 },[send,bound,session,returning,change]);
 useEffect(()=>{
  const pending=pendingReturn.current;if(!pending)return;
  if(session?.beast?.qbeast?.profile.id===pending.id&&session.beast.localGrowth?.applied?.includes(pending.event)){pendingReturn.current=null;setReturning(false);setNote(`${name} · journey saved to the same Beast. Your cartridge is still running.`);}
 },[session,name]);
 useEffect(()=>{
  if(!returning)return;
  returnTimer.current=setTimeout(()=>{pendingReturn.current=null;setReturning(false);setNote('The journey did not return yet. Your game is still running; try SAVE JOURNEY again.');},15000);
  return()=>{if(returnTimer.current)clearTimeout(returnTimer.current);};
 },[returning]);
 useEffect(()=>{
  if(!starting)return;const timer=setTimeout(()=>{setStarting(false);setNote('Lost COSMOS is taking longer to load. Keep the game open, or try START LOST COSMOS again.');},90000);return()=>clearTimeout(timer);
 },[starting]);
 // If the cartridge page never answers (no 'admitted' message), say so after 20 s and offer a real retry instead of 'Loading the cartridge…' forever.
 useEffect(()=>{if(!bound||admitted||running){setStalled(false);return;}const t=setTimeout(()=>setStalled(true),20000);return()=>clearTimeout(t);},[bound,admitted,running,frameKey]);
 function startGame(){if(starting||!admitted||running)return;setStarting(true);setNote('Starting Lost COSMOS…');post({type:'sol-spark-start'});}
 function retryLoad(){sent.current=false;setStalled(false);setAdmitted(false);setNote('Loading the cartridge again…');setFrameKey(k=>k+1);}
 useEffect(()=>{const id=importIdFromSearch(window.location.search);if(!id||id===session?.beast?.qbeast?.profile?.id)return;
  try{const beast=readImportedBeast(window.localStorage,id);setVisiting(beast);setNote(shownName(beast)+' is visiting from the bridge. Tap SEND BEAST to play. Journeys save only to your active Beast.');}
  catch(error){setNote(error instanceof Error?error.message:'That Beast could not be imported.');}
 },[session?.beast?.qbeast?.profile?.id]);
 function bind() {
  const source=visiting||session?.beast;
  try{if(visiting)createGameHandoff(visiting);else createGameHandoff(session.beast);setBound(JSON.parse(JSON.stringify(source)));setNote('Sending your Beast…');void display.current?.normal();}
  catch(error){setNote(error instanceof Error?error.message:'Choose your Beast first.');}
 }
 const applyGameAction=useCallback(async(button:string,expectedKey:string):Promise<boolean>=>{
    const valid=['up','down','left','right','a','b'].includes(button);
    const identity=bound?.qbeast?.profile?.id&&bound.seed?bound.qbeast.profile.id+':'+bound.seed:'';
    if(!valid||!expectedKey||expectedKey!==identity||gameBeastKey(session)!==identity||
       !inputLive.current||!running||document.hidden||modelHeld.current)return false;
    modelHeld.current=button;
    try{
      controllerInput(button,true,'agent');
      await new Promise(resolve=>setTimeout(resolve,125));
      return inputLive.current && !document.hidden &&
             gameBeastKey(session)===expectedKey;
    }finally{
      controllerInput(button,false,'agent');
      if(modelHeld.current===button)modelHeld.current=null;
    }
  },[bound,session,running]);
 useEffect(()=>{if(!pausePending)return;const timeout=setTimeout(()=>{setPausePending(false);setNote('Pause response unavailable. The cartridge remains mounted.');},4000);return()=>clearTimeout(timeout);},[pausePending]);
 function pause(){release();setPausePending(true);post({type:'sol-spark-player-state',active:active&&!minimized,paused:!paused});}
 function reload(){release();setReloading(true);post({type:'sol-spark-reload-request'});}
 function saveJourney(){setReturning(true);setNote('Saving your native journey…');post({type:'sol-spark-return-request'});}
 const dismissed=minimized&&cardHidden;
 return <><section ref={shell} tabIndex={0} className={css.shell} data-dismissed={dismissed} aria-hidden={dismissed||undefined} data-lost-cosmos-player-shell data-spark-player data-creature-id={id} data-running={running} data-player-mode={minimized?'minimized':mode} data-player-stage={stage} aria-label={`Lost COSMOS player · ${name}`}>
  <header className={css.header}><div className={css.identity}><span className={css.light} data-lit={running} aria-hidden="true"/><div><strong>{name}</strong><small>LOST COSMOS · {running?'RUNNING':admitted?'BEAST VERIFIED':'YOUR BEAST / YOUR GAME'}</small></div></div>
   {minimized?(bound?<button type="button" onClick={()=>void display.current?.restore()}>RESTORE GAME</button>:<Link className={css.open} href="/sol-game" prefetch={false} onClick={()=>void display.current?.restore()}>OPEN GAME</Link>):null}
   {minimized?<button type="button" className={css.closeCard} aria-label="Close game card" onClick={()=>hideCard(true)}>×</button>:null}
   {minimized?<span className={css.sound}>{audio.wanted?(audio.running?'SOUND ON':'SOUND ARMED'):'SOUND OFF'}</span>:null}
   {!minimized?<div className={css.talk}><SolGameTalk active={active} observeGame={observeGame} applyGameAction={applyGameAction} canGuide={inputEnabled} gameKey={bound?.qbeast?.profile.id&&bound.seed?bound.qbeast.profile.id+':'+bound.seed:''}/></div>:null}
  </header>
  <div className={css.status}><p role="status">{ready?note:'Finding your saved Beast…'}</p><details><summary>Companion connection</summary><p>{bridgeStatus}</p><code>{id||'No canonical saved identity selected'}</code><p>Saved identities, display personas and local snapshots remain separate. Native palette/body representations use the recorded seed; web sprite accents may differ.</p>{!bound||bridgeStatus.startsWith('No matching')?<a href="/spark/index.html">Choose or recover a compatible Beast</a>:null}</details></div>
  <div className={css.screen} data-has-frame={!!bound}>
   {bound&&!running&&!starting?<div className={css.preboot} data-preboot-poster aria-hidden={false} role={admitted?'button':'note'} tabIndex={admitted?0:undefined} aria-label={admitted?'Start Lost COSMOS':undefined} data-preboot-start={admitted?'':undefined} onClick={admitted?startGame:undefined} onKeyDown={admitted?(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();startGame();}}:undefined} style={admitted?{cursor:'pointer',pointerEvents:'auto'}:stalled?{pointerEvents:'auto'}:undefined}><span aria-hidden="true">🎮</span><strong>{admitted?'Tap START LOST COSMOS':stalled?'The cartridge did not answer':'Loading the cartridge…'}</strong><small>{admitted?'The screen stays dark until the original cartridge boots.':stalled?'Nothing is lost. Try loading it again.':'Same ROM, same save. This is the page, not the game.'}</small>{!admitted&&stalled?<button type="button" data-rom-retry onClick={retryLoad} style={{minHeight:48,minWidth:120,marginTop:8}}>TRY AGAIN</button>:null}</div>:null}
   {bound?<iframe key={frameKey} ref={frame} title="Native LOST COSMOS cartridge" src={GAME} onLoad={send} allow="autoplay; fullscreen; gamepad; screen-wake-lock" allowFullScreen/>:<div className={css.poster}><span aria-hidden="true">🐉 🎮</span><p>Same Beast. New adventure.</p><button type="button" disabled={!ready||!(visiting||session?.beast)?.qbeast} onClick={bind} data-visiting={visiting?visiting.qbeast.profile.id:undefined}>SEND BEAST</button>{!session?.beast?.qbeast?<a href="/spark/index.html">Choose your Beast</a>:null}</div>}
  </div>
  {running&&!minimized&&!audio.running?<p className={css.gameAudioHint} role="status">🔊 If the game screen says TAP TO PLAY, tap it once: that tap wakes Safari sound inside the cartridge. Mute or unmute any time in ☰ MENU.</p>:null}
  <div className={css.playAction}>{admitted&&!running?<button type="button" disabled={starting} onClick={startGame}>{starting?'STARTING…':'START LOST COSMOS'}</button>:null}</div>
  <div className={css.controls}><GbaControls shoulders enabled={inputEnabled} onMenu={()=>setMenuOpen(v=>!v)}/></div>
  <nav className={css.toolbar} aria-label="Game actions">
   <button type="button" onClick={()=>expanded?void display.current?.normal():void display.current?.expand()}>{expanded?'RETURN':'FULL SCREEN'}</button>
   <button type="button" onClick={()=>void display.current?.minimize()}>MINIMIZE</button>
   <button type="button" aria-expanded={menuOpen} aria-controls="handheld-menu" onClick={()=>setMenuOpen(v=>!v)}>☰ MENU</button>
  </nav>
  {menuOpen?<div id="handheld-menu" className={css.menuDrawer} role="dialog" aria-label="Handheld menu" onKeyDown={e=>{if(e.key==='Escape')setMenuOpen(false);}}>
   <header><strong>HANDHELD MENU</strong><button type="button" aria-label="Close handheld menu" onClick={()=>setMenuOpen(false)}>×</button></header>
   <section aria-label="Play"><span>PLAY</span>
    <button type="button" disabled={!running||pausePending||reloading} onClick={pause}>{pausePending?'WAIT…':paused?'RESUME':'PAUSE'}</button>
   </section>
   <section aria-label="Save and load"><span>SAVE / LOAD</span>
    <button type="button" disabled={!running||returning} onClick={saveJourney}>{returning?'SAVING…':'SAVE JOURNEY'}</button>
    <button type="button" disabled={!running||reloading||returning} onClick={reload}>{reloading?'RELOADING…':'RELOAD SAVE'}</button>
   </section>
   <section aria-label="Sound"><span>SOUND</span><p>{audio.running?(audio.wanted?'Game sound is on (native emulator audio running).':'Game is muted.'):'Sound wakes when you tap TAP TO PLAY on the game screen. Use your phone volume for loudness.'}</p><button type="button" disabled={!running} aria-pressed={!audio.wanted} onClick={()=>post({type:'sol-spark-audio-mute',muted:audio.wanted})}>{audio.wanted?'MUTE GAME':'UNMUTE GAME'}</button></section>
   <section aria-label="Display"><span>DISPLAY</span>
    <button type="button" onClick={()=>{setMenuOpen(false);expanded?void display.current?.normal():void display.current?.expand();}}>{expanded?'RETURN TO PAGE':'FULL SCREEN'}</button>
    <button type="button" onClick={()=>{setMenuOpen(false);void display.current?.minimize();}}>MINIMIZE (keeps playing)</button>
   </section>
   <section aria-label="Cartridge"><span>CARTRIDGE</span><p>Lost COSMOS V12.2 · original ROM, unchanged · {name}{id?' · '+id:''}</p></section>
   <section aria-label="Input help"><span>INPUT</span><p>D-pad moves · A confirms/acts · B cancels · START opens the game menu · SELECT / L / R where the cartridge maps them. Keyboard: arrows, Z = A, X = B, Enter = START, V = SELECT, Q / E = L / R.</p></section>
   <Link href="/beast-cage" onClick={()=>{setMenuOpen(false);void display.current?.minimize();}}>BEAST BOX ↗</Link>
  </div>:null}
 </section>{dismissed&&typeof document!=='undefined'?createPortal(<button type="button" className={css.reopenTab} aria-label="Show game card" onClick={()=>hideCard(false)}>🎮</button>,document.body):null}</>;
}
