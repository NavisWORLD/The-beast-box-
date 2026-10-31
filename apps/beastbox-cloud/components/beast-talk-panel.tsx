'use client';
import Details from './details-toggle';
import {useCallback,useEffect,useMemo,useRef,useState,type FormEvent} from 'react';
import {useBeastSession} from './beast-session';
import {useCompanion} from './companion-provider';
import {rememberExchange} from '../lib/companion/adventure.mjs';
import type {GameChatBridge} from './beast-chat-types';
import GameChatTools from './game-chat-tools';
import {gameBeastKey,knownGameContext} from '../lib/companion/sol-game-talk.mjs';
import {useBeastAudio} from './use-beast-audio';
import {loadPrivateChat,createPrivateChatQueue,mergePrivateChat} from '../lib/companion/private-chat.mjs';
import type {PrivateChatBinding,PrivateChatQueueState} from '../lib/companion/private-chat.mjs';
import {getOrCreateVisitorId,freshGrowth,readVisitorGrowth,writeVisitorGrowth,advanceVisitorGrowth,growthModelContext} from '../lib/companion/visitor-growth.mjs';
import type {VisitorGrowth} from '../lib/companion/visitor-growth.mjs';
import {beastIdentity} from '../lib/companion/session.mjs';
import type {TalkRoute} from '../lib/companion/beast-talk.mjs';
import {
 DEFAULT_HF_MODEL,DEFAULT_OLLAMA_MODEL,DEFAULT_OLLAMA_URL,DEFAULT_ROUTE,MAX_MESSAGE,ROUTE_INFO,TALK_ROUTES,
 connectHelp,readInfo,readTalkLog,talkPersona,talkToBeast,writeTalkLog,LOG_PREFIX,DRAFT_PREFIX,readTalkDraft,writeTalkDraft,readTalkRetention,TALK_RETENTION_KEY
} from '../lib/companion/beast-talk.mjs';
import {speakSeeded,speakableText,voiceProfile,ZEREF_VOICE_SEED,REACH_OUT_LABEL} from '../lib/companion/seeded-voice.mjs';
import {isTeacherRoute,makePair,rememberPair,readContribute,writeContribute,contributionBody,readPairs} from '../lib/companion/teacher-distill.mjs';
import styles from './beast-talk-panel.module.css';
import {useTalkPersona} from './use-talk-target';
import {RAWRPHOS_PUBLIC_PIN} from '../lib/companion/brain.mjs';
import ZerefLibraryPanel,{ReadsBox,RecordedNotes,type LibraryState} from './zeref-library-panel';
import {libraryContext} from '../lib/library/context.mjs';
import {BANK_URL,BANK_CONSENT_KEY,BANK_LABEL,buildBank,loadShardsFor,searchBank,bankContext,provenanceLine,isStillLearningReply,stillLearningNote} from '../lib/knowledge/bank.mjs';

export type TalkState='idle'|'thinking'|'listening'|'speaking'|'replied'|'offline';
type Route=TalkRoute;
type TeacherHint={text:string;label:string;model?:string;route:string};
type BankUsed={id:string;title:string;excerpt:string;source:string;license:string;version:number};
type Turn=TurnBase&{bank?:BankUsed[];stillLearning?:boolean};
type TurnBase={role:'you'|'beast'|'system';text:string;model?:string;route?:string;at?:number;id?:string;cloudImported?:boolean;verified?:boolean;teacher?:TeacherHint;beastMissing?:string;coachedBy?:string;reachOut?:string;read?:{readChars:number;totalChars:number;extracted:boolean;note:string};libraryUsed?:{title:string;loc:string}[]};
type ChatTurn=Turn&{role:'you'|'beast'};
/** System notices (model offline) are shown in the log but never sent to a model or saved as chat. */
const chatOnly=(l:Turn[]):ChatTurn[]=>l.filter((t):t is ChatTurn=>t.role!=='system');
type Offline={error:string;help:string[];route:string};
type Prefs={route:Route;ollamaUrl:string;ollamaModel:string;hfModel:string};
type Status={routes?:Record<string,{configured:boolean|string}>;default?:string};
type SpeechResult={results:ArrayLike<{0:{transcript:string}}>};
type Recognition={lang:string;interimResults:boolean;onresult:((event:SpeechResult)=>void)|null;onerror:(()=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void};
type BrowserSpeech=Window&{SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition};

const PREFS_KEY='beastbox-talk-prefs-v1',HF_KEY='beastbox-talk-hf-key-v1',GROWTH_CONSENT_KEY='beastbox-growth-context-consent-v1';
const DEFAULT_PREFS:Prefs={route:DEFAULT_ROUTE as Route,ollamaUrl:DEFAULT_OLLAMA_URL,ollamaModel:DEFAULT_OLLAMA_MODEL,hfModel:DEFAULT_HF_MODEL};
const time=(at?:number)=>at?new Date(at).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}):'';

