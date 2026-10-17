'use client';
import {useEffect,useRef,useState} from 'react';
import {talkToBeast} from '../lib/companion/beast-talk.mjs';
import {analyzeFrame,analyzeAudio,notice,noticePrompt,experience,LOG_KEY} from '../lib/companion/field-perception.mjs';

const W=32,H=24,TALK_GAP=75000,MAX_LOG=300;
type Exp=ReturnType<typeof experience>;
function readLog():Exp[]{try{const v=JSON.parse(localStorage.getItem(LOG_KEY)||'[]');return Array.isArray(v)?v.slice(-MAX_LOG):[];}catch{return [];}}

/** Zeref's senses in the Open Field: camera + mic analysed on this device only. Signal reading only (the AR stage is separate). */
export default function FieldPerception(){
 const [on,setOn]=useState(false),[err,setErr]=useState(''),[mood,setMood]=useState('calm'),[seen,setSeen]=useState(''),[line,setLine]=useState<{text:string;by:string}|null>(null);
 const [p,setP]=useState<any>(null),[count,setCount]=useState(0),[share,setShare]=useState(false),[shareMsg,setShareMsg]=useState('');
 const stream=useRef<MediaStream|null>(null),video=useRef<HTMLVideoElement|null>(null),ctx=useRef<AudioContext|null>(null),timer=useRef<any>(null),lastTalk=useRef(0),prev=useRef<any>(null),gray=useRef<Float32Array|null>(null);
 useEffect(()=>{setCount(readLog().length);const stopAll=()=>stop();window.addEventListener('pagehide',stopAll);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});return()=>{window.removeEventListener('pagehide',stopAll);stop();};
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[]);
 function stop(){clearInterval(timer.current);timer.current=null;stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;ctx.current?.close().catch(()=>{});ctx.current=null;if(video.current)video.current.srcObject=null;setOn(false);}
 async function start(){
  setErr('');
  if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){setErr('Senses need a secure page with camera/mic access.');return;}
  try{
   const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:160}},audio:{echoCancellation:true,noiseSuppression:true}});
   stream.current=s;const v=video.current!;v.setAttribute('playsinline','');v.muted=true;v.srcObject=s;await v.play().catch(()=>{});
   const AC=(window as any).AudioContext||(window as any).webkitAudioContext;let an:AnalyserNode|null=null;
   if(AC&&s.getAudioTracks().length){const c:AudioContext=new AC();ctx.current=c;await c.resume().catch(()=>{});an=c.createAnalyser();an.fftSize=2048;c.createMediaStreamSource(s).connect(an);}
   const cv=document.createElement('canvas');cv.width=W;cv.height=H;const g=cv.getContext('2d',{willReadFrequently:true})!;
   const buf=new Float32Array(2048);
   timer.current=setInterval(()=>{
    if(!v.videoWidth)return;g.drawImage(v,0,0,W,H);const f=analyzeFrame(g.getImageData(0,0,W,H).data,gray.current,W,H);gray.current=f.gray;
    let a={loudness:0,pitchHz:0};if(an&&ctx.current){an.getFloatTimeDomainData(buf);a=analyzeAudio(buf,ctx.current.sampleRate);}
    const cur={brightness:f.brightness,hue:f.hue,motion:f.motion,gazeX:f.gazeX,gazeY:f.gazeY,...a};setP(cur);
    const n=notice(cur,prev.current);prev.current=cur;
    if(n){setMood(n.emotion);setSeen(n.event);
     const log=[...readLog(),experience(cur,Date.now())].slice(-MAX_LOG);try{localStorage.setItem(LOG_KEY,JSON.stringify(log));}catch{}setCount(log.length);
     if(Date.now()-lastTalk.current>TALK_GAP){lastTalk.current=Date.now();void react(n);}}
   },500);
   setOn(true);
  }catch{setErr('Camera/microphone permission was not given. Zeref keeps wandering without senses.');stop();}
 }
 async function react(n:{event:string;emotion:string}){
  const r:any=await talkToBeast({route:'guest-rawrphos',text:noticePrompt(n)}).catch(()=>null);
  if(!(r?.ok&&r.route==='guest-rawrphos'&&r.reply))return; // only his own RAWRPHOS words; otherwise stay silent
  const text=String(r.reply).slice(0,300);setLine({text,by:'RAWRPHØS'});
  window.dispatchEvent(new CustomEvent('zeref:speak',{detail:{text,emotions:{dominant:n.emotion}}}));
 }
 async function contribute(){
  if(!share){setShareMsg('Tick the opt-in box first.');return;}
  const ex=readLog().slice(-120);if(!ex.length){setShareMsg('No experiences yet.');return;}
  const r=await fetch('/api/zeref/perception',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({consent:true,experiences:ex})}).then(r=>r.json()).catch(()=>({error:'Network error'}));
  setShareMsg(r.ok?`Shared ${r.count} numeric experiences for review.`:String(r.error||'Not shared.'));
 }
 const eye={transform:`translate(${(p?.gazeX||0)*14}px,${(p?.gazeY||0)*8}px)`,transition:'transform .4s'};
 return <section data-field-perception style={{margin:'14px auto',maxWidth:560,padding:12,border:'1px solid #3b3f78',borderRadius:14,background:'#0d1230',color:'#e8ecff',font:'13px system-ui'}}>
  <h2 style={{margin:'0 0 6px',fontSize:16}}>Zeref&apos;s senses</h2>
  <p style={{margin:'0 0 8px',opacity:.8}}>Zeref can see and hear the room through your camera and mic. Everything is analysed on this device: brightness, colour, motion, loudness and pitch. No images or audio are saved or uploaded. This is simple signal reading. The walking creatures above use the camera overlay (iPhone) or true AR tracking (WebXR on Android); this panel does neither.</p>
  <video ref={video} playsInline muted style={{width:96,height:72,borderRadius:8,background:'#000',display:on?'inline-block':'none',verticalAlign:'middle'}}/>
  <span aria-hidden style={{display:'inline-flex',gap:10,margin:'0 12px',verticalAlign:'middle'}}>{[0,1].map(i=><span key={i} style={{width:26,height:26,borderRadius:13,background:'#ffd34d',display:'inline-flex',alignItems:'center',justifyContent:'center'}}><span style={{width:8,height:14,borderRadius:4,background:'#111',...eye}}/></span>)}</span>
  {on?<button type="button" onClick={stop} data-senses-stop>Stop senses</button>:<button type="button" onClick={()=>void start()} data-senses-start>👁️👂 Let Zeref see &amp; hear</button>}
  {err?<p role="status">{err}</p>:null}
  {on&&p?<p style={{margin:'6px 0'}}>Mood: <b>{mood}</b>{seen?<> · noticed {seen}</>:null}<br/><small>light {p.brightness} · motion {p.motion} · sound {p.loudness}{p.pitchHz?` · ~${p.pitchHz} Hz`:''}</small></p>:null}
  {line?<p data-field-line style={{background:'#171d44',borderRadius:10,padding:8}}><small style={{opacity:.75}}>Zeref, in his own words ({line.by}, synthetic voice if sound is on):</small><br/>{line.text}</p>:null}
  <p style={{margin:'8px 0 4px'}}><small>{count} numeric experiences saved on this device for his learning.</small></p>
  <label style={{display:'block'}}><input type="checkbox" checked={share} onChange={e=>setShare(e.target.checked)}/> Opt in: share these numeric experiences (no images/audio) to help train Zeref. Off by default.</label>
  <button type="button" onClick={()=>void contribute()} disabled={!share}>Share experiences</button> {shareMsg?<small role="status">{shareMsg}</small>:null}
 </section>;
}
