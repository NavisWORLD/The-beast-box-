'use client';
import {useCallback,useEffect,useMemo,useRef,useState,type FormEvent} from 'react';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import {rememberExchange} from '../lib/companion/adventure.mjs';
import type {GameChatBridge} from './beast-chat-types';
import GameChatTools from './game-chat-tools';
import {gameBeastKey} from '../lib/companion/sol-game-talk.mjs';
import {useBeastAudio} from './use-beast-audio';
import {beastIdentity} from '../lib/companion/session.mjs';
import type {TalkRoute} from '../lib/companion/beast-talk.mjs';
import {
 DEFAULT_HF_MODEL,DEFAULT_OLLAMA_MODEL,DEFAULT_OLLAMA_URL,DEFAULT_ROUTE,MAX_MESSAGE,ROUTE_INFO,TALK_ROUTES,
 connectHelp,readTalkLog,talkPersona,talkToBeast,writeTalkLog,LOG_PREFIX,DRAFT_PREFIX,readTalkDraft,writeTalkDraft,readTalkRetention,TALK_RETENTION_KEY
} from '../lib/companion/beast-talk.mjs';
import styles from './beast-talk-panel.module.css';

export type TalkState='idle'|'thinking'|'listening'|'speaking'|'replied'|'offline';
type Route=TalkRoute;
type Turn={role:'you'|'beast';text:string;model?:string;route?:string;at?:number};
type Offline={error:string;help:string[];route:string};
type Prefs={route:Route;ollamaUrl:string;ollamaModel:string;hfModel:string};
type Status={routes?:Record<string,{configured:boolean|string}>;default?:string};
type SpeechResult={results:ArrayLike<{0:{transcript:string}}>};
type Recognition={lang:string;interimResults:boolean;onresult:((event:SpeechResult)=>void)|null;onerror:(()=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void};
type BrowserSpeech=Window&{SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition};

const PREFS_KEY='beastbox-talk-prefs-v1',HF_KEY='beastbox-talk-hf-key-v1';
const DEFAULT_PREFS:Prefs={route:DEFAULT_ROUTE as Route,ollamaUrl:DEFAULT_OLLAMA_URL,ollamaModel:DEFAULT_OLLAMA_MODEL,hfModel:DEFAULT_HF_MODEL};
const time=(at?:number)=>at?new Date(at).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}):'';

/**
 * The one Talk to Beast panel used by the Cage, Brain Bay and the talk page.
 * The visitor's own Beast frames every message; the chosen brain only voices it.
 * Replies appear only after a successful, verified request.
 */
