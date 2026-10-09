'use client';
import {useCallback, useEffect, useRef, useState} from 'react';
import {useBeastSession} from './beast-session';
import {beastIdentity} from '../lib/companion/session.mjs';
import {applySensedEvent,modelSensedContext} from '../lib/companion/sensory-bridge.mjs';
import styles from './companion-local-bay.module.css';
import {
  CompanionMemory, acceptHearing, acceptVision, birth, loopbackOnly, reply, simulateLive,
} from '../lib/companion-local.mjs';

const OLLAMA = 'http://127.0.0.1:11434/api/chat';
const WHISPER = 'http://127.0.0.1:8080/inference';
const MEMORY_KEY = 'beastbox-companion-memory-v1';
const BRAIN_KEY = 'beastbox-companion-brain-v1';
type Model={alias:string;ollama_name:string;smoke?:boolean;selectable?:boolean;eval?:Record<string,number>;honesty?:string;creature?:string};
type Line={role:'you'|'companion';text:string;speaker:string};

function readMemory(){
 try{
  const parsed=JSON.parse(window.localStorage.getItem(MEMORY_KEY)||'null');
  if(!parsed||!Array.isArray(parsed.records))return new CompanionMemory();
  return new CompanionMemory(parsed.records.filter((row:Record<string,unknown>)=>typeof row.text==='string'&&typeof row.kind==='string'));
 }catch{return new CompanionMemory();}
}
function writeMemory(store:CompanionMemory){
 const records=store.records.map((row:Record<string,unknown>)=>({id:row.id,text:row.text,kind:row.kind,source:row.source}));
 window.localStorage.setItem(MEMORY_KEY, JSON.stringify({schema:'companion-memory-v1', records}));
}

