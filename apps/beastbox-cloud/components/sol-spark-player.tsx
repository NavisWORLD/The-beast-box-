'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {useBeastSession} from './beast-session';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {checkedSpark} from '../public/spark/identity.mjs';
import {GBA_KEYS,gamepadButtons} from '../lib/companion/go-hud.mjs';
import {applyGameReturn,shownName} from '../lib/companion/session.mjs';
import {createPlayerDisplay} from '../lib/companion/player-display.mjs';
import GbaControls,{controllerInput} from './gba-controls';
import SolGameTalk from './sol-game-talk';
import css from './sol-spark-player.module.css';

const ROOT='https://navisworld.github.io';
const GAME=ROOT+'/Cosmic-synapse-the-living-universe-sim-engine-/arcade/sol-spark-gate/?mode=handheld&controller=previeworigin41&player=shell45&bridge=return44&audiofix=42&optical=01';
type Mode='normal'|'fullscreen'|'immersive'|'minimized';

export default function SolSparkPlayer({active=true,stage=true}:{active?:boolean;stage?:boolean}) {
 const {ready,session,change}=useBeastSession();
 const frame=useRef<HTMLIFrameElement>(null),shell=useRef<HTMLElement>(null);
 const display=useRef<ReturnType<typeof createPlayerDisplay>|null>(null);
 // Bind once on SEND BEAST. Care, navigation and layout never resend a starter save.
 const [bound,setBound]=useState<any>(null),[admitted,setAdmitted]=useState(false),[running,setRunning]=useState(false);
 const [mode,setMode]=useState<Mode>('normal'),[note,setNote]=useState('Your Beast has a cartridge to explore.');
 const [starting,setStarting]=useState(false),[returning,setReturning]=useState(false),[audio,setAudio]=useState({wanted:false,running:false});
 const sources=useRef(new Map<string,Set<string>>()),pressed=useRef(new Set<string>()),keyboardHeld=useRef(new Set<string>()),returnTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const pendingReturn=useRef<{id:string;event:string}|null>(null),sent=useRef(false);
 const observationWait=useRef<{requestId:string;beastId:string;timer:ReturnType<typeof setTimeout>;resolve:(value:any)=>void}|null>(null);
 const minimized=mode==='minimized'||(!stage&&!bound&&mode==='normal');
 const expanded=mode==='fullscreen'||mode==='immersive';
 const inputEnabled=running&&!minimized&&active;
 const inputLive=useRef(inputEnabled);inputLive.current=inputEnabled;
 const name=shownName(bound||session?.beast),id=bound?.qbeast?.profile.id||session?.beast?.qbeast?.profile.id||'';
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
   const source=['pointer','keyboard','gamepad'].includes(String(detail.source))?String(detail.source):'legacy';
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
   if(!event.isTrusted||target instanceof HTMLElement&&target.closest('textarea,input,select,[contenteditable="true"]'))return;
   if(target instanceof HTMLElement&&target.closest('button')&&(event.key==='Enter'||event.key===' '))return;
   if(event.key==='Escape'&&mode==='immersive'){void display.current?.normal();return;}
   if(!entry)return;event.preventDefault();if(event.repeat)return;
   if(event.type==='keydown')keyboardHeld.current.add(entry[0]);controllerInput(entry[0],event.type==='keydown','keyboard');
  };
  // Some browsers route the final keyup to the newly focused editor (or drop it).
  // Release ONLY the keyboard source when focus enters an editable field, keeping
  // simultaneous pointer/gamepad holds intact and preventing a stuck native key.
  const onFocus=(event:FocusEvent)=>{
   const target=event.target;
   if(!(target instanceof HTMLElement)||!target.closest('textarea,input,select,[contenteditable="true"]'))return;
   for(const button of keyboardHeld.current)controllerInput(button,false,'keyboard');
   keyboardHeld.current.clear();
  };
  window.addEventListener('keydown',onKey);window.addEventListener('keyup',onKey);
  window.addEventListener('focusin',onFocus,true);
  return()=>{window.removeEventListener('keydown',onKey);window.removeEventListener('keyup',onKey);window.removeEventListener('focusin',onFocus,true);release();};
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
  try{const text=serializeQbeast(bound.qbeast);checkedSpark(text);post({type:'sol-spark-qbeast',text});post({type:'sol-spark-player-state',active:active&&!document.hidden});}
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
    sent.current=true;setAdmitted(true);setNote(`${shownName(bound)} · same Beast verified. Ready for Lost COSMOS.`);return;
   }
   if(data?.type==='sol-spark-start-error'){setStarting(false);setNote('Lost COSMOS could not start: '+String(data.message||'Please try START LOST COSMOS again.').slice(0,180));return;}
   if(data?.type==='sol-spark-running'&&sent.current){setStarting(false);setRunning(true);setNote(`${shownName(bound)} · cartridge running. ${data.resumed?'Choose CONTINUE to keep your journey.':'Choose NEW GAME to begin your journey.'}`);return;}
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
 function bind() {
  try{checkedSpark(serializeQbeast(session.beast.qbeast));setBound(JSON.parse(JSON.stringify(session.beast)));setNote('Sending your Beast…');void display.current?.normal();}
  catch(error){setNote(error instanceof Error?error.message:'Choose your Beast first.');}
 }
 function saveJourney(){setReturning(true);setNote('Saving your native journey…');post({type:'sol-spark-return-request'});}
 return <section ref={shell} tabIndex={0} className={css.shell} data-lost-cosmos-player-shell data-spark-player data-creature-id={id} data-running={running} data-player-mode={minimized?'minimized':mode} data-player-stage={stage} aria-label={`Lost COSMOS player · ${name}`}>
  <header className={css.header}><div className={css.identity}><span className={css.light} data-lit={running} aria-hidden="true"/><div><strong>{name}</strong><small>LOST COSMOS · {running?'RUNNING':admitted?'BEAST VERIFIED':'YOUR BEAST / YOUR GAME'}</small></div></div>
   {minimized?(bound?<button type="button" onClick={()=>void display.current?.restore()}>RESTORE GAME</button>:<Link className={css.open} href="/sol-game" onClick={()=>void display.current?.restore()}>OPEN GAME</Link>):null}
   {minimized?<span className={css.sound}>{audio.wanted?(audio.running?'SOUND ON':'SOUND ARMED'):'SOUND OFF'}</span>:null}
  </header>
  <div className={css.status}><p role="status">{ready?note:'Finding your saved Beast…'}</p></div>
  <div className={css.screen}>
   {bound?<iframe ref={frame} title="Native LOST COSMOS cartridge" src={GAME} onLoad={send} allow="autoplay; fullscreen; gamepad; screen-wake-lock" allowFullScreen/>:<div className={css.poster}><span aria-hidden="true">🐉 🎮</span><p>Same Beast. New adventure.</p><button type="button" disabled={!ready||!session?.beast?.qbeast} onClick={bind}>SEND BEAST</button>{!session?.beast?.qbeast?<Link href="/spark/index.html">Choose your Spark Beast</Link>:null}</div>}
  </div>
  {running&&!minimized?<p className={css.gameAudioHint} role="status">{!audio.wanted?'🔊 iPhone: tap ENABLE GAME SOUND inside the Game Boy. Use 🔔 Test speaker there to check device output separately.':!audio.running?'🔊 Safari game sound is still unverified. In the Game Boy tap RESUME SOUND, then 🔔 TEST SPEAKER. A test chirp alone does not prove cartridge audio.':'🔊 The native emulator AudioContext is running. If silent, check the cartridge audio menu, iPhone media volume, Silent Mode and Bluetooth output.'}</p>:null}
  <div className={css.playAction}>{admitted&&!running?<button type="button" disabled={starting} onClick={()=>{setStarting(true);setNote('Starting Lost COSMOS…');post({type:'sol-spark-start'});}}>{starting?'STARTING…':'START LOST COSMOS'}</button>:null}</div>
  <div className={css.talk}><SolGameTalk active={active} observeGame={observeGame}/></div>
  <div className={css.controls}><GbaControls enabled={inputEnabled}/></div>
  <nav className={css.toolbar} aria-label="Game actions">
   <button type="button" onClick={()=>expanded?void display.current?.normal():void display.current?.expand()}>{expanded?'RETURN':'FULL SCREEN'}</button>
   <button type="button" onClick={()=>void display.current?.minimize()}>MINIMIZE</button>
   <button type="button" disabled={!running||returning} onClick={saveJourney}>{returning?'SAVING…':'SAVE JOURNEY'}</button>
   <Link href="/beast-cage" onClick={()=>void display.current?.minimize()}>BEAST BOX ↗</Link>
  </nav>
 </section>;
}