/**
 * The one Talk to Beast panel used by the Cage, Brain Bay and the talk page.
 * The visitor's own Beast frames every message; the chosen brain only voices it.
 * Replies appear only after a successful, verified request.
 */
type PanelProps={onState?:(state:TalkState)=>void;compact?:boolean;title?:string;surface?:'panel';gameBridge?:GameChatBridge|null};
const TEACHER_LABEL:Record<string,string>={'shared-ollama':'Ollama','guest-rawrphos':'Beast Box free host','connected-brain-bay':'Brain Bay','local-ollama':'My local Ollama','hf-byok':'My Hugging Face key'};
export default function BeastTalkPanel(props:PanelProps){
 const {session}=useBeastSession(),{profile}=useCompanion();
 const {persona}=useTalkPersona(session?.beast,profile);
 useEffect(()=>{if(props.surface==='panel'||!props.onState)return;const report=(event:Event)=>props.onState?.((event as CustomEvent).detail.state);window.addEventListener('beastbox:talk-state',report);return()=>window.removeEventListener('beastbox:talk-state',report);},[props.surface,props.onState]);
 if(props.surface==='panel')return <BeastTalkContent {...props}/>;
 return <button type="button" className={styles.openChat} aria-controls="beast-chat-overlay" onClick={event=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{opener:event.currentTarget}}))}>{props.title||`Talk to ${persona.name}`}</button>;
}
function BeastTalkContent({onState,compact=false,title,gameBridge}:PanelProps){
 const {ready,session,change}=useBeastSession();
 const {profile}=useCompanion();
 const {persona,companion,target,choose}=useTalkPersona(session?.beast||null,profile);
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
 const [lib,setLib]=useState<LibraryState>({owner:false,ready:false,docCount:0}),[notes,setNotes]=useState<{id:string;items:{title:string;loc:string;excerpt:string;sha256?:string}[]}|null>(null),[libNote,setLibNote]=useState('');
 // Knowledge bank: opt-in, default OFF. Public open-license passages, looked up by keyword in this browser; nothing leaves the device except the matching words sent with the message.
 const [bankOn,setBankOn]=useState(false),bankRef=useRef<ReturnType<typeof buildBank>|null>(null);
 useEffect(()=>{try{setBankOn(localStorage.getItem(BANK_CONSENT_KEY)==='on');}catch{/* off */}},[]);
 function toggleBank(on:boolean){setBankOn(on);try{localStorage.setItem(BANK_CONSENT_KEY,on?'on':'off');}catch{/* optional */}}
 const [contribute,setContribute]=useState(false),[pairCount,setPairCount]=useState(0),[contribStatus,setContribStatus]=useState('');
 const [cloudStatus,setCloudStatus]=useState('Private cloud is optional. Restore your own conversation before saving.'),[cloudOwner,setCloudOwner]=useState(''),[cloudSync,setCloudSync]=useState(false),[cloudRestoring,setCloudRestoring]=useState(false);
 const [queueState,setQueueState]=useState<PrivateChatQueueState>({busy:false,pending:0,paused:false,error:null,lastSavedEvent:null});
 const privateQueue=useRef<ReturnType<typeof createPrivateChatQueue>|null>(null),privateBinding=useRef<PrivateChatBinding|null>(null),restoreAbort=useRef<AbortController|null>(null);
 const cloudBusy=cloudRestoring||queueState.busy;
 const selectionKey=JSON.stringify([persona.key,beastIdentity(session?.beast||null),session?.beast?.genome?.seed,session?.beast?.seed,session?.beast?.qbeast?.profile?.seed]);
 const privateSelection=useRef(selectionKey);privateSelection.current=selectionKey;
 const [prefsLoaded,setPrefsLoaded]=useState(false),[loadedConversation,setLoadedConversation]=useState('');
 const conversationKey=JSON.stringify([selectionKey,retention]),conversationReady=ready&&prefsLoaded&&loadedConversation===conversationKey;
 useEffect(()=>{const queue=createPrivateChatQueue({onChange:setQueueState});privateQueue.current=queue;return()=>{queue.dispose();privateQueue.current=null;restoreAbort.current?.abort();};},[]);
 const [cloudConsented,setCloudConsented]=useState(false);
 const [visitorId,setVisitorId]=useState<string|null>(null),[growth,setGrowth]=useState<VisitorGrowth|null>(null),[shareGrowth,setShareGrowth]=useState(false);
 const pending=useRef<AbortController|null>(null),speech=useRef<Recognition|null>(null),logEnd=useRef<HTMLDivElement>(null);
 const personaKey=useRef(persona.key);personaKey.current=persona.key;

 useEffect(()=>{
  setRetention(readTalkRetention(localStorage));
  try{const raw=localStorage.getItem(PREFS_KEY);if(raw){const saved=JSON.parse(raw);setPrefs(p=>({...p,...saved,route:TALK_ROUTES.includes(saved?.route)?saved.route:p.route}));}}catch{/* defaults */}
  try{setHfKey(sessionStorage.getItem(HF_KEY)||'');}catch{/* private mode */}
  try{setShareGrowth(localStorage.getItem(GROWTH_CONSENT_KEY)==='yes');}catch{/* private by default */}
  setContribute(readContribute(localStorage));setPairCount(readPairs(localStorage).length);
  setPrefsLoaded(true);
  const controller=new AbortController();
  fetch('/api/talk',{cache:'no-store',signal:controller.signal}).then(r=>r.ok?r.json():null).then(setStatus).catch(()=>setStatus({}));
  return()=>controller.abort();
 },[]);
 // Each Beast keeps its own conversation. Switching Beasts never mixes logs.
 useEffect(()=>{pending.current?.abort();pending.current=null;setBusy(false);speech.current?.stop();setListening(false);window.speechSynthesis?.cancel();setSpeaking(false);storage.current=retention==='device'?localStorage:sessionStorage;setLog(readTalkLog(storage.current,persona.key));setText(readTalkDraft(storage.current,persona.key));setOffline(null);setVerifiedAt(null);setShareHistory(false);setIncludeGame(false);const id=getOrCreateVisitorId(storage.current);setVisitorId(id);setGrowth(id?readVisitorGrowth(storage.current,id,persona.key):null);setLoadedConversation(conversationKey);},[selectionKey,retention]);
 function editText(value:string){const draft=value.slice(0,MAX_MESSAGE);setText(draft);writeTalkDraft(storage.current,persona.key,draft);}
 useEffect(()=>{restoreAbort.current?.abort();restoreAbort.current=null;privateBinding.current=null;privateQueue.current?.select(null);setCloudRestoring(false);setCloudOwner('');setCloudConsented(false);setCloudSync(false);setCloudStatus('Private cloud is optional. Restore your own conversation before saving.');},[selectionKey]);
 useEffect(()=>{const binding=privateBinding.current;privateQueue.current?.select(binding?{...binding,enabled:cloudSync,consented:cloudConsented}:null);},[cloudSync,cloudConsented,cloudOwner,selectionKey]);
 // Zeref's own unprompted messages (RAWRPHOS or his diary line) appear in chat, labeled.
 useEffect(()=>{const on=(e:Event)=>{const d=(e as CustomEvent).detail||{};if(!d.text||persona.name!=='Zeref')return;
  setLog(prev=>[...prev,{role:'beast',text:String(d.text),at:d.at,id:'reach-'+d.at,reachOut:String(d.by||'RAWRPHØS')}]);};
  window.addEventListener('zeref:reach-out',on);return()=>window.removeEventListener('zeref:reach-out',on);},[persona.name]);
 useEffect(()=>{if(queueState.error)setCloudStatus(queueState.error+' The completed reply remains in your selected local storage. Retry explicitly.');else if(queueState.lastSavedEvent)setCloudStatus('Both turns were saved in one private cloud revision. Model weights and native saves are unchanged.');},[queueState.error,queueState.lastSavedEvent]);
 async function restorePrivate(){
  if(busy||cloudBusy||!conversationReady||!session?.beast)return;
  const captured=selectionKey,key=persona.key,target=storage.current,beast=structuredClone(session.beast),owner=cloudOwner||undefined,controller=new AbortController();
  restoreAbort.current?.abort();restoreAbort.current=controller;setCloudRestoring(true);setShareHistory(false);setCloudSync(false);privateQueue.current?.select(null);
  try{const result=await loadPrivateChat(beast,{signal:controller.signal,expectedOwner:owner});if(controller.signal.aborted||privateSelection.current!==captured||restoreAbort.current!==controller)return;
   const restored=mergePrivateChat(readTalkLog(target,key),result.rows);setLog(restored);writeTalkLog(target,key,restored);setShareHistory(false);setCloudOwner(result.owner);setCloudConsented(result.consented);setVerifiedAt(null);
   privateBinding.current={key,owner:result.owner,beast,enabled:false,consented:result.consented};privateQueue.current?.select(privateBinding.current);
   setCloudStatus(result.consented?'Restored this Beast’s private conversation. Imported text is not live inference. You can enable private saving below.':'Restored this Beast’s private history. Enable conversation persistence for it in Settings before saving new exchanges.');
  }catch(error){if(!controller.signal.aborted&&privateSelection.current===captured)setCloudStatus(error instanceof Error?error.message:'Private cloud unavailable.');}
  finally{if(restoreAbort.current===controller){restoreAbort.current=null;setCloudRestoring(false);}}
 }
 function togglePrivateSync(value:boolean){setCloudSync(value);const binding=privateBinding.current;privateQueue.current?.select(binding?{...binding,enabled:value,consented:cloudConsented}:null);}
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
 function toggleGrowth(value:boolean){setShareGrowth(value);try{localStorage.setItem(GROWTH_CONSENT_KEY,value?'yes':'no');}catch{/* optional */}}
 function resetGrowth(){if(!visitorId||busy)return;const fresh=freshGrowth(visitorId,persona.key);writeVisitorGrowth(storage.current,fresh);setGrowth(fresh);}
 function rememberKey(value:string){setHfKey(value);try{if(value)sessionStorage.setItem(HF_KEY,value);else sessionStorage.removeItem(HF_KEY);}catch{/* optional */}}

 const route=prefs.route,info=ROUTE_INFO[route];
 const guestConfigured=status?.routes?.['guest-rawrphos']?.configured;
 const modelName=route==='local-ollama'?prefs.ollamaModel:route==='hf-byok'?prefs.hfModel:info.model;
 const connection=busy?{tone:'busy',text:'Asking the model…'}
  :offline?{tone:'off',text:'Model offline · '+offline.error}
  :verifiedAt?{tone:'on',text:`${persona.name}'s reply · came from the real model `+time(verifiedAt)}
  :route==='guest-rawrphos'&&guestConfigured===false?{tone:'off',text:'Model offline · the free guest host is not configured on this site'}
  :route==='guest-rawrphos'&&guestConfigured===true?{tone:'ready',text:'Ready · free host configured (every reply is checked to come from the real model)'}
  :route==='guest-rawrphos'?{tone:'ready',text:'Checking the free host…'}
  :route==='hf-byok'&&!hfKey?{tone:'off',text:'Needs your Hugging Face token'}
  :{tone:'ready',text:'Ready to try · runs on your side'};

 async function send(event:FormEvent<HTMLFormElement>){
  event.preventDefault();
  const saying=text.trim();
  if((pending.current&&!pending.current.signal.aborted)||cloudRestoring||!conversationReady||!saying||saying.length>MAX_MESSAGE)return;
  speech.current?.stop();window.speechSynthesis?.cancel();setSpeaking(false);
  const controller=new AbortController();pending.current=controller;
  // A model on the visitor's own CPU can take minutes on a slow or busy computer; Cancel is always shown.
  const timeout=window.setTimeout(()=>controller.abort(),route==='local-ollama'?180000:65000);
  const forKey=persona.key,forSelection=selectionKey,beastId=beastIdentity(session?.beast||null),boundForCloud=cloudSync&&cloudConsented&&privateBinding.current?{...privateBinding.current,beast:structuredClone(privateBinding.current.beast),enabled:true,consented:true}:null;
  setBusy(true);setOffline(null);
  try{
   const observation=includeGame&&gameBridge?.key===gameBeastKey(session)?await gameBridge.observeGame?.():null;
   if(controller.signal.aborted||personaKey.current!==forKey||privateSelection.current!==forSelection)return;
   // Zeref's own library (owner only): deterministic keyword lookup, passages copied verbatim. Used by RAWRPHØS only, never sent to teachers.
   let used:{docId?:string;title:string;loc:string;excerpt:string;sha256?:string}[]=[],libraryText='';setLibNote('');
   if(persona.source==='zeref'&&lib.owner&&lib.ready){
    try{
     const r=await fetch('/api/zeref/library/search',{method:'POST',credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({query:readInfo(saying).text.slice(-1000),k:3})});
     const j=await r.json().catch(()=>null);
     if(r.ok&&Array.isArray(j?.hits)){const c=libraryContext(j.hits,saying);used=c.used;libraryText=c.text;if(!used.length)setLibNote('Nothing in your library matched this message, so Zeref answered without notes.');}
     else setLibNote('Library lookup failed ('+(j?.error||r.status)+'). Zeref answered without notes.');
    }catch{if(controller.signal.aborted)return;setLibNote('Library lookup failed. Zeref answered without notes.');}
    if(controller.signal.aborted||personaKey.current!==forKey||privateSelection.current!==forSelection)return;
   }
   // Zeref's knowledge bank (opt-in): deterministic keyword lookup in the open-license library; passages are copied verbatim and shown with their source.
   let bankUsed:BankUsed[]=[];
   if(persona.source==='zeref'&&bankOn){
    try{
     if(!bankRef.current){const r=await fetch(BANK_URL,{cache:'force-cache',signal:controller.signal});if(r.ok)bankRef.current=buildBank(await r.json());}
     if(bankRef.current){bankRef.current=await loadShardsFor(bankRef.current,readInfo(saying).text.slice(-300),async(u:string)=>{const r=await fetch(u,{cache:'force-cache',signal:controller.signal});if(!r.ok)throw new Error(String(r.status));return r.json();});}
     if(bankRef.current){const c=bankContext(searchBank(bankRef.current,readInfo(saying).text.slice(-300)));bankUsed=c.used;if(c.text)libraryText=[libraryText,c.text].filter(Boolean).join(' | ');}
    }catch{if(controller.signal.aborted)return;}
    if(controller.signal.aborted||personaKey.current!==forKey||privateSelection.current!==forSelection)return;
   }
   const ask={persona,history:chatOnly(log),text:saying,shareHistory,observation,context:[knownGameContext(session,gameBridge?.key),shareGrowth?growthModelContext(growth):''].filter(Boolean).join('\n'),signal:controller.signal,
    ollama:{url:prefs.ollamaUrl,model:prefs.ollamaModel},hf:{key:hfKey,model:prefs.hfModel,spendConfirmed:spend}};
   // Teacher design: any non-RAWRPHOS brain is a TEACHER. RAWRPHOS still writes the
   // Beast's own reply; the teacher's answer is shown separately and labeled.
   const teaching=isTeacherRoute(route);
   // Cory (2026-10-16): chat is ALWAYS Zeref's own RAWRPHOS voice. Teachers run in the
   // background only to make distillation lessons; their text is never shown.
   const [teacherResult,result]=await Promise.all([teaching?talkToBeast({...ask,route}).catch(()=>null):Promise.resolve(null),talkToBeast({...ask,route:'guest-rawrphos',library:libraryText})]);
   if(pending.current!==controller||controller.signal.aborted||personaKey.current!==forKey||privateSelection.current!==forSelection)return;
   if(teacherResult&&teacherResult.ok&&teacherResult.route!=='shared-ollama')recordTeacherPair(saying,{text:teacherResult.reply,label:TEACHER_LABEL[teacherResult.route]||teacherResult.label,model:teacherResult.model,route:teacherResult.route});
   // A teacher that couldn't connect is reported honestly (with setup help) but never blocks Zeref's own reply.
   const teacherDown=teacherResult&&!teacherResult.ok?{error:'Teacher not connected: '+teacherResult.error,help:teacherResult.help,route:teacherResult.route}:null;
   if(!result.ok){
    // Honest, visible, in the conversation: no reply was produced and nothing is shown as Zeref's voice.
    // The message stays in the box so Send/Retry works again without reloading.
    const at=Date.now();
    setLog(prev=>[...prev,{role:'you',text:saying,at,id:'failed-'+at+'-you'},{role:'system',text:`${persona.name}'s model is offline (${result.error||'no verified reply'}). No reply was shown as ${persona.name}. Your message is still in the box; tap Retry.`,at,id:'failed-'+at+'-sys'}]);
    setOffline({error:`${persona.name}'s verified RAWRPHØS model did not answer: ${result.error||'no verified reply'}`+(teacherDown?' '+teacherDown.error:''),help:teacherDown?.help||[],route:'guest-rawrphos'});return;}
   if(teacherDown)setOffline(teacherDown);
   const exchangeId=crypto.randomUUID(),at=Date.now();
   const coachedBy=teacherResult&&teacherResult.ok?TEACHER_LABEL[teacherResult.route]||teacherResult.label:undefined;
   const youTurn={role:'you' as const,text:saying,at,id:exchangeId+'-you'};
   const next=[...log.filter(t=>!String(t.id||'').startsWith('failed-')),youTurn,{role:'beast' as const,text:result.reply,model:result.model,route:result.route,at:result.at,id:exchangeId+'-beast',coachedBy,read:result.read?{readChars:result.read.readChars,totalChars:result.read.totalChars,extracted:result.read.extracted,note:result.read.note}:undefined,libraryUsed:used.length?used.map(u=>({title:u.title,loc:u.loc})):undefined,bank:bankUsed.length?bankUsed:undefined,stillLearning:persona.source==='zeref'&&bankOn&&isStillLearningReply(result.reply)?true:undefined}];
   setLog(next);setNotes(used.length?{id:exchangeId+'-beast',items:used}:null);writeTalkLog(storage.current,forKey,chatOnly(next));setVerifiedAt(result.ok?result.at:at);editText('');
   if(visitorId&&storage.current){const prior=growth?.beastKey===forKey?growth:freshGrowth(visitorId,forKey);const updated=advanceVisitorGrowth(prior,{text:saying,reply:result.reply,verified:true});writeVisitorGrowth(storage.current,updated);setGrowth(updated);}
   if(boundForCloud){try{privateQueue.current?.enqueue({...boundForCloud,exchange:{eventId:exchangeId,text:saying,reply:result.reply,provider:result.route,model:result.model,at}});}catch(error){setCloudStatus((error instanceof Error?error.message:'Private queue unavailable.')+' The completed reply remains in local storage.');}}
   // Same Beast, same growth: a verified exchange adds to the saved Beast's chat and bond.
   if(retention==='device'&&beastId&&session?.beast&&persona.source==='spark')void change(draft=>{if(beastIdentity(draft.beast)===beastId)rememberExchange(draft,saying,result.reply);});
  }finally{
   window.clearTimeout(timeout);
   if(pending.current===controller||!pending.current||pending.current.signal.aborted){pending.current=null;setBusy(false);}
  }
 }
 function recordTeacherPair(prompt:string,teacher:TeacherHint){
  // Distillation candidate: kept on THIS device by default; never shared across visitors.
  const pair=makePair({prompt,reply:teacher.text,route:teacher.route,model:teacher.model,beast:persona.name});
  const rows=rememberPair(localStorage,pair);setPairCount(rows.length);
  // Shared training only with explicit opt-in. Brain Bay is the owner's own paired
  // provider (owner-only route), so the owner path auto-contributes.
  const owner=teacher.route==='connected-brain-bay';
  // Cory's shared Ollama is fed to distillation server-side; never re-sent from the browser.
  if(!pair||teacher.route==='shared-ollama'||!(contribute||owner))return;
  const body=contributionBody(pair);
  if(!body){setContribStatus('This teacher pair looked like it had private info, so it stayed on your device only.');return;}
  void fetch('/api/teacher-pairs',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
   .then(async r=>{const j=await r.json().catch(()=>null);setContribStatus(r.ok?`Shared for review (${j?.review_status||'pending'}).`:(j?.error||'Not shared; kept on this device.'));})
   .catch(()=>setContribStatus('Not shared; kept on this device.'));
 }
 function toggleContribute(on:boolean){setContribute(on);writeContribute(localStorage,on);setContribStatus(on?'Future teacher answers will be shared for training review after a privacy filter.':'Teacher answers stay on this device only.');}
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
  // Seeded synthetic voice; only the Beast's own RAWRPHOS turn is ever spoken (never teacher text).
  const line=speakableText(lastReply);if(!line)return;
  const r=speakSeeded(line,voiceProfile(persona.key||ZEREF_VOICE_SEED),{volume:audioState.volume,onend:()=>setSpeaking(false)});setSpeaking(r.ok);
 }

 return <section className={styles.panel} data-compact={compact||undefined} data-overlay data-talk-state={state} data-talk-route={route} aria-label={`Talk to ${persona.name}`}>
  <div className={styles.body}>
  <header className={styles.who}>
   <div className={styles.avatar} aria-hidden="true">{persona.source==='zeref'?'🌙':persona.source==='spark'?'🐣':'✦'}</div>
   <div className={styles.whoText}>
    {companion?<div role="tablist" aria-label="Who to talk to" data-talk-target style={{display:'flex',gap:6,marginBottom:6}}>
     <button type="button" role="tab" aria-selected={target==='companion'} className={styles.ghost} style={{fontWeight:target==='companion'?800:400}} onClick={()=>choose('companion')}>🐣 {companion.name}</button>
     <button type="button" role="tab" aria-selected={target==='zeref'} className={styles.ghost} style={{fontWeight:target==='zeref'?800:400}} onClick={()=>choose('zeref')} data-talk-zeref>🌙 Talk to Zeref</button>
    </div>:null}
    <h2>{ready?title||`Talk to ${persona.name}`:'Finding your Beast…'}</h2>
    <p><strong>{persona.name}</strong> · {persona.kind}. {persona.traits.join(', ')}.</p>
    {persona.source==='zeref'?<small data-chat-identity data-chat-qbeast="bb-deada969" data-chat-step={RAWRPHOS_PUBLIC_PIN.step}>Zeref · built on RAWRPHØS · voice: RAWRPHØS step {RAWRPHOS_PUBLIC_PIN.step} (public chat pin; each reply is checked against it)</small>:null}
    <small>{persona.source==='zeref'?'Showing Zeref, the site Beast. Meet your own Beast in My Beast and it will talk here instead.':persona.source==='spark'?'Your saved Beast. Its name, personality and memories stay the same whichever brain answers.':'Your Beast Cage creature. Its personality stays the same whichever brain answers.'}</small>
   </div>
  </header>

  <div className={styles.brainBar} data-tone={connection.tone}>
   <span className={styles.light} aria-hidden="true"/>
   <div className={styles.brainText} role="status" aria-live="polite">
    <strong data-teacher-header style={{fontSize:11,fontWeight:500,opacity:.7}}>{persona.name}&apos;s teacher: {TEACHER_LABEL[route]||info.label}</strong>
    <span>{connection.text}</span>
    <a className={styles.workstationLink} href="/workspace">Workshop →</a>
   </div>
   <button type="button" className={styles.ghost} aria-expanded={showBrains} onClick={()=>setShowBrains(v=>!v)}>{showBrains?'Done':'Change teacher'}</button>
  </div>

  <details className={styles.brains} data-visitor-growth>
   <summary>My COSMOS growth · {growth?.exchanges??0} verified exchange{(growth?.exchanges??0)===1?'':'s'} · this browser only</summary>
   <p>Curiosity {growth?.curiosity??50} · Resonance {growth?.resonance??50} · Stability {growth?.stability??50} · Signal {growth?.signal??50}</p>
   <small>Local classical QVM-inspired stimulus (Rigetti-style simulation, NOT a Rigetti cloud or hardware run). No shared model weights are retrained. The growth record stores aggregates, not raw conversation text.</small>
   <label className={styles.check}><input type="checkbox" checked={shareGrowth} onChange={e=>toggleGrowth(e.target.checked)}/> Share my local growth summary with whichever brain I select. Use the separate history control to include previous messages. Off by default.</label>
   <small>When enabled, cloud model providers may receive this context. Your browser ID is never included.</small>
   <button type="button" className={styles.ghost} onClick={resetGrowth} disabled={!visitorId||busy}>Reset my local growth</button>
  </details>

  {showBrains?<fieldset className={styles.brains}>
   <legend>Choose {persona.name}&apos;s teacher</legend>
   <p className={styles.advancedBrain} data-advanced-brain>Advanced · Brain: {info.label} (teacher) · <code>{modelName}</code>. {persona.name}&apos;s own voice is always RAWRPHØS. A teacher only coaches in the background; its answer becomes a lesson and is never shown or spoken as {persona.name}.</p>
   <label className={styles.check} data-teacher-contribute><input type="checkbox" checked={contribute} onChange={e=>toggleContribute(e.target.checked)}/> Help train RAWRPHØS: share my teacher answers (not my key, not my history) for review. Off by default. Private info is filtered out and pairs are rate-limited.</label>
   <small data-teacher-pairs>{pairCount} teacher pair{pairCount===1?'':'s'} saved on this device only.{contribStatus?' '+contribStatus:''}</small>
   {TALK_ROUTES.map(key=><label key={key} className={styles.brainChoice} data-selected={route===key||undefined}>
    <input type="radio" name="talk-brain" value={key} checked={route===key} onClick={()=>savePrefs({route:key as Route})} onChange={()=>savePrefs({route:key as Route})}/>
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

  <details className={styles.options} data-brain-reads-details><summary>How much does {persona.name} read?</summary><ReadsBox/></details>

  <div className={styles.log} aria-label={`Conversation with ${persona.name}`} aria-live="polite">
   {log.length===0?<p className={styles.empty}>Say hi to {persona.name}! 👋 Type below, then tap Send.<small> {persona.name}&apos;s replies come from RAWRPHØS, never from a script. Teachers coach RAWRPHØS in the background; their words are never shown as {persona.name}&apos;s.</small></p>:
    log.map((turn,i)=>turn.role==='system'?<div key={i} className={styles.offline} role="status" data-model-offline-turn><strong>⚠ Model offline · not {persona.name}&apos;s voice</strong><p>{turn.text}</p></div>:<div key={i} style={{display:'contents'}}><div className={turn.role==='you'?styles.you:styles.beast}>
     <span className={styles.speaker}>{turn.role==='you'?'You':persona.name}{turn.role==='beast'&&turn.model?<Details inline label="·"><em>via {turn.model}</em></Details>:null}</span>
     <p>{turn.text}</p>
     {turn.reachOut?<small data-reach-out>💬 {REACH_OUT_LABEL} · {turn.reachOut}</small>:null}
     {turn.role==='beast'&&turn.coachedBy?<small data-coached-by>Coached by: {turn.coachedBy}</small>:null}
     {turn.role==='beast'&&turn.read&&(turn.read.extracted||turn.libraryUsed)?<small data-read-note>{turn.read.extracted?turn.read.note:`${persona.name} read all ${turn.read.totalChars.toLocaleString('en-US')} characters of your message.`}{turn.libraryUsed?` Notes recorded from your library: ${turn.libraryUsed.map(u=>u.title+(u.loc?' ('+u.loc+')':'')).join('; ')}.`:''}</small>:null}
     {turn.role==='beast'&&notes&&notes.id===turn.id?<RecordedNotes items={notes.items}/>:null}
     {turn.role==='beast'&&(turn.stillLearning||turn.bank?.length)?<div data-knowledge-bank-notes role="note">
      {turn.stillLearning?<small data-still-learning>{stillLearningNote(turn.bank)}</small>:null}
      {(turn.bank||[]).map(b=><div key={b.id} data-bank-passage><q>{b.excerpt}</q><small>{BANK_LABEL} · {provenanceLine({...b,score:0,domain:''})}</small></div>)}
     </div>:null}
    </div>
    </div>)}
   {busy?<div className={styles.beast}><span className={styles.speaker}>{persona.name}</span><p className={styles.thinking}>thinking<span>.</span><span>.</span><span>.</span></p></div>:null}
   <div ref={logEnd}/>
  </div>

  {offline?<div className={styles.offline} role="alert">
   <strong>Model offline: no reply was received</strong>
   <p>{offline.error}</p>
   {offline.help.length?<><span>How to connect a brain:</span><ul>{offline.help.map(line=><li key={line}>{line}</li>)}</ul></>:null}
   <button type="button" className={styles.ghost} data-chat-retry disabled={busy||!text.trim()} onClick={()=>document.querySelector<HTMLFormElement>('form[data-companion-chat-form]')?.requestSubmit()}>Retry</button>
   {!showBrains&&offline.help.length?<button type="button" className={styles.ghost} onClick={()=>setShowBrains(true)}>Pick another teacher</button>:null}
  </div>:null}

  {persona.source==='zeref'?<ZerefLibraryPanel onState={setLib}/>:null}
  {libNote?<small data-library-note role="status">{libNote}</small>:null}

  <details className={styles.options}><summary>Conversation & observation settings</summary>
   <p role="status">{cloudStatus}</p><button type="button" disabled={busy||cloudBusy||!conversationReady||!session?.beast} onClick={()=>void restorePrivate()}>Restore my private cloud conversation</button>
   <label><input type="checkbox" checked={cloudSync} disabled={!cloudOwner||!cloudConsented||cloudBusy} onChange={e=>togglePrivateSync(e.target.checked)}/> Save new verified exchanges to my private cloud. Requires this Beast’s separate cloud consent in Settings.</label>
   {queueState.pending>0?<button type="button" disabled={cloudBusy||!cloudSync||!cloudConsented} onClick={()=>void privateQueue.current?.retry()}>Retry private save ({queueState.pending})</button>:null}
   <label>Keep this conversation <select value={retention} onChange={e=>{const next=e.target.value==='session'?'session':'device';const target=next==='session'?sessionStorage:localStorage;writeTalkLog(target,persona.key,chatOnly(log));writeTalkDraft(target,persona.key,text);if(next==='session'){localStorage.removeItem(LOG_PREFIX+persona.key);localStorage.removeItem(DRAFT_PREFIX+persona.key);}setRetention(next);try{localStorage.setItem(TALK_RETENTION_KEY,next);}catch{/* optional */}}}><option value="device">On this device</option><option value="session">In this tab only</option></select></label>
   <label><input type="checkbox" checked={shareHistory} onChange={e=>setShareHistory(e.target.checked)}/> Share recent conversation with the selected provider</label>
   {persona.source==='zeref'?<label data-bank-toggle><input type="checkbox" checked={bankOn} onChange={e=>toggleBank(e.target.checked)}/> Let Zeref use his knowledge bank (open-license English, math, world facts and his own world, looked up by keyword; each passage is shown with its source). Off by default.</label>:null}
   {gameBridge&&gameBridge.key===gameBeastKey(session)?<><label><input type="checkbox" checked={includeGame} onChange={e=>setIncludeGame(e.target.checked)}/> Include measured game screen brightness, contrast and color</label><GameChatTools bridge={gameBridge} busy={busy} route={route} optedIn={includeGame}/></>:<p>Observation mode: creature identity and your message. No live game vision bridge is connected.</p>}
   <p>Voice typing starts only on your tap and may use your browser’s speech service. Speech playback follows your sound settings.</p>
  </details>
  </div>
  <form data-companion-chat-form className={styles.form} onSubmit={send}>
   <label htmlFor="beast-talk-input" className={styles.srOnly}>Message to {persona.name}</label>
   <textarea id="beast-talk-input" value={conversationReady?text:''} onChange={e=>editText(e.target.value)} rows={compact?2:3} maxLength={MAX_MESSAGE} disabled={busy||cloudRestoring||!conversationReady}
    placeholder={`Say something to ${persona.name}…`} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form?.requestSubmit();}}}/>
   <div className={styles.actions}>
    <button type="button" className={styles.ghost} onClick={listen} aria-pressed={listening} disabled={busy}>{listening?'Stop':'🎙 Voice'}</button>
    {lastReply?<button type="button" className={styles.ghost} onClick={speak} aria-pressed={speaking}>{speaking?'Stop voice':'🔊 Hear reply'}</button>:null}
    {log.length?<button type="button" className={styles.ghost} onClick={clearLog} disabled={busy}>Clear</button>:null}
    {busy?<button type="button" className={styles.ghost} onClick={cancel}>Cancel</button>:null}
    <button type="submit" className={styles.send} disabled={busy||cloudRestoring||!conversationReady||!text.trim()}>{busy?'Waiting…':'Send'}</button>
   </div>
   <small className={styles.count} data-typed-count>{text.length.toLocaleString('en-US')}/{MAX_MESSAGE.toLocaleString('en-US')} ·{text.length>400?` ${persona.name} reads about ${readInfo(text,undefined,lib.ready?500:0).readChars.toLocaleString('en-US')} of these. ·`:''} {retention==='device'?'Saved on this device':'Kept in this tab'} · {persona.name}.</small>
  </form>
 </section>;
}