/** Additive Brain Bay card. It does not call the existing model switcher. */
export default function CompanionLocalBay({variant='bay'}:{variant?:'bay'|'chat'}){
 const {session:activeSession,change:changeBeast,ready:beastReady}=useBeastSession();
 const activeSessionRef=useRef(activeSession);
 activeSessionRef.current=activeSession;
 const [linkToBeast,setLinkToBeast]=useState(false);
 const [shareWithLocalModel,setShareWithLocalModel]=useState(false);
 const linkRef=useRef(false),lastAccepted=useRef(0);
 linkRef.current=linkToBeast;
 const [card,setCard]=useState<Record<string,unknown>|null>(null);
 const [models,setModels]=useState<Model[]>([]);
 const [selected,setSelected]=useState('');
 const selectedBeastKey=beastIdentity(activeSession?.beast)||'';
 const lastBeastKey=useRef(selectedBeastKey);
 useEffect(()=>{
  if(lastBeastKey.current!==selectedBeastKey){
   lastBeastKey.current=selectedBeastKey;
   linkRef.current=false;
   setLinkToBeast(false);
   setShareWithLocalModel(false);
   lastAccepted.current=0;
  }
 },[selectedBeastKey]);
 const [cameraOn,setCameraOn]=useState(false);
 const [micOn,setMicOn]=useState(false);
 const [speechMode,setSpeechMode]=useState<'off'|'whisper.cpp'|'web-speech-fallback'>('off');
 const [visionModel,setVisionModel]=useState('moondream');
 const [notice,setNotice]=useState('Camera and microphone are off. Raw frames and audio are never stored.');
 const [simLabel,setSimLabel]=useState('SIMULATED · recorded IBM counts, not a live quantum device');
 const [draft,setDraft]=useState('');
 const [thread,setThread]=useState<Line[]>([]);
 const [askOllama,setAskOllama]=useState(false);
 const [optInImport,setOptInImport]=useState(false);
 const [memoryCount,setMemoryCount]=useState(0);
 const videoRef=useRef<HTMLVideoElement>(null);
 const canvasRef=useRef<HTMLCanvasElement>(null);
 const streamRef=useRef<MediaStream|null>(null);
 const audioRef=useRef<MediaStream|null>(null);
 const traitsRef=useRef({focus:0,calm:0,spark:0});
 const genomeRef=useRef<Record<string,unknown>|null>(null);
 const memoryRef=useRef<CompanionMemory>(new CompanionMemory());
 const cardRef=useRef<Record<string,unknown>|null>(null);
 const alive=useRef(true);
 const speechModeRef=useRef(speechMode);
 speechModeRef.current=speechMode;
 const visionModelRef=useRef(visionModel);
 visionModelRef.current=visionModel;
 const captureRef=useRef<() => Promise<void>>(async()=>{});

 const publish=useCallback((event:Record<string,unknown>)=>{
  const result=simulateLive(traitsRef.current, [event]);
  const animation=String(result.animation);
  setSimLabel(`SIMULATED · ${result.mood} · ${animation} · recorded run ${result.run_key} · not a live quantum device`);
  window.dispatchEvent(new CustomEvent('beastbox:ambient-action', {detail:animation}));
  if(typeof event.text==='string')memoryRef.current.add(event.text, 'vision', String(event.model||'vision'));
  else if(typeof event.transcript==='string'&&event.transcript)memoryRef.current.add(event.transcript, 'hearing', String(event.engine||'hearing'));
  else memoryRef.current.add(`loudness ${Number(event.loudness||0).toFixed(2)} onset ${Boolean(event.onset)}`, 'hearing', String(event.engine||'loudness-only'));
  writeMemory(memoryRef.current);
  setMemoryCount(memoryRef.current.records.length);
  if(linkRef.current){
   const id=beastIdentity(activeSessionRef.current?.beast);
   const now=Date.now();
   if(id&&now-lastAccepted.current>=8000){
    lastAccepted.current=now;
    changeBeast(draft=>{applySensedEvent(draft,event,{consented:true,expectedId:id,nowMs:now,place:'grove'});});
   }
  }
 },[changeBeast]);

 const stopAll=useCallback(()=>{
  streamRef.current?.getTracks().forEach(track=>track.stop());
  streamRef.current=null;
  audioRef.current?.getTracks().forEach(track=>track.stop());
  audioRef.current=null;
  if(videoRef.current)videoRef.current.srcObject=null;
  if(alive.current){setCameraOn(false);setMicOn(false);setSpeechMode('off');}
 },[]);

 useEffect(()=>{
  alive.current=true;
  const born=birth('serene');
  traitsRef.current=born.traits;
  genomeRef.current=born.genome;
  cardRef.current=born.card;
  setCard(born.card);
  memoryRef.current=readMemory();
  setMemoryCount(memoryRef.current.records.length);
  try{setSelected(window.localStorage.getItem(BRAIN_KEY)||'');}catch{setSelected('');}
  const stop=()=>{linkRef.current=false;setLinkToBeast(false);setShareWithLocalModel(false);stopAll();setNotice('Master privacy stop revoked sensor/model sharing and halted camera and microphone.');};
  window.addEventListener('beastbox:master-privacy-stop', stop);
  return()=>{alive.current=false;window.removeEventListener('beastbox:master-privacy-stop', stop);stopAll();};
 },[stopAll]);

 useEffect(()=>{
  let cancel=false;
  void fetch('/companion/catalog.json').then(response=>response.ok?response.json():null).then(data=>{
   if(cancel||!data||!Array.isArray(data.models))return;
   setModels(data.models.filter((row:Model)=>row&&row.selectable&&typeof row.alias==='string'));
  }).catch(()=>{});
  return()=>{cancel=true;};
 },[]);

 useEffect(()=>{
  if(!cameraOn)return;
  let cancel=false;
  let timer=0;
  void navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}, audio:false}).then(stream=>{
   if(cancel||!alive.current){stream.getTracks().forEach(track=>track.stop());return;}
   streamRef.current=stream;
   if(videoRef.current){videoRef.current.srcObject=stream;void videoRef.current.play();}
   timer=window.setInterval(()=>{void captureRef.current();}, 8000);
  }).catch(()=>{if(!cancel){setCameraOn(false);setNotice('Camera permission was not granted. Nothing was stored.');}});
  return()=>{
   cancel=true;
   window.clearInterval(timer);
   streamRef.current?.getTracks().forEach(track=>track.stop());
   streamRef.current=null;
  };
 },[cameraOn]);

 captureRef.current=captureFrame;
 async function captureFrame(){
  const video=videoRef.current, canvas=canvasRef.current;
  if(!video||!canvas||video.readyState<2)return;
  canvas.width=160;canvas.height=120;
  const context=canvas.getContext('2d');
  if(!context)return;
  context.drawImage(video, 0, 0, 160, 120);
  const blob=await new Promise<Blob|null>(resolve=>canvas.toBlob(resolve, 'image/jpeg', 0.6));
  context.clearRect(0, 0, canvas.width, canvas.height);
  if(!blob)return;
  const bytes=new Uint8Array(await blob.arrayBuffer());
  let binary='';
  for(const byte of bytes)binary+=String.fromCharCode(byte);
  const image=btoa(binary);
  try{
   if(!loopbackOnly(OLLAMA))throw new Error('vision endpoint must be loopback');
   const response=await fetch(OLLAMA, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
    model:visionModelRef.current, stream:false,
    messages:[{role:'user', content:'Describe the scene in one short sentence. Do not guess who anyone is.', images:[image]}],
   })});
   const data=await response.json();
   const text=data?.message?.content;
   if(!response.ok||typeof text!=='string'||!text.trim())throw new Error('vision model unreachable');
   publish(acceptVision({schema:'companion-vision-event-v1', text:text.slice(0, 400), model:visionModelRef.current}));
   setNotice('Scene text kept. The frame was discarded.');
  }catch{
   setNotice('Local vision model unreachable. Frame discarded. Nothing stored.');
  }
 }

 useEffect(()=>{
  if(!micOn)return;
  let audioTimer=0;
  let recorder:MediaRecorder|null=null;
  let recognition:SpeechRecognitionLike|null=null;
   const AudioCtx=window.AudioContext||(window as unknown as {webkitAudioContext?:typeof AudioContext}).webkitAudioContext;
  let context:AudioContext|null=null;
  let previous=0;
  let cancel=false;
  void navigator.mediaDevices.getUserMedia({audio:true, video:false}).then(stream=>{
   if(cancel||!alive.current){stream.getTracks().forEach(track=>track.stop());return;}
   audioRef.current=stream;
   if(!AudioCtx){setNotice('This browser has no Web Audio analyser. Microphone text was not started.');return;}
   context=new AudioCtx();
   const source=context.createMediaStreamSource(stream);
   const analyser=context.createAnalyser();
   analyser.fftSize=1024;
   source.connect(analyser);
   const samples=new Uint8Array(analyser.fftSize);
   audioTimer=window.setInterval(()=>{
    analyser.getByteTimeDomainData(samples);
    let sum=0;
    for(const value of samples){const x=(value-128)/128;sum+=x*x;}
    const loudness=Math.max(0, Math.min(1, Math.sqrt(sum/samples.length)*4));
    const onset=loudness>=0.08&&previous<0.08;
    previous=loudness;
    window.dispatchEvent(new CustomEvent('beastbox:local-sensor-level', {detail:{schema:'local-measurement-v1', kind:'microphone', level:loudness, active:true}}));
    if(speechModeRef.current==='off'&&(onset||loudness>=0.5)){
     publish(acceptHearing({schema:'companion-hearing-event-v1', transcript:'', loudness, onset, engine:'loudness-only'}));
    }
   }, 250);
   if(speechModeRef.current==='whisper.cpp'&&typeof MediaRecorder!=='undefined'){
    recorder=new MediaRecorder(stream);
    recorder.ondataavailable=(event)=>{
     const audioBlob=event.data;
     if(!audioBlob||!audioBlob.size||!loopbackOnly(WHISPER))return;
     const body=new FormData();
     body.append('file', audioBlob, 'clip.webm');
     void fetch(WHISPER, {method:'POST', body}).then(async response=>{
      const data=await response.json().catch(()=>null);
      const text=typeof data?.text==='string'?data.text:''
      if(!response.ok||!text.trim()){setNotice('whisper.cpp was not reachable. Audio discarded. Nothing stored.');return;}
      publish(acceptHearing({schema:'companion-hearing-event-v1', transcript:text.slice(0, 400), loudness:0, onset:false, engine:'whisper.cpp'}));
     }).catch(()=>setNotice('whisper.cpp was not reachable. Audio discarded. Nothing stored.'));
    };
    recorder.start(4000);
   }
   if(speechModeRef.current==='web-speech-fallback'){
    const speechWindow=window as unknown as {SpeechRecognition?:new()=>SpeechRecognitionLike;webkitSpeechRecognition?:new()=>SpeechRecognitionLike};
   const Ctor=speechWindow.SpeechRecognition||speechWindow.webkitSpeechRecognition;
    if(!Ctor){setNotice('Web Speech is unavailable in this browser. Loudness stays on-device.');return;}
    recognition=new Ctor();
    recognition.continuous=true;
    recognition.interimResults=false;
    recognition.onresult=(event)=>{
     const last=event.results[event.results.length-1];
     const text=last&&last[0]?String(last[0].transcript||''):'';
     if(!text.trim())return;
     publish(acceptHearing({schema:'companion-hearing-event-v1', transcript:text.slice(0, 400), loudness:0, onset:false, engine:'web-speech-fallback'}));
    };
    recognition.start();
    setNotice('Web Speech fallback: the browser vendor may process audio. This is not on-device whisper.cpp.');
   }
  }).catch(()=>{if(!cancel){setMicOn(false);setNotice('Microphone permission was not granted. Nothing was stored.');}});
  return()=>{
   cancel=true;
   window.clearInterval(audioTimer);
   if(recorder&&recorder.state!=='inactive')recorder.stop();
   try{recognition?.abort();}catch{/* already stopped */}
   void context?.close();
   audioRef.current?.getTracks().forEach(track=>track.stop());
   audioRef.current=null;
  };
 },[micOn, speechMode, publish]);

 async function sendChat(){
  const text=draft.trim();
  const current=cardRef.current;
  if(!text||!current)return;
  let answer=reply(current, text, memoryRef.current.records);
  let speaker='seeded personality layer';
  if(askOllama&&selected){
   const model=models.find(row=>row.alias===selected);
   try{
    if(!model||!loopbackOnly(OLLAMA))throw new Error('loopback required');
    const response=await fetch(OLLAMA, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
     model:model.ollama_name, stream:false,
     messages:[{role:'system', content:String(current.honesty||'')},{role:'user', content:
      [text,...modelSensedContext(activeSessionRef.current,{approved:linkToBeast&&shareWithLocalModel})].join('\n')}],
    })});
    const data=await response.json();
    if(response.ok&&typeof data?.message?.content==='string'&&data.message.content.trim()){
     answer=data.message.content.trim();
     speaker='ollama:'+model.ollama_name;
    }else speaker='fallback: seeded personality layer (Ollama unreachable)';
   }catch{speaker='fallback: seeded personality layer (Ollama unreachable)';}
  }
  try{
   memoryRef.current.add(text, 'chat', 'keeper');
   memoryRef.current.add(answer.slice(0, 500), 'chat', speaker);
   writeMemory(memoryRef.current);
   setMemoryCount(memoryRef.current.records.length);
  }catch(error){setNotice((error as Error).message);return;}
  setThread(old=>[...old, {role:'you' as const, text, speaker:'you'}, {role:'companion' as const, text:answer, speaker}].slice(-12));
  setDraft('');
 }

 function choose(alias:string){
  setSelected(alias);
  try{window.localStorage.setItem(BRAIN_KEY, alias);}catch{/* private mode */}
 }
 function downloadBeast(){
  const genome=genomeRef.current;
  if(!genome)return;
  const text=memoryRef.current.exportQbeast(genome);
  const blob=new Blob([text], {type:'application/json'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download=`${String(card?.name||'companion')}.qbeast`;link.click();
  URL.revokeObjectURL(url);
 }
 async function importChat(file:File){
  if(!optInImport){setNotice('Check the opt-in box before importing exported chat.');return;}
  const data=JSON.parse(await file.text());
  if(!data||data.opt_in!==true||!Array.isArray(data.messages))throw new Error('export must set opt_in true');
  for(const message of data.messages){
   if(message&&message.role==='user'&&typeof message.content==='string')memoryRef.current.add(message.content, 'chat', 'opt-in-export');
  }
  writeMemory(memoryRef.current);
  setMemoryCount(memoryRef.current.records.length);
  setNotice('Opt-in chat text was added to local companion memory.');
 }

 const name=String(card?.name||'companion');
 return <article className={styles.card+' data-card wide'} aria-label={variant==='bay'?'Companion local brain':'Companion chat'}>
  <div className="cloud-connect-heading"><div><h2>{variant==='bay'?'COMPANION BRAIN':'COMPANION CHAT'}</h2>
   <p className={styles.note}>{name} is a small local character seeded by recorded run {String(card?.quantum_run||'')}. Not conscious. Not omniscient. This card does not replace the COSMOS provider.</p></div></div>
  {variant==='bay'?<div className={styles.row}>{models.length?models.map(model=><button type="button" key={model.alias} className={'outline-action '+styles.choice} aria-pressed={selected===model.alias} onClick={()=>choose(model.alias)}>{model.creature||model.alias}{model.smoke?' · smoke LoRA':''}</button>):<p className={styles.note}>No catalog loaded yet. The seeded personality layer still answers.</p>}
   {selected&&models.find(model=>model.alias===selected)?.eval?<p className={styles.note}>Eval personality {models.find(model=>model.alias===selected)?.eval?.personality_consistency}, lore {models.find(model=>model.alias===selected)?.eval?.lore_recall}, false-claim refusals {models.find(model=>model.alias===selected)?.eval?.no_false_claims}, LoRA preference {models.find(model=>model.alias===selected)?.eval?.lora_preference}.</p>:null}
  </div>:selected?<p className={styles.note}>Selected companion brain: {selected}. Replies stay in this card.</p>:null}
  <p className={styles.note} role="status">{simLabel}</p>
  <p className={styles.note} role="status">{notice}</p>
  <p className={styles.note}>Text notes kept: {memoryCount}. Growing memory is local and exportable as .qbeast.</p>
  {variant==='bay'?<><div className={styles.row}>
    <button type="button" className="outline-action" aria-pressed={cameraOn} onClick={()=>setCameraOn(value=>!value)}>{cameraOn?'Stop camera':'Camera off · opt in'}</button>
    <label>Vision model <input aria-label="Local vision model" value={visionModel} onChange={event=>setVisionModel(event.target.value)}/></label>
    <button type="button" className="outline-action" aria-pressed={micOn} onClick={()=>setMicOn(value=>!value)}>{micOn?'Stop microphone':'Microphone off · opt in'}</button>
    <label>Speech <select aria-label="Speech engine" value={speechMode} onChange={event=>setSpeechMode(event.target.value as typeof speechMode)}>
     <option value="off">Loudness and onset only</option>
     <option value="whisper.cpp">whisper.cpp on 127.0.0.1:8080</option>
     <option value="web-speech-fallback">Web Speech fallback (may leave the device)</option>
    </select></label>
   </div>
   <div className={styles.row}>
    <label><input type="checkbox" checked={linkToBeast} disabled={!beastReady||!beastIdentity(activeSession?.beast)}
      onChange={event=>{setLinkToBeast(event.target.checked);if(!event.target.checked)setShareWithLocalModel(false);}}/>
      Link approved sensor summaries to my active Beast (local save; no XP or native stage changes)</label>
    <label><input type="checkbox" checked={shareWithLocalModel} disabled={!linkToBeast}
      onChange={event=>setShareWithLocalModel(event.target.checked)}/>
      Separately allow my already-selected LOCAL Ollama model to receive up to three saved sensor summaries</label>
   </div>
   <p className={styles.note} role="status">Linked Beast: {beastReady&&beastIdentity(activeSession?.beast)
     ?String(beastIdentity(activeSession.beast)).slice(0,24)+'… · '+(activeSession.beast.senseNotes?.length||0)+' approved text summaries'
     :'No active Beast chosen yet.'} Source descriptions are model interpretations, not proof of what the camera saw. No raw frames or audio enter the Beast save.</p>
   <p className={styles.note}>Verified HF references (not automatic paid inference):
    <a href="https://huggingface.co/phera-ra/QC67_cosmo" target="_blank" rel="noopener noreferrer"> QC67 local GGUF</a> ·
    <a href="https://huggingface.co/phera-ra/rawrphos-native-12k" target="_blank" rel="noopener noreferrer"> RAWRPHØS private 12K checkpoint</a>.
    Private model access requires its own authorized runtime; these links do not connect credentials.</p>
   <p className={styles.note}>Vision sends a frame to loopback Ollama ({visionModel}, for example moondream or llava) and keeps the sentence only. Hearing loudness is on-device. Web Speech is a labeled fallback, not whisper.cpp.</p>
   <video ref={videoRef} className={styles.hidden} muted playsInline aria-hidden="true"/>
   <canvas ref={canvasRef} className={styles.hidden} aria-hidden="true"/>
  </>:null}
  <div className={styles.row}>
   <input aria-label="Message your companion" value={draft} onChange={event=>setDraft(event.target.value)} placeholder={`Say something to ${name}`}/>
   <button type="button" className="outline-action" onClick={()=>void sendChat()}>Ask companion</button>
   <label><input type="checkbox" checked={askOllama} onChange={event=>setAskOllama(event.target.checked)}/> Ask loopback Ollama if it is running</label>
  </div>
  <pre className={styles.log}>{thread.map(line=>`${line.role==='you'?'You':name+' ('+line.speaker+')'}: ${line.text}`).join('\n')||'No companion turns yet.'}</pre>
  <div className={styles.row}>
   <button type="button" className="outline-action" onClick={downloadBeast}>Download .qbeast</button>
   <label><input type="checkbox" checked={optInImport} onChange={event=>setOptInImport(event.target.checked)}/> I opt in to importing this chat export</label>
   <input aria-label="Import opt-in chat export" type="file" accept="application/json,.json" onChange={event=>{const file=event.target.files?.[0];event.target.value='';if(file)void importChat(file).catch(error=>setNotice((error as Error).message));}}/>
  </div>
  {variant==='bay'?<p className={styles.note} data-meta-muse-link="true">Meta Muse (Meta&apos;s AI agent) can pair with your field beast through the Beast Box connector. <a href="/beast-cage/go#meta-muse">Pair with Meta Muse</a></p>:null}
 </article>;
}

type SpeechRecognitionLike={
 continuous:boolean;interimResults:boolean;start:()=>void;abort:()=>void;
 onresult:((event:{results:ArrayLike<ArrayLike<{transcript:string}>>})=>void)|null;
};
