/** DOM surface for the same Beast chat client used by the React talk room. */
import {
 DEFAULT_HF_MODEL,DEFAULT_OLLAMA_MODEL,DEFAULT_OLLAMA_URL,DEFAULT_ROUTE,MAX_LOG,MAX_MESSAGE,
 ROUTE_INFO,TALK_ROUTES,connectHelp,talkPersona,talkToBeast,readTalkLog,writeTalkLog,
 LOG_PREFIX,DRAFT_PREFIX,readTalkDraft,writeTalkDraft,readTalkRetention,TALK_RETENTION_KEY,
} from './shared/beast-talk.mjs';
import {chatViewport} from './shared/chat-viewport.mjs';
import {getOrCreateVisitorId,readVisitorGrowth,writeVisitorGrowth,advanceVisitorGrowth,growthModelContext,freshGrowth} from './shared/visitor-growth.mjs';
import {loadPrivateChat,savePrivateExchange,mergePrivateChat} from './shared/private-chat.mjs';

const PREFS_KEY='beastbox-talk-prefs-v1',HF_KEY='beastbox-talk-hf-key-v1',GROWTH_CONSENT_KEY='beastbox-growth-context-consent-v1';
const DEFAULT_PREFS={route:DEFAULT_ROUTE,ollamaUrl:DEFAULT_OLLAMA_URL,ollamaModel:DEFAULT_OLLAMA_MODEL,hfModel:DEFAULT_HF_MODEL};
const time=at=>at?new Date(at).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'';
const optionalStorage=kind=>{try{return window[kind];}catch{return null;}};
function readPrefs(storage){
 try{const saved=JSON.parse(storage?.getItem(PREFS_KEY)||'{}');return {...DEFAULT_PREFS,...Object.fromEntries(['ollamaUrl','ollamaModel','hfModel'].filter(key=>typeof saved[key]==='string').map(key=>[key,saved[key]])),route:TALK_ROUTES.includes(saved.route)?saved.route:DEFAULT_ROUTE};}catch{return {...DEFAULT_PREFS};}
}