type PanelProps={onState?:(state:TalkState)=>void;compact?:boolean;title?:string;surface?:'panel';gameBridge?:GameChatBridge|null};
export default function BeastTalkPanel(props:PanelProps){
 const {session}=useBeastSession(),{profile}=useCompanion();
 const persona=talkPersona({beast:session?.beast,cage:profile});
 useEffect(()=>{if(props.surface==='panel'||!props.onState)return;const report=(event:Event)=>props.onState?.((event as CustomEvent).detail.state);window.addEventListener('beastbox:talk-state',report);return()=>window.removeEventListener('beastbox:talk-state',report);},[props.surface,props.onState]);
 if(props.surface==='panel')return <BeastTalkContent {...props}/>;
 return <button type="button" className={styles.openChat} onClick={()=>window.dispatchEvent(new Event('beastbox:open-chat'))}>{props.title||`Talk to ${persona.name}`}</button>;
}
function BeastTalkContent({onState,compact=false,title,gameBridge}:PanelProps){
 const {ready,session,change}=useBeastSession();
 const {profile}=useCompanion();
 const persona=useMemo(()=>talkPersona({beast:session?.beast||null,cage:profile}),[session?.beast,profile]);
 const {audio,state:audioState}=useBeastAudio();
 const [retention,setRetention]=useState<'device'|'session'>('device'),[shareHistory,setShareHistory]=useState(false),[includeGame,setIncludeGame]=useState(false);
 const storage=useRef<Storage|null>(null);
 const [prefs,setPrefs]=useState<Prefs>(DEFAULT_PREFS);
 const [hfKey,setHfKey]=useState(''),[spend,setSpend]=useState(false);
 const [status,setStatus]=useState<Status|null>(null);
 const [log,setLog]=useState<Turn[]>([]);
 const [text,setText]=useState(''),[busy,setBusy]=useState(false),[offline,setOffline]=useState<Offline|null>(null);
 const [verifiedAt,setVerifiedAt]=useState<number|null>(null),[listening,setListening]=useState(false),[speaking,setSpeaking]=useState(false);
 const [showBrains,setShowBrains]=useState(false);
 const pending=useRef<AbortController|null>(null),speech=useRef<Recognition|null>(null),logEnd=useRef<HTMLDivElement>(null);
 const personaKey=useRef(persona.key);personaKey.current=persona.key;

 useEffect(()=>{
  setRetention(readTalkRetention(localStorage));
  try{const raw=localStorage.getItem(PREFS_KEY);if(raw){const saved=JSON.parse(raw);setPrefs(p=>({...p,...saved,route:TALK_ROUTES.includes(saved?.route)?saved.route:p.route}));}}catch{/* defaults */}
  try{setHfKey(sessionStorage.getItem(HF_KEY)||'');}catch{/* private mode */}
  const controller=new AbortController();
  fetch('/api/talk',{cache:'no-store',signal:controller.signal}).then(r=>r.ok?r.json():null).then(setStatus).catch(()=>setStatus({}));
  return()=>controller.abort();
 },[]);
 // Each Beast keeps its own conversation. Switching Beasts never mixes logs.
 useEffect(()=>{pending.current?.abort();pending.current=null;setBusy(false);speech.current?.stop();setListening(false);window.speechSynthesis?.cancel();setSpeaking(false);storage.current=retention==='device'?localStorage:sessionStorage;setLog(readTalkLog(storage.current,persona.key));setText(readTalkDraft(storage.current,persona.key));setOffline(null);setVerifiedAt(null);setShareHistory(false);setIncludeGame(false);},[persona.key,retention]);
 function editText(value:string){const draft=value.slice(0,MAX_MESSAGE);setText(draft);writeTalkDraft(storage.current,persona.key,draft);}
 useEffect(()=>()=>{pending.current?.abort();speech.current?.stop();if(typeof window!=='undefined')window.speechSynthesis?.cancel();},[]);
 useEffect(()=>{logEnd.current?.scrollIntoView({block:'nearest'});},[log.length]);
 const state:TalkState=busy?'thinking':listening?'listening':speaking?'speaking':offline?'offline':verifiedAt?'replied':'idle';
 useEffect(()=>{onState?.(state);},[state,onState]);

 useEffect(()=>{const draft=(event:Event)=>{const value=(event as CustomEvent).detail?.draft;if(typeof value==='string')editText(value);};window.addEventListener('beastbox:open-chat',draft);return()=>window.removeEventListener('beastbox:open-chat',draft);},[persona.key]);
 const savePrefs=useCallback((next:Partial<Prefs>)=>{
  pending.current?.abort();pending.current=null;setBusy(false);
  // React state updaters must be pure: writing localStorage inside the updater
  // can be replayed or deferred by concurrent rendering, making the controlled
  // provider radio snap back despite a user click.
  const merged={...prefs,...next};
  setPrefs(merged);
  try{localStorage.setItem(PREFS_KEY,JSON.stringify(merged));}catch{/* optional device preference */}
  setOffline(null);setVerifiedAt(null);
 },[prefs]);
 function rememberKey(value:string){setHfKey(value);try{if(value)sessionStorage.setItem(HF_KEY,value);else sessionStorage.removeItem(HF_KEY);}catch{/* optional */}}

 const route=prefs.route,info=ROUTE_INFO[route];
 const guestConfigured=status?.routes?.['guest-rawrphos']?.configured;
 const modelName=route==='local-ollama'?prefs.ollamaModel:route==='hf-byok'?prefs.hfModel:info.model;
 const connection=busy?{tone:'busy',text:'Asking the model…'}
  :offline?{tone:'off',text:'Model offline · '+offline.error}
  :verifiedAt?{tone:'on',text:'Connected · real reply verified '+time(verifiedAt)}
  :route==='guest-rawrphos'&&guestConfigured===false?{tone:'off',text:'Model offline · the free guest host is not configured on this site'}
  :route==='guest-rawrphos'&&guestConfigured===true?{tone:'ready',text:'Ready · free host configured (each reply is verified)'}
  :route==='guest-rawrphos'?{tone:'ready',text:'Checking the free host…'}
  :route==='hf-byok'&&!hfKey?{tone:'off',text:'Needs your Hugging Face token'}
  :{tone:'ready',text:'Ready to try · runs on your side'};

 async function send(event:FormEvent<HTMLFormElement>){
  event.preventDefault();
  const saying=text.trim();
  if(busy||!ready||!saying||saying.length>MAX_MESSAGE)return;
  speech.current?.stop();window.speechSynthesis?.cancel();setSpeaking(false);
  const controller=new AbortController();pending.current=controller;
  // A model on the visitor's own CPU can take minutes on a slow or busy computer; Cancel is always shown.
  const timeout=window.setTimeout(()=>controller.abort(),route==='local-ollama'?180000:65000);
  const forKey=persona.key,beastId=beastIdentity(session?.beast||null);
  setBusy(true);setOffline(null);
  try{
   const observation=includeGame&&gameBridge?.key===gameBeastKey(session)?await gameBridge.observeGame?.():null;
   if(controller.signal.aborted||personaKey.current!==forKey)return;
   const result=await talkToBeast({route,persona,history:log,text:saying,shareHistory,observation,signal:controller.signal,
    ollama:{url:prefs.ollamaUrl,model:prefs.ollamaModel},hf:{key:hfKey,model:prefs.hfModel,spendConfirmed:spend}});
   if(pending.current!==controller||personaKey.current!==forKey)return;
   if(!result.ok){setOffline({error:result.error,help:result.help,route:result.route});return;}
   const next=[...log,{role:'you' as const,text:saying,at:Date.now()},{role:'beast' as const,text:result.reply,model:result.model,route:result.route,at:result.at}];
   setLog(next);writeTalkLog(storage.current,forKey,next);setVerifiedAt(result.at);editText('');
   // Same Beast, same growth: a verified exchange adds to the saved Beast's chat and bond.
   if(retention==='device'&&beastId&&session?.beast)void change(draft=>{if(beastIdentity(draft.beast)===beastId)rememberExchange(draft,saying,result.reply);});
  }finally{
   window.clearTimeout(timeout);
   if(pending.current===controller){pending.current=null;setBusy(false);}
  }
 }
 function cancel(){pending.current?.abort();}
 function clearLog(){setLog([]);writeTalkLog(storage.current,persona.key,[]);}
 function listen(){
  if(listening){speech.current?.stop();speech.current=null;setListening(false);return;}
  const ctor=(window as BrowserSpeech).SpeechRecognition||(window as BrowserSpeech).webkitSpeechRecognition;
  if(!ctor){setOffline({error:'Voice typing is not supported in this browser. You can type instead.',help:[],route});return;}
  try{
   const instance=new ctor();instance.lang='en-US';instance.interimResults=false;
   instance.onresult=e=>{const said=e.results[0]?.[0]?.transcript||'';editText((text+' '+said).trim());setListening(false);};
   instance.onerror=()=>{setListening(false);};
   instance.onend=()=>{setListening(false);speech.current=null;};
   instance.start();speech.current=instance;setListening(true);
  }catch{setListening(false);}
 }
 const lastReply=[...log].reverse().find(turn=>turn.role==='beast');
 function speak(){
  if(speaking){window.speechSynthesis?.cancel();setSpeaking(false);return;}
  if(!lastReply||!('speechSynthesis' in window)){setOffline({error:'Speech playback is unavailable in this browser.',help:[],route});return;}
  if(audioState.sparkMuted){setOffline({error:'Unmute sound in Settings to hear a reply.',help:[],route});return;}audio.unlock();
  const utterance=new SpeechSynthesisUtterance(lastReply.text.slice(0,600));utterance.lang='en-US';utterance.pitch=1.15;utterance.volume=audioState.volume;
  utterance.onend=()=>setSpeaking(false);utterance.onerror=()=>setSpeaking(false);
  try{window.speechSynthesis.cancel();window.speechSynthesis.speak(utterance);setSpeaking(true);}catch{setSpeaking(false);}
 }

 return <section className={styles.panel} data-compact={compact||undefined} data-overlay data-talk-state={state} data-talk-route={route} aria-label={`Talk to ${persona.name}`}>
  <div className={styles.body}>
  <header className={styles.who}>
   <div className={styles.avatar} aria-hidden="true">{persona.source==='zeref'?'🌙':persona.source==='spark'?'🐣':'✦'}</div>
   <div className={styles.whoText}>
    <h2>{ready?title||`Talk to ${persona.name}`:'Finding your Beast…'}</h2>
    <p><strong>{persona.name}</strong> · {persona.kind}. {persona.traits.join(', ')}.</p>
    <small>{persona.source==='zeref'?'Showing Zeref, the site Beast. Meet your own Beast in My Beast and it will talk here instead.':persona.source==='spark'?'Your saved Beast. Its name, personality and memories stay the same whichever brain answers.':'Your Beast Cage creature. Its personality stays the same whichever brain answers.'}</small>
   </div>
  </header>

  <div className={styles.brainBar} data-tone={connection.tone}>
   <span className={styles.light} aria-hidden="true"/>
   <div className={styles.brainText} role="status" aria-live="polite">
    <strong>Brain: {info.label} · <code>{modelName}</code></strong>
    <span>{connection.text}</span>
   </div>
   <button type="button" className={styles.ghost} aria-expanded={showBrains} onClick={()=>setShowBrains(v=>!v)}>{showBrains?'Done':'Change brain'}</button>
  </div>

  {showBrains?<fieldset className={styles.brains}>
   <legend>Choose which model gives {persona.name} a voice</legend>
   {TALK_ROUTES.map(key=><label key={key} className={styles.brainChoice} data-selected={route===key||undefined}>
    <input type="radio" name="talk-brain" value={key} checked={route===key} onChange={()=>savePrefs({route:key as Route})}/>
    <span><strong>{ROUTE_INFO[key].label}</strong><small>{ROUTE_INFO[key].detail}</small></span>
   </label>)}
   {route==='local-ollama'?<div className={styles.fields}>
    <label>Ollama address<input value={prefs.ollamaUrl} onChange={e=>savePrefs({ollamaUrl:e.target.value.trim()})} placeholder={DEFAULT_OLLAMA_URL} inputMode="url" autoComplete="off" spellCheck={false}/></label>
    <label>Model tag<input value={prefs.ollamaModel} onChange={e=>savePrefs({ollamaModel:e.target.value.trim()})} placeholder="companion-glacecoil or qwen2.5:0.5b" autoComplete="off" spellCheck={false}/></label>
   </div>:null}
   {route==='hf-byok'?<div className={styles.fields}>
    <label>Your Hugging Face token<input type="password" value={hfKey} onChange={e=>rememberKey(e.target.value.trim())} placeholder="hf_…" autoComplete="off" spellCheck={false}/></label>
    <label>Model ID<input value={prefs.hfModel} onChange={e=>savePrefs({hfModel:e.target.value.trim()})} placeholder={DEFAULT_HF_MODEL} autoComplete="off" spellCheck={false}/></label>
    <label className={styles.check}><input type="checkbox" checked={spend} onChange={e=>setSpend(e.target.checked)}/>Any charges go to my own Hugging Face account.</label>
    <small>The token stays in this browser tab only and is sent through the existing Hugging Face proxy only when you send a confirmed request.</small>
   </div>:null}
   <ul className={styles.helpList}>{connectHelp(route).map(line=><li key={line}>{line}</li>)}</ul>
  </fieldset>:null}

  <div className={styles.log} aria-label={`Conversation with ${persona.name}`} aria-live="polite">
   {log.length===0?<p className={styles.empty}>Say hi to {persona.name}. Replies come from the brain shown above, never from a script.</p>:
    log.map((turn,i)=><div key={i} className={turn.role==='you'?styles.you:styles.beast}>
     <span className={styles.speaker}>{turn.role==='you'?'You':persona.name}{turn.role==='beast'&&turn.model?<em> · via {turn.model}</em>:null}</span>
     <p>{turn.text}</p>
    </div>)}
   {busy?<div className={styles.beast}><span className={styles.speaker}>{persona.name}</span><p className={styles.thinking}>thinking<span>.</span><span>.</span><span>.</span></p></div>:null}
   <div ref={logEnd}/>
  </div>

  {offline?<div className={styles.offline} role="alert">
   <strong>Model offline: no reply was received</strong>
   <p>{offline.error}</p>
   {offline.help.length?<><span>How to connect a brain:</span><ul>{offline.help.map(line=><li key={line}>{line}</li>)}</ul></>:null}
   {!showBrains&&offline.help.length?<button type="button" className={styles.ghost} onClick={()=>setShowBrains(true)}>Pick another brain</button>:null}
  </div>:null}

  <details className={styles.options}><summary>Conversation & observation settings</summary>
   <label>Keep this conversation <select value={retention} onChange={e=>{const next=e.target.value==='session'?'session':'device';const target=next==='session'?sessionStorage:localStorage;writeTalkLog(target,persona.key,log);writeTalkDraft(target,persona.key,text);if(next==='session'){localStorage.removeItem(LOG_PREFIX+persona.key);localStorage.removeItem(DRAFT_PREFIX+persona.key);}setRetention(next);try{localStorage.setItem(TALK_RETENTION_KEY,next);}catch{/* optional */}}}><option value="device">On this device</option><option value="session">In this tab only</option></select></label>
   <label><input type="checkbox" checked={shareHistory} onChange={e=>setShareHistory(e.target.checked)}/> Share recent conversation with the selected provider</label>
   {gameBridge&&gameBridge.key===gameBeastKey(session)?<><label><input type="checkbox" checked={includeGame} onChange={e=>setIncludeGame(e.target.checked)}/> Include measured game screen brightness, contrast and color</label><GameChatTools bridge={gameBridge} busy={busy} route={route} optedIn={includeGame}/></>:<p>Observation mode: creature identity and your message. No live game vision bridge is connected.</p>}
   <p>Voice typing starts only on your tap and may use your browser’s speech service. Speech playback follows your sound settings.</p>
  </details>
  </div>
  <form data-companion-chat-form className={styles.form} onSubmit={send}>
   <label htmlFor="beast-talk-input" className={styles.srOnly}>Message to {persona.name}</label>
   <textarea id="beast-talk-input" value={text} onChange={e=>editText(e.target.value)} rows={compact?2:3} maxLength={MAX_MESSAGE} disabled={busy}
    placeholder={`Say something to ${persona.name}…`} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form?.requestSubmit();}}}/>
   <div className={styles.actions}>
    <button type="button" className={styles.ghost} onClick={listen} aria-pressed={listening} disabled={busy}>{listening?'Stop':'🎙 Voice'}</button>
    {lastReply?<button type="button" className={styles.ghost} onClick={speak} aria-pressed={speaking}>{speaking?'Stop voice':'🔊 Hear reply'}</button>:null}
    {log.length?<button type="button" className={styles.ghost} onClick={clearLog} disabled={busy}>Clear</button>:null}
    {busy?<button type="button" className={styles.ghost} onClick={cancel}>Cancel</button>:null}
    <button type="submit" className={styles.send} disabled={busy||!ready||!text.trim()}>{busy?'Waiting…':'Send'}</button>
   </div>
   <small className={styles.count}>{text.length}/{MAX_MESSAGE} · {retention==='device'?'Saved on this device':'Kept in this tab'} · {persona.name}.</small>
  </form>
 </section>;
}
