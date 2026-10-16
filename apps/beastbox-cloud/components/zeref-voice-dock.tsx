'use client';
import {useEffect,useRef,useState} from 'react';
import {talkToBeast} from '../lib/companion/beast-talk.mjs';
import {autonomyTickMs,beatMs,HEART_FALLBACK} from '../lib/companion/zeref-heart.mjs';
import {voiceProfile,speakSeeded,readPrefs,writePrefs,armOnFirstTap,canReachOut,recordReachOut,reachOutPrompt,REACH_OUT_LABEL,VOICE_LABEL,ZEREF_VOICE_SEED} from '../lib/companion/seeded-voice.mjs';

type Prefs=ReturnType<typeof readPrefs>&{mutedByUser?:boolean};
const MOODS=['joy','curiosity','fear','calm','mischief'];
function moodToEmotion(m:string){const s=String(m||'').toLowerCase();return MOODS.find(k=>s.includes(k.slice(0,4)))||(/play|zoom/.test(s)?'mischief':/happy/.test(s)?'joy':/rest|sleep/.test(s)?'calm':null);}

/** Zeref's autonomous voice + reach-out messages. On-device only; only his own RAWRPHØS text or diary line. */
export default function ZerefVoiceDock(){
 const [prefs,setPrefs]=useState<Prefs|null>(null);
 const [bubble,setBubble]=useState<{text:string;by:string}|null>(null);
 const [heart,setHeart]=useState<any>(HEART_FALLBACK);
 useEffect(()=>{fetch('/spark/zeref-heart.json').then(r=>r.ok?r.json():null).then(h=>{if(h?.bpm)setHeart(h);}).catch(()=>{});},[]);
 const lastActivity=useRef(Date.now()),busy=useRef(false),prefsRef=useRef<Prefs|null>(null);
 const save=(p:Prefs)=>{prefsRef.current=p;setPrefs(p);writePrefs(localStorage,p);};
 useEffect(()=>{const p=readPrefs(localStorage) as Prefs;prefsRef.current=p;setPrefs(p);
  const tap=()=>{const cur=prefsRef.current;if(cur&&!cur.armed)save(armOnFirstTap(cur) as Prefs);};
  const act=()=>{lastActivity.current=Date.now();};
  const speak=(e:Event)=>{const d=(e as CustomEvent).detail||{};const cur=prefsRef.current;if(cur?.voice&&cur.armed&&d.text)speakSeeded(d.text,voiceProfile(d.seed||ZEREF_VOICE_SEED,d.emotions||null));};
  window.addEventListener('pointerdown',tap,{once:false});window.addEventListener('keydown',act);window.addEventListener('pointerdown',act);window.addEventListener('zeref:speak',speak);
  const timer=setInterval(()=>void tick(),autonomyTickMs(HEART_FALLBACK,12));
  return ()=>{clearInterval(timer);window.removeEventListener('pointerdown',tap);window.removeEventListener('keydown',act);window.removeEventListener('pointerdown',act);window.removeEventListener('zeref:speak',speak);};
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[]);
 async function tick(){
  const p=prefsRef.current;if(!p||busy.current)return;const now=Date.now();
  if(!canReachOut(p,now,lastActivity.current,document.visibilityState==='visible').ok)return;
  busy.current=true;save(recordReachOut(p,now) as Prefs);
  try{
   const d=await fetch('/api/zeref/diary',{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null);
   const e=d?.recent?.[0]||{};const mood=String(e.mood||''),place=String(e.place||''),diary=String(e.thought?.text||'');
   const idleMin=Math.round((now-lastActivity.current)/60000);
   let text='',by='';
   const r:any=await talkToBeast({route:'guest-rawrphos',text:reachOutPrompt({mood,place,event:diary,idleMin})}).catch(()=>null);
   if(r?.ok&&r.route==='guest-rawrphos'&&r.reply){text=String(r.reply).slice(0,400);by='RAWRPHØS';}
   else if(diary){text=diary;by='his diary';}
   if(!text)return;
   setBubble({text,by});window.dispatchEvent(new CustomEvent('zeref:reach-out',{detail:{text,by,at:now,mood,place}}));
   const cur=prefsRef.current;const emo=moodToEmotion(mood);
   if(cur?.voice&&cur.armed)speakSeeded(text,voiceProfile(ZEREF_VOICE_SEED,emo?{dominant:emo}:null));
   setTimeout(()=>setBubble(b=>b&&b.text===text?null:b),180000);
  }finally{busy.current=false;}
 }
 if(!prefs)return null;
 const ms=beatMs(heart),btn:React.CSSProperties={width:34,height:34,borderRadius:17,border:'1px solid #6b5bd6',background:'#121833dd',color:'#fff',fontSize:15,padding:0,cursor:'pointer'};
 return <div data-zeref-voice-dock style={{position:'fixed',left:6,top:'38vh',zIndex:30,display:'flex',flexDirection:'column',gap:6,font:'12px system-ui',color:'#e8ecff'}}>
  <style>{`@keyframes zerefBeat{0%,100%{transform:scale(1)}12%{transform:scale(1.25)}24%{transform:scale(1)}36%{transform:scale(1.12)}}`}</style>
  <span data-zeref-heart title={`Zeref's heart · ${Math.round(heart.bpm)} BPM · rhythm from Cory's heartbeat recording (a creative seed, not a biological signal)`} aria-label={`Zeref's heart, ${Math.round(heart.bpm)} beats per minute`} style={{...btn,display:'inline-flex',alignItems:'center',justifyContent:'center',animation:`zerefBeat ${ms}ms infinite`}}>💜</span>
  <button type="button" style={btn} data-zeref-voice-toggle aria-pressed={prefs.voice} aria-label={prefs.voice?'Zeref voice on (tap to mute)':'Zeref voice off (tap to turn on)'} title={(prefs.voice?'Zeref voice on · ':'Zeref voice off · ')+VOICE_LABEL}
   onClick={()=>save({...prefs,armed:true,voice:!prefs.voice,mutedByUser:prefs.voice})}>{prefs.voice?'🔊':'🔇'}</button>
  <button type="button" style={{...btn,opacity:prefs.reachOut?1:.5}} data-zeref-reachout-toggle aria-pressed={prefs.reachOut} aria-label={prefs.reachOut?'Zeref reach-outs on (tap to turn off)':'Zeref reach-outs off (tap to turn on)'} title={prefs.reachOut?'Reach-outs on':'Reach-outs off'}
   onClick={()=>save({...prefs,reachOut:!prefs.reachOut})}>💬</button>
  {bubble?<div role="status" data-zeref-reach-out style={{position:'absolute',left:42,top:0,width:'min(240px,calc(100vw - 70px))',background:'#121833ee',border:'1px solid #6b5bd6',borderRadius:12,padding:'8px 10px'}}>
   <small style={{opacity:.75}}>💬 {REACH_OUT_LABEL} · {bubble.by}</small><div>{bubble.text}</div>
   <button type="button" onClick={()=>setBubble(null)} style={{fontSize:11,marginTop:4}}>Dismiss</button></div>:null}
 </div>;
}
