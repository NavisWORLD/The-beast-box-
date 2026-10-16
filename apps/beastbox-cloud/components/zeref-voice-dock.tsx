'use client';
import {useEffect,useRef,useState} from 'react';
import {talkToBeast} from '../lib/companion/beast-talk.mjs';
import {voiceProfile,speakSeeded,readPrefs,writePrefs,armOnFirstTap,canReachOut,recordReachOut,reachOutPrompt,REACH_OUT_LABEL,VOICE_LABEL,ZEREF_VOICE_SEED} from '../lib/companion/seeded-voice.mjs';

type Prefs=ReturnType<typeof readPrefs>&{mutedByUser?:boolean};
const MOODS=['joy','curiosity','fear','calm','mischief'];
function moodToEmotion(m:string){const s=String(m||'').toLowerCase();return MOODS.find(k=>s.includes(k.slice(0,4)))||(/play|zoom/.test(s)?'mischief':/happy/.test(s)?'joy':/rest|sleep/.test(s)?'calm':null);}

/** Zeref's autonomous voice + reach-out messages. On-device only; only his own RAWRPHØS text or diary line. */
export default function ZerefVoiceDock(){
 const [prefs,setPrefs]=useState<Prefs|null>(null);
 const [bubble,setBubble]=useState<{text:string;by:string}|null>(null);
 const lastActivity=useRef(Date.now()),busy=useRef(false),prefsRef=useRef<Prefs|null>(null);
 const save=(p:Prefs)=>{prefsRef.current=p;setPrefs(p);writePrefs(localStorage,p);};
 useEffect(()=>{const p=readPrefs(localStorage) as Prefs;prefsRef.current=p;setPrefs(p);
  const tap=()=>{const cur=prefsRef.current;if(cur&&!cur.armed)save(armOnFirstTap(cur) as Prefs);};
  const act=()=>{lastActivity.current=Date.now();};
  const speak=(e:Event)=>{const d=(e as CustomEvent).detail||{};const cur=prefsRef.current;if(cur?.voice&&cur.armed&&d.text)speakSeeded(d.text,voiceProfile(d.seed||ZEREF_VOICE_SEED,d.emotions||null));};
  window.addEventListener('pointerdown',tap,{once:false});window.addEventListener('keydown',act);window.addEventListener('pointerdown',act);window.addEventListener('zeref:speak',speak);
  const timer=setInterval(()=>void tick(),30000);
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
   setTimeout(()=>setBubble(null),20000);
  }finally{busy.current=false;}
 }
 // The bottom-left corner is shared with the sound, support, Spark and Lost Cosmos docks, whose heights and stacking
 // change with the page and the selected Spark. Sit just above whichever of them shares our column instead of on top.
 const dockRef=useRef<HTMLDivElement|null>(null);const [lift,setLift]=useState(12);
 useEffect(()=>{if(!prefs)return;const sel='[class*="site-sound-dock"],.cosmic-support,[data-lost-cosmos-dock],[class*="sol-spark-player"],[class*="beast-chat-overlay"]';
  const place=()=>{const me=dockRef.current;if(!me)return;const w=me.getBoundingClientRect().width,H=innerHeight;let top=H;
   for(const el of document.querySelectorAll<HTMLElement>(sel)){if(me.contains(el)||el.contains(me))continue;const r=el.getBoundingClientRect();
    if(!r.width||!r.height||r.top<H*.45||r.right<12||r.left>12+w)continue;top=Math.min(top,r.top);}
   const next=Math.max(12,Math.round(H-top+8));setLift(v=>v===next?v:next);};
  place();const t=setInterval(place,800);addEventListener('resize',place);return ()=>{clearInterval(t);removeEventListener('resize',place);};},[prefs]);
 if(!prefs)return null;
 const box:React.CSSProperties={position:'fixed',left:12,bottom:lift,maxWidth:'min(300px, calc(100vw - 80px))',zIndex:60,font:'12px system-ui',color:'#e8ecff'};
 return <div ref={dockRef} style={box} data-zeref-voice-dock>
  {bubble?<div role="status" data-zeref-reach-out style={{background:'#121833ee',border:'1px solid #6b5bd6',borderRadius:12,padding:'8px 10px',marginBottom:6}}>
   <small style={{opacity:.75}}>💬 {REACH_OUT_LABEL} · {bubble.by}</small><div>{bubble.text}</div>
   <button type="button" onClick={()=>setBubble(null)} style={{fontSize:11,marginTop:4}}>Dismiss</button></div>:null}
  <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
   <button type="button" data-zeref-voice-toggle aria-pressed={prefs.voice} title={VOICE_LABEL}
    onClick={()=>save({...prefs,armed:true,voice:!prefs.voice,mutedByUser:prefs.voice})}>{prefs.voice?'🔊 Zeref voice on':'🔇 Zeref voice off'}</button>
   <button type="button" data-zeref-reachout-toggle aria-pressed={prefs.reachOut}
    onClick={()=>save({...prefs,reachOut:!prefs.reachOut})}>{prefs.reachOut?'💬 Reach-outs on':'💬 Reach-outs off'}</button>
  </div>
  {!prefs.armed?<small style={{display:'block',opacity:.7}}>Tap anywhere to let Zeref speak (synthetic on-device voice).</small>:null}
 </div>;
}