export function createSparkChatPopup({getBeast,getAvatar,onVerified,onPattern}){
 const $=id=>document.getElementById(id),overlay=$('spark-chat'),dialog=$('talk-dialog'),trigger=$('talk'),resume=$('talk-resume'),input=$('talk-text'),scroll=$('talk-scroll'),form=$('talk-form');
 const device=optionalStorage('localStorage'),tab=optionalStorage('sessionStorage');
 let prefs=readPrefs(device),retention=readTalkRetention(device),persona=null,log=[],pending=null,offline=null,verified=null,pattern='',open=false,opener=trigger,locked=null,inertNodes=[],visitorId=null,growth=null;
 let shareHistory=false,shareGrowth=false;
 let cloudState=null,cloudEnabled=false,cloudPending=null,cloudMode=null,cloudMessage='Private cloud is optional. Restore this creature’s conversation to check ownership and consent.';
 const cloudQueues=new Map(),historyMarker=crypto.randomUUID();
 let historyOwned=false,historyLeaving=false,reopenAfterHistory=null;
 const storage=()=>retention==='device'?device:tab;
 try{$('talk-hf-key').value=tab?.getItem(HF_KEY)||'';shareGrowth=device?.getItem(GROWTH_CONSENT_KEY)==='yes';}catch{}
 $('talk-share-growth').checked=shareGrowth;
 input.maxLength=MAX_MESSAGE;

 for(const route of TALK_ROUTES){
  const label=document.createElement('label'),radio=document.createElement('input'),copy=document.createElement('span'),name=document.createElement('strong'),detail=document.createElement('small');
  radio.type='radio';radio.name='talk-route';radio.value=route;radio.id='talk-route-'+route;radio.setAttribute('aria-label',ROUTE_INFO[route].label);
  name.textContent=ROUTE_INFO[route].label;detail.textContent=ROUTE_INFO[route].detail;copy.append(name,detail);label.append(radio,copy);$('talk-route-options').append(label);
  radio.addEventListener('change',()=>{if(radio.checked)savePrefs({route});});
 }
 function status(){
  const route=prefs.route,info=ROUTE_INFO[route],model=route==='local-ollama'?prefs.ollamaModel:route==='hf-byok'?prefs.hfModel:info.model;
  $('talk-source').textContent=`Selected brain: ${info.label} · ${model}`;
  $('talk-source').title=$('talk-source').textContent;
  $('talk-reply').textContent=pending?'Asking the selected model…':offline?'Model offline · no reply received':verified?`Connected · real reply verified ${time(verified.at)}`:'Not connected yet · each model reply is checked';
  $('talk-brain-bar').dataset.tone=pending?'busy':offline?'offline':verified?'verified':'ready';
  dialog.dataset.talkState=pending?'thinking':offline?'offline':verified?'replied':'idle';dialog.dataset.talkRoute=route;
  $('talk-send').disabled=!!pending||cloudMode==='restore'||!input.value.trim();$('talk-cancel').hidden=!pending;input.readOnly=!!pending||cloudMode==='restore';
  $('talk-pattern').disabled=!!pending||cloudMode==='restore'||!input.value.trim();$('talk-clear').disabled=!!pending||cloudMode==='restore'||!log.length;
  $('talk-count').textContent=`${input.value.length}/${MAX_MESSAGE}`;
  $('talk-resume-label').textContent=pending?`${persona?.name||'Beast'} is thinking…`:`Talk to ${persona?.name||'your Beast'}`;
  renderCloud();
 }
 function cloudQueue(){return cloudState?cloudQueues.get(persona?.key+'|'+cloudState.owner):null;}
 function renderCloud(){
  const queue=cloudQueue();$('talk-cloud-status').textContent=cloudMessage;
  $('talk-cloud-restore').disabled=!!pending||!!cloudPending;
  $('talk-cloud-sync').disabled=!cloudState?.consented||!!cloudPending||!!pending;$('talk-cloud-sync').checked=cloudEnabled;
  $('talk-cloud-retry').hidden=!queue?.paused||!queue.items.length;
  $('talk-cloud-retry').disabled=!!cloudPending||!!pending||!cloudState?.consented;
  $('talk-private-cloud').setAttribute('aria-busy',String(!!cloudPending));
 }
 function privateError(error){
  if(error?.name==='AbortError')return 'The private request was cancelled before an acknowledgement arrived.';
  if(error instanceof TypeError)return 'Could not reach private cloud memory. Check your connection and try again.';
  return error?.message||'Private cloud memory is unavailable.';
 }
 function resetCloud(){
  cloudPending?.abort();cloudPending=null;cloudMode=null;cloudState=null;cloudEnabled=false;
  cloudMessage='Private cloud is optional. Restore this creature’s conversation to check ownership and consent.';renderCloud();
 }
 async function restoreCloud(){
  if(pending||cloudPending)return;
  const key=persona.key,beast=structuredClone(getBeast()),expectedOwner=cloudState?.owner,controller=new AbortController();
  cloudPending=controller;cloudMode='restore';cloudState=null;cloudEnabled=false;cloudMessage='Restoring this creature’s private conversation…';status();
  try{
   const restored=await loadPrivateChat(beast,{signal:controller.signal,expectedOwner});
   if(controller.signal.aborted||cloudPending!==controller||persona.key!==key)return;
   log=mergePrivateChat(log,restored.rows.map(row=>({...row,cloudImported:true})));writeTalkLog(storage(),key,log);cloudState=restored;verified=null;
   cloudMessage=restored.consented?'Restored this creature’s private history. Imported turns are marked as unverified. You can choose to save new verified exchanges below.':'Restored private history. Conversation saving is off for this creature. Enable its private conversation consent in Settings, then restore again.';
   renderHistory();
  }catch(error){if(cloudPending===controller&&persona.key===key)cloudMessage=privateError(error)+' Your conversation stays in the selected local storage.';}
  finally{if(cloudPending===controller){cloudPending=null;cloudMode=null;status();}}
 }
 async function saveCloudQueue(){
  const queue=cloudQueue();if(cloudPending||!cloudState?.consented||!queue?.items.length)return;
  const key=persona.key,owner=cloudState.owner,controller=new AbortController();cloudPending=controller;cloudMode='save';queue.paused=false;
  try{
   while(queue.items.length){
    const saved=queue.items[0];cloudMessage=`Saving ${queue.items.length===1?'this exchange':queue.items.length+' exchanges'} to this creature’s private cloud…`;renderCloud();
    await savePrivateExchange(saved.beast,saved.exchange,{signal:controller.signal,expectedOwner:owner});
    if(controller.signal.aborted||cloudPending!==controller||persona.key!==key)return;
    queue.items.shift();cloudMessage='The completed exchange was saved to this creature’s private cloud.';
   }
  }catch(error){
   queue.paused=true;
   if(cloudPending===controller&&persona.key===key){
    cloudMessage=privateError(error)+' The completed reply stays in local storage. Retry cloud save uses the same exchange; it does not ask the model again.';
    if(/conversation storage is off|ownership changed/i.test(error?.message||'')){cloudState={...cloudState,consented:false};cloudEnabled=false;}
   }
  }finally{if(cloudPending===controller){cloudPending=null;cloudMode=null;renderCloud();}}
 }
 function queueCloudExchange(key,beast,exchange,owner){
  const queueKey=key+'|'+owner,queue=cloudQueues.get(queueKey)||{items:[],paused:false};
  queue.items.push({beast,exchange});cloudQueues.set(queueKey,queue);
  if(!queue.paused&&!cloudPending)void saveCloudQueue();else renderCloud();
 }
 function renderBrain(){
  for(const radio of $('talk-route-options').querySelectorAll('input'))radio.checked=radio.value===prefs.route;
  $('talk-ollama-fields').hidden=prefs.route!=='local-ollama';$('talk-hf-fields').hidden=prefs.route!=='hf-byok';
  $('talk-ollama-url').value=prefs.ollamaUrl;$('talk-ollama-model').value=prefs.ollamaModel;$('talk-hf-model').value=prefs.hfModel;
  $('talk-help').replaceChildren(...connectHelp(prefs.route).map(line=>{const li=document.createElement('li');li.textContent=line;return li;}));
  status();
 }
 function renderHistory(){
  $('talk-history').replaceChildren(...log.map(turn=>{
   const row=document.createElement('article'),speaker=document.createElement('span'),text=document.createElement('p');
   row.className='talk-turn '+(turn.role==='you'?'talk-you':'talk-beast');row.dataset.talkTurn=turn.role;
   speaker.className='talk-speaker';speaker.textContent=turn.role==='you'?'You':persona.name;
   if(turn.cloudImported){const imported=document.createElement('small');imported.className='talk-cloud-import';imported.textContent=' · cloud history, unverified';speaker.append(imported);}
   else if(turn.role==='beast'&&turn.model){const via=document.createElement('small');via.textContent=' · via '+turn.model;speaker.append(via);}
   text.textContent=turn.text;row.append(speaker,text);return row;
  }));
  $('talk-empty').hidden=!!log.length;$('talk-empty').textContent=`Say hi to ${persona.name}. A model reply appears here only after the selected brain answers.`;
  status();
 }
 function renderError(){
  $('talk-offline').hidden=!offline;
  $('talk-error').textContent=offline?.error||'';
  $('talk-error-help').replaceChildren(...(offline?.help||[]).map(line=>{const li=document.createElement('li');li.textContent=line;return li;}));
  $('talk-pattern-reply').hidden=!pattern;$('talk-pattern-text').textContent=pattern;
  status();
 }
 function renderGrowth(){
  $('talk-growth').textContent=growth?`${growth.exchanges} verified exchanges · curiosity ${growth.curiosity} · resonance ${growth.resonance}`:'Local experience is unavailable in this browser.';
 }
 function editDraft(value){input.value=String(value||'').slice(0,MAX_MESSAGE);writeTalkDraft(storage(),persona.key,input.value);status();}
 function cancel(){pending?.abort();}
 function abandon(){pending?.abort();pending=null;offline=null;verified=null;pattern='';status();renderError();}
 function savePrefs(next){
  abandon();prefs={...prefs,...next};try{device?.setItem(PREFS_KEY,JSON.stringify(prefs));}catch{}
  renderBrain();
 }
 function syncPersona(){
  const next=talkPersona({beast:getBeast()});
  if(next.key!==persona?.key){
   if(persona)writeTalkDraft(storage(),persona.key,input.value);
   resetCloud();abandon();persona=next;log=readTalkLog(storage(),next.key);input.value=readTalkDraft(storage(),next.key);
   shareHistory=false;$('talk-share-history').checked=false;
   visitorId=getOrCreateVisitorId(storage());growth=visitorId?readVisitorGrowth(storage(),visitorId,next.key):null;
   renderHistory();renderGrowth();
  }else persona=next;
  dialog.setAttribute('aria-label',`Talk to ${persona.name}`);$('talk-title').textContent=`Talk to ${persona.name}`;
  $('talk-persona').textContent=persona.traits.join(' · ');input.placeholder=`Say something to ${persona.name}…`;
  $('talk-input-label').textContent=`Message to ${persona.name}`;$('talk-history').setAttribute('aria-label',`Conversation with ${persona.name}`);
  resume.setAttribute('aria-label',`Resume conversation with ${persona.name}`);
  const avatar=getAvatar?.();if(avatar){const canvas=$('talk-avatar');canvas.getContext('2d').clearRect(0,0,64,64);canvas.getContext('2d').imageSmoothingEnabled=false;canvas.getContext('2d').drawImage(avatar,0,0,64,64);}
  status();
 }
 function viewport(){
  const visible=window.visualViewport,geometry=chatViewport(window.innerHeight,visible);
  overlay.dataset.keyboard=String(geometry.height<window.innerHeight*.78||geometry.bottom>80);
  overlay.style.setProperty('--talk-visible-height',geometry.height+'px');overlay.style.setProperty('--talk-keyboard-bottom',geometry.bottom+'px');
  overlay.style.setProperty('--talk-visible-width',(visible?.width||window.innerWidth)+'px');overlay.style.setProperty('--talk-visible-left',(visible?.offsetLeft||0)+'px');
 }
 function lock(){
  if(locked)return;
  locked={style:document.body.getAttribute('style'),x:window.scrollX,y:window.scrollY,htmlScrollBehavior:document.documentElement.style.scrollBehavior};
  Object.assign(document.body.style,{position:'fixed',top:-locked.y+'px',left:-locked.x+'px',width:'100%',overflow:'hidden'});
  inertNodes=[...document.body.children].filter(node=>node!==overlay&&node!==resume&&node.tagName!=='SCRIPT').map(node=>({node,inert:node.inert}));
  for(const {node}of inertNodes)node.inert=true;
 }
 function unlock(){
  if(!locked)return;
  for(const {node,inert}of inertNodes)node.inert=inert;inertNodes=[];
  const prior=locked;locked=null;
  if(prior.style===null)document.body.removeAttribute('style');else document.body.setAttribute('style',prior.style);
  document.documentElement.style.scrollBehavior='auto';window.scrollTo(prior.x,prior.y);document.documentElement.style.scrollBehavior=prior.htmlScrollBehavior;
 }
 function openChat(from=trigger){
  if(historyLeaving){reopenAfterHistory=from;return;}
  syncPersona();if(open){input.focus({preventScroll:true});return;}
  try{if(history.state?.beastboxChat!==historyMarker){const prior=history.state&&typeof history.state==='object'?history.state:{};history.pushState({...prior,beastboxChat:historyMarker},'',location.href);}historyOwned=history.state?.beastboxChat===historyMarker;}catch{historyOwned=false;}
  opener=from?.isConnected?from:trigger;open=true;overlay.hidden=false;resume.hidden=true;trigger.setAttribute('aria-expanded','true');viewport();lock();input.focus({preventScroll:true});
  if(log.length)scroll.scrollTop=scroll.scrollHeight;
 }
 function dismiss(minimize=false,{fromHistory=false}={}){
  if(!open){resume.hidden=true;return;}
  writeTalkDraft(storage(),persona.key,input.value);open=false;overlay.hidden=true;resume.hidden=!minimize;trigger.setAttribute('aria-expanded','false');unlock();
  (opener?.isConnected?opener:trigger).focus({preventScroll:true});
  if(!fromHistory&&historyOwned&&history.state?.beastboxChat===historyMarker){historyLeaving=true;try{history.back();}catch{historyLeaving=false;}}
  historyOwned=false;
 }
 async function send(event){
  event?.preventDefault();syncPersona();const text=input.value.trim();if(pending||cloudMode==='restore'||!text)return;
  const forKey=persona.key,forPersona={...persona,traits:persona.traits.slice()},forRetention=retention,forStorage=storage(),forLog=log.slice(),forBeast=structuredClone(getBeast()),forCloud=cloudEnabled&&cloudState?.consented?{...cloudState}:null,controller=new AbortController();
  pending=controller;offline=null;pattern='';status();renderError();
  const timeout=window.setTimeout(()=>controller.abort(),prefs.route==='local-ollama'?180000:65000);
  try{
   const result=await talkToBeast({route:prefs.route,persona:forPersona,text,history:forLog,shareHistory,context:shareGrowth?growthModelContext(growth):'',signal:controller.signal,
    ollama:{url:prefs.ollamaUrl,model:prefs.ollamaModel},hf:{key:$('talk-hf-key').value.trim(),model:prefs.hfModel,spendConfirmed:$('talk-hf-spend').checked}});
   if(pending!==controller||persona.key!==forKey)return;
   if(!result.ok){offline=result;renderError();if(open)scroll.scrollTop=scroll.scrollHeight;return;}
   let careError='';try{await onVerified?.({persona:forPersona,text,reply:result.reply,retention:forRetention,model:result.model});}catch(error){careError=error.message||'The creature care save was not confirmed.';}
   if(pending!==controller||persona.key!==forKey)return;
   const exchangeId=crypto.randomUUID(),at=result.at||Date.now();
   log=[...forLog,{id:exchangeId+'-you',role:'you',text,at},{id:exchangeId+'-beast',role:'beast',text:result.reply,route:result.route,model:result.model,at}].slice(-MAX_LOG);
   const saved=writeTalkLog(forStorage,forKey,log);verified=result;editDraft('');
   if(visitorId){growth=advanceVisitorGrowth(growth||freshGrowth(visitorId,forKey),{text,reply:result.reply,verified:true});writeVisitorGrowth(forStorage,growth);renderGrowth();}
   $('talk-save-note').textContent=careError||(!saved?'The model replied, but this browser could not save the conversation.':'');
   renderHistory();if(open)scroll.scrollTop=scroll.scrollHeight;
   if(forCloud&&cloudEnabled&&cloudState?.consented&&cloudState.owner===forCloud.owner)queueCloudExchange(forKey,forBeast,{eventId:exchangeId,text,reply:result.reply,provider:result.route,model:result.model,at},forCloud.owner);
  }finally{window.clearTimeout(timeout);if(pending===controller){pending=null;status();}}
 }
 trigger.setAttribute('aria-haspopup','dialog');trigger.setAttribute('aria-controls','talk-dialog');trigger.setAttribute('aria-expanded','false');
 trigger.addEventListener('click',()=>openChat(trigger));resume.addEventListener('click',()=>openChat(opener));
 $('talk-close').addEventListener('click',()=>dismiss());$('talk-minimize').addEventListener('click',()=>dismiss(true));
 $('talk-expand').addEventListener('click',()=>{const expanded=dialog.dataset.expanded!=='true';dialog.dataset.expanded=String(expanded);$('talk-expand').setAttribute('aria-pressed',String(expanded));$('talk-expand').setAttribute('aria-label',expanded?'Restore conversation size':'Expand conversation');$('talk-expand').textContent=expanded?'↙':'↗';});
 overlay.addEventListener('click',event=>{if(event.target===overlay)dismiss();});
 document.addEventListener('keydown',event=>{
  if(!open)return;
  if(event.key==='Escape'){event.preventDefault();event.stopPropagation();dismiss();return;}
  if(event.key!=='Tab')return;
  const focusable=[...dialog.querySelectorAll('button,input,textarea,select,summary,a[href],[tabindex]')].filter(node=>!node.disabled&&node.tabIndex>=0&&node.getClientRects().length);
  const first=focusable[0]||dialog,last=focusable.at(-1)||dialog;
  if(event.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){event.preventDefault();first.focus();}
 });
 input.addEventListener('input',()=>{pattern='';$('talk-pattern-reply').hidden=true;editDraft(input.value);});
 input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
 form.addEventListener('submit',send);$('talk-cancel').addEventListener('click',cancel);
 $('talk-change-brain').addEventListener('click',()=>{const show=$('talk-brains').hidden;$('talk-brains').hidden=!show;$('talk-change-brain').textContent=show?'Done':'Change brain';$('talk-change-brain').setAttribute('aria-expanded',String(show));if(show)scroll.scrollTop=0;});
 for(const [id,key]of [['talk-ollama-url','ollamaUrl'],['talk-ollama-model','ollamaModel'],['talk-hf-model','hfModel']])$(id).addEventListener('input',()=>{abandon();prefs={...prefs,[key]:$(id).value.trim()};try{device?.setItem(PREFS_KEY,JSON.stringify(prefs));}catch{}status();});
 $('talk-hf-key').addEventListener('input',()=>{abandon();try{if($('talk-hf-key').value)tab?.setItem(HF_KEY,$('talk-hf-key').value.trim());else tab?.removeItem(HF_KEY);}catch{}});
 $('talk-retention').value=retention;
 $('talk-retention').addEventListener('change',()=>{
  abandon();const prior=storage(),next=$('talk-retention').value==='session'?'session':'device',target=next==='device'?device:tab;
  if(writeTalkLog(target,persona.key,log)&&writeTalkDraft(target,persona.key,input.value)){
   if(prior!==target)try{prior?.removeItem(LOG_PREFIX+persona.key);prior?.removeItem(DRAFT_PREFIX+persona.key);}catch{}
   retention=next;try{device?.setItem(TALK_RETENTION_KEY,next);}catch{}
   visitorId=getOrCreateVisitorId(target);growth=visitorId?readVisitorGrowth(target,visitorId,persona.key):null;
   shareHistory=false;$('talk-share-history').checked=false;renderGrowth();
   $('talk-save-note').textContent=next==='session'?'This conversation stays in this tab. It will not update saved creature memories.':'';
  }else{$('talk-retention').value=retention;$('talk-save-note').textContent='This browser could not change conversation storage. Your current history was kept.';}
 });
 $('talk-share-history').addEventListener('change',()=>{shareHistory=$('talk-share-history').checked;});
 $('talk-cloud-restore').addEventListener('click',restoreCloud);
 $('talk-cloud-sync').addEventListener('change',()=>{cloudEnabled=$('talk-cloud-sync').checked&&cloudState?.consented===true;cloudMessage=cloudEnabled?'New verified exchanges for this creature will be saved to your private cloud. Provider history sharing stays under its separate control.':'Private saving is off for new exchanges. Your local conversation is kept.';renderCloud();});
 $('talk-cloud-retry').addEventListener('click',()=>void saveCloudQueue());
 $('talk-share-growth').addEventListener('change',()=>{shareGrowth=$('talk-share-growth').checked;try{device?.setItem(GROWTH_CONSENT_KEY,shareGrowth?'yes':'no');}catch{}});
 $('talk-reset-growth').addEventListener('click',()=>{if(visitorId&&!pending){growth=freshGrowth(visitorId,persona.key);writeVisitorGrowth(storage(),growth);renderGrowth();}});
 $('talk-clear').addEventListener('click',()=>{if(!pending){log=[];writeTalkLog(storage(),persona.key,log);renderHistory();}});
 $('talk-pattern').addEventListener('click',async()=>{
  if(pending||!input.value.trim()||!onPattern)return;
  try{pattern=await onPattern({persona,text:input.value.trim(),retention});renderError();if(open)scroll.scrollTop=scroll.scrollHeight;}
  catch(error){offline={error:error.message||'The on-device pattern was unavailable.',help:[]};renderError();}
 });
 window.visualViewport?.addEventListener('resize',viewport);window.visualViewport?.addEventListener('scroll',viewport);window.addEventListener('resize',viewport);window.addEventListener('orientationchange',viewport);
 window.addEventListener('popstate',()=>{
  if(historyLeaving){historyLeaving=false;const from=reopenAfterHistory;reopenAfterHistory=null;if(from)openChat(from);return;}
  if(open&&history.state?.beastboxChat!==historyMarker)dismiss(false,{fromHistory:true});
 });
 window.addEventListener('pagehide',()=>{cancel();resetCloud();dismiss(false,{fromHistory:true});historyLeaving=false;reopenAfterHistory=null;});
 window.addEventListener('beastbox:open-chat',event=>{openChat(trigger);if(typeof event.detail?.draft==='string')editDraft(event.detail.draft);});
 window.addEventListener('storage',event=>{if(event.key===PREFS_KEY){abandon();prefs=readPrefs(device);renderBrain();}});
 syncPersona();renderBrain();viewport();
 // A selected creature can render before this popup finishes wiring its event handlers.
 // Expose a narrow readiness contract so a tap or browser test is never mistaken for a failed chat.
 trigger.disabled=false;trigger.removeAttribute('aria-busy');trigger.dataset.chatReady='true';
 return {open:openChat,close:()=>dismiss(),syncPersona,setDraft:value=>{syncPersona();editDraft(value);},send:()=>form.requestSubmit()};
}
