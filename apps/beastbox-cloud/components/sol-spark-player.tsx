'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {useBeastSession} from './beast-session';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {checkedSpark} from '../public/spark/identity.mjs';
import {GBA_KEYS, gamepadButtons} from '../lib/companion/go-hud.mjs';
import {applyGameReturn} from '../lib/companion/session.mjs';
import SolGameTalk from './sol-game-talk';
const ROOT='https://navisworld.github.io';
const GAME=ROOT+'/Cosmic-synapse-the-living-universe-sim-engine-/arcade/sol-spark-gate/?mode=handheld&controller=previeworigin41';
export default function SolSparkPlayer({compact=false,active=true}:{compact?:boolean;active?:boolean}){
 const {ready,session,change}=useBeastSession();
 const frame=useRef<HTMLIFrameElement>(null);
 const [started,setStarted]=useState(false),[note,setNote]=useState('Your saved QBEAST will enter the current native cartridge.'),[admitted,setAdmitted]=useState(false),[running,setRunning]=useState(false),[returning,setReturning]=useState(false);
 const beast=session?.beast;
 const send=useCallback(()=>{
  try{
   if(!beast?.qbeast)throw Error('Generate a Spark Beast first, then return here.');
   const text=serializeQbeast(beast.qbeast);checkedSpark(text);
   frame.current?.contentWindow?.postMessage({type:'sol-spark-qbeast',text},ROOT);
   frame.current?.contentWindow?.postMessage({type:'sol-spark-player-state',active:active&&!document.hidden},ROOT);
  }catch(err){setNote(err instanceof Error?err.message:'Could not verify the saved Beast.');}
 },[beast?.qbeast,active]);
 useEffect(()=>{
  const update=()=>frame.current?.contentWindow?.postMessage({type:'sol-spark-player-state',active:active&&!document.hidden},ROOT);
  update();document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update);
 },[active,started]);
 useEffect(()=>{
  const allowed=new Set(['up','down','left','right','a','b','start','select','l','r']);
  const forward=(event:Event)=>{
   if(!running)return;
   const detail=(event as CustomEvent<{button?:unknown;down?:unknown}>).detail;
   const button=typeof detail?.button==='string'?detail.button.toLowerCase():'';
   if(!allowed.has(button)||typeof detail?.down!=='boolean')return;
   frame.current?.contentWindow?.postMessage({type:'sol-spark-input',button,down:detail.down},ROOT);
  };
  window.addEventListener('beastbox:gba-input',forward);
  return()=>window.removeEventListener('beastbox:gba-input',forward);
 },[running]);
 useEffect(()=>{
  if(!running)return;
  const onKey=(event:KeyboardEvent)=>{
   const target=event.target;
   if(target instanceof HTMLElement&&target.closest('textarea, input'))return;
   const entry=Object.entries(GBA_KEYS).find(([,spec])=>spec.key.toLowerCase()===event.key.toLowerCase());
   if(!entry)return;
   event.preventDefault();
   if(event.type==='keydown'&&event.repeat)return;
   window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button:entry[0],down:event.type==='keydown'}}));
  };
  window.addEventListener('keydown',onKey);
  window.addEventListener('keyup',onKey);
  return()=>{window.removeEventListener('keydown',onKey);window.removeEventListener('keyup',onKey);};
 },[running]);
 useEffect(()=>{
  if(!running||typeof navigator.getGamepads!=='function')return;
  let frame=0;let active=new Set<string>();
  const release=()=>{for(const button of active)window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down:false}}));active=new Set();};
  const poll=()=>{
   frame=window.requestAnimationFrame(poll);
   const next=new Set<string>();
   for(const pad of navigator.getGamepads())if(pad)for(const button of gamepadButtons(pad))next.add(button);
   for(const button of next)if(!active.has(button))window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down:true}}));
   for(const button of active)if(!next.has(button))window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down:false}}));
   active=next;
  };
  frame=window.requestAnimationFrame(poll);
  return()=>{window.cancelAnimationFrame(frame);release();};
 },[running]);
 function hold(button:string,down:boolean,event:React.PointerEvent<HTMLButtonElement>){
  event.preventDefault();
  if(!running)return;
  window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down}}));
 }
 useEffect(()=>{
  const message=(event:MessageEvent)=>{
   if(event.origin!==ROOT||event.source!==frame.current?.contentWindow)return;
   if(event.data?.type==='sol-spark-ready')send();
   if(event.data?.type==='sol-spark-admitted'){
    if(event.data.id!==beast?.qbeast?.profile.id||event.data.seed!==beast?.seed){setNote('The game did not confirm the selected identity.');return;}
    setNote(`${beast.displayName||beast.genome.names[1]} · same QBEAST verified. Press Start Lost COSMOS.`);
    setAdmitted(true);
   }
   if(event.data?.type==='sol-spark-running'){
    setRunning(true);setReturning(false);setNote(`${beast?.displayName||beast?.genome?.names?.[1]||"Your Beast"} is in Lost COSMOS. The native cartridge is running.`);return;
   }
   if(event.data?.type==='sol-spark-input-ack'&&event.data.down===true&&event.data.applied!==true){
    setNote('The cartridge is still starting. Try that control again when the game picture is moving.');return;
   }
   if(event.data?.type==='sol-spark-return'){
    const payload=event.data.payload;
    if(!payload||payload.schema!=='lost-cosmos-return-v1'||payload.qbeast_id!==beast?.qbeast?.profile.id){setReturning(false);setNote('Lost COSMOS returned a journey for a different or invalid Beast. Nothing was changed.');return;}
    change(draft=>{applyGameReturn(draft,payload);});
    setReturning(false);setNote(`${beast?.displayName||beast?.genome?.names?.[1]||"Your Beast"} returned from Lost COSMOS. Native progress is saved to this same QBEAST.`);return;
   }
   if(event.data?.type==='sol-spark-return-error'){setReturning(false);setNote('Journey return: '+String(event.data.message||'The native save could not be returned.').slice(0,180));return;}
   if(event.data?.type==='sol-spark-rejected')setNote('Game handoff: '+String(event.data.message).slice(0,180));
  };
  window.addEventListener('message',message);return()=>window.removeEventListener('message',message);
 },[send,beast,change]);
 return <section data-spark-player data-creature-id={beast?.qbeast?.profile.id||''} style={{width:'100%',minWidth:0,color:'#d5def4'}}>
  <SolGameTalk active={active}/>
  {!started?<div style={{padding:compact?12:22,textAlign:'center'}}>
   <p>{ready?note:'Opening your local Beast…'}</p>
   <button type="button" disabled={!ready||!beast?.qbeast} onClick={()=>setStarted(true)} style={{padding:12,border:'1px solid #7ee7ff',borderRadius:8,background:'#14304a',color:'#7ee7ff'}}>SEND BEAST &amp; PLAY 🎮</button>
   {!beast?.qbeast?<p><a href="/spark/index.html">Generate your Spark Beast</a></p>:null}
  </div>:<>
   <p role="status" style={{fontSize:11,padding:'4px 10px',margin:0}}>{note}</p>
   {admitted&&!running?<button type="button" onClick={()=>{setNote('Starting the verified native cartridge…');frame.current?.contentWindow?.postMessage({type:'sol-spark-start'},ROOT);}} style={{margin:'8px 10px',padding:12,border:'1px solid #7ee7ff',borderRadius:8,background:'#14304a',color:'#7ee7ff'}}>START LOST COSMOS</button>:null}
   {running?<button type="button" disabled={returning} onClick={()=>{setReturning(true);setNote('Saving the native journey back to this Beast…');frame.current?.contentWindow?.postMessage({type:'sol-spark-return-request'},ROOT);}} style={{margin:'8px 10px',padding:12,border:'1px solid #7ee7ff',borderRadius:8,background:'#14304a',color:'#7ee7ff'}}>{returning?'SAVING JOURNEY…':'SAVE JOURNEY TO BEAST BOX'}</button>:null}
   <iframe ref={frame} title="Current native LOST COSMOS with your exact Spark QBEAST" src={GAME} onLoad={send} allow="autoplay; fullscreen; gamepad; screen-wake-lock" allowFullScreen style={{width:'100%',height:compact?610:850,border:0,display:'block'}}/>
   <div aria-label="Lost COSMOS controls" style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:8,padding:12,touchAction:'none'}}>
    {(['up','down','left','right','a','b','start','select'] as const).map(button=><button key={button} type="button" disabled={!running} aria-label={GBA_KEYS[button].label} onPointerDown={event=>hold(button,true,event)} onPointerUp={event=>hold(button,false,event)} onPointerCancel={event=>hold(button,false,event)} style={{minHeight:48,border:'1px solid #7ee7ff',borderRadius:8,background:'#14304a',color:'#7ee7ff',opacity:running?1:.5}}>{GBA_KEYS[button].label}</button>)}
   </div>
  </>}
 </section>;
}
