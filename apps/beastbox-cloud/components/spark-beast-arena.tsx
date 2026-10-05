'use client';
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {Volume2,VolumeX,Zap} from 'lucide-react';
import SparkBeastCompanion,{type Genome} from './spark-beast-companion';
import {useBeastSession} from './beast-session';
import {buildMoveset,nextAttackDelay,pickAttack,roamAt,roarFor} from '../lib/companion/beast-moves.mjs';
import type {BaseLook,CreatureProfile} from '../lib/creature-profile';
import styles from './spark-beast-arena.module.css';

type VisualState='idle'|'listening'|'thinking'|'remembering'|'observing'|'sleeping'|'celebrating'|'halted';
type Move=NonNullable<ReturnType<typeof pickAttack>>;
type Moveset=ReturnType<typeof buildMoveset>;
type Particle={x:number;y:number;vx:number;vy:number;life:number;max:number;size:number;hue:number};
type Fx={move:Move;start:number;from:{x:number;y:number};to:{x:number;y:number};particles:Particle[];struck:boolean;seed:number};

/** Tiny deterministic PRNG for particle scatter (seeded from the move, never unseeded). */
function lcg(seed:number){let s=seed>>>0||1;return()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};}

/**
 * The live habitat creature on /beast-cage. It wraps the existing Spark Beast
 * renderer (same sprite, gait and generated voice) and adds seeded roaming,
 * a roar and attack effects. Moves come from the recorded-seed genome, so each
 * beast fights differently. Sound stays off until the visitor taps.
 */
export default function SparkBeastArena({profile,fallbackLook='nebula',state='idle',label}:{
 profile?:CreatureProfile|null;fallbackLook?:BaseLook;state?:VisualState;label?:string;
}){
 const {session}=useBeastSession();
 const root=useRef<HTMLDivElement>(null),fxCanvas=useRef<HTMLCanvasElement>(null),flash=useRef<HTMLDivElement>(null);
 const [genome,setGenome]=useState<Genome|null>(null);
 const [sound,setSound]=useState(false),soundRef=useRef(false),userMuted=useRef(false);
 const [reduced,setReduced]=useState(false),[visible,setVisible]=useState(true);
 const [toast,setToast]=useState<{text:string;crit:boolean;id:number}|null>(null);
 const [phase,setPhase]=useState<'idle'|'charge'|'strike'>('idle');
 const counter=useRef(0),fx=useRef<Fx|null>(null),busy=useRef(false);
 const audio=useRef<AudioContext|null>(null);
 const roamPos=useRef({x:0,y:0});
 const moveset:Moveset|null=useMemo(()=>genome?buildMoveset(genome):null,[genome]);
 const onGenome=useCallback((next:Genome)=>setGenome(next),[]);
 const name=genome?.names?.[2]||genome?.names?.[1]||profile?.name||'Spark Beast';

 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const update=()=>setReduced(media.matches);
  update();media.addEventListener('change',update);
  return()=>media.removeEventListener('change',update);
 },[]);

 useEffect(()=>{
  const node=root.current;
  if(!node||typeof IntersectionObserver!=='function')return;
  const io=new IntersectionObserver(entries=>setVisible(entries.some(e=>e.isIntersecting)),{threshold:.05});
  io.observe(node);
  const onVis=()=>setVisible(!document.hidden&&node.getBoundingClientRect().bottom>0);
  document.addEventListener('visibilitychange',onVis);
  return()=>{io.disconnect();document.removeEventListener('visibilitychange',onVis);};
 },[]);

 // Continuous seeded roam: the sprite wanders its own figure inside the habitat.
 useEffect(()=>{
  const node=root.current;
  if(!node||!moveset||!visible)return;
  if(reduced){node.style.setProperty('--roam-x','0px');node.style.setProperty('--roam-y','0px');roamPos.current={x:0,y:0};return;}
  let frame=0,clock=0,last=performance.now();
  const loop=(now:number)=>{
   // The beast plants its feet while it attacks, then keeps wandering its seeded path.
   if(!busy.current)clock+=Math.min(.1,(now-last)/1000);
   last=now;
   const rect=node.getBoundingClientRect();
   const p=roamAt(moveset,clock);
   const x=p.x*rect.width*.26,y=p.y*rect.height*.16;
   roamPos.current={x,y};
   node.style.setProperty('--roam-x',x.toFixed(1)+'px');
   node.style.setProperty('--roam-y',y.toFixed(1)+'px');
   node.style.setProperty('--roam-face',String(p.facing));
   frame=requestAnimationFrame(loop);
  };
  frame=requestAnimationFrame(loop);
  return()=>cancelAnimationFrame(frame);
 },[moveset,visible,reduced]);

 const ensureAudio=useCallback(async()=>{
  try{
   if(!audio.current){
    const Ctor=window.AudioContext||(window as unknown as {webkitAudioContext?:typeof AudioContext}).webkitAudioContext;
    if(!Ctor)return null;
    audio.current=new Ctor();
   }
   if(audio.current.state==='suspended')await audio.current.resume();
   return audio.current;
  }catch{return null;}
 },[]);

 // WebAudio roar: a swept, formant-filtered sawtooth plus a noise breath and an impact thump.
 const roar=useCallback(async(move:Move)=>{
  if(!soundRef.current||!genome)return;
  const ac=await ensureAudio();
  if(!ac)return;
  const spec=roarFor(genome,move);
  const t0=ac.currentTime+.02,charge=move.chargeMs/1000,dur=spec.seconds;
  const out=ac.createGain();out.gain.value=.9;out.connect(ac.destination);
  const osc=ac.createOscillator();osc.type='sawtooth';
  osc.frequency.setValueAtTime(spec.startHz*.7,t0);
  osc.frequency.exponentialRampToValueAtTime(spec.startHz,t0+charge*.8);
  osc.frequency.exponentialRampToValueAtTime(spec.peakHz,t0+charge+.08);
  osc.frequency.exponentialRampToValueAtTime(Math.max(40,spec.endHz),t0+charge+dur);
  const band=ac.createBiquadFilter();band.type='bandpass';band.frequency.value=spec.formantHz;band.Q.value=1.4;
  const low=ac.createBiquadFilter();low.type='lowpass';low.frequency.value=2600;
  const env=ac.createGain();
  env.gain.setValueAtTime(.0001,t0);
  env.gain.exponentialRampToValueAtTime(spec.gain*.25,t0+charge*.9);
  env.gain.exponentialRampToValueAtTime(spec.gain,t0+charge+.05);
  env.gain.exponentialRampToValueAtTime(.0001,t0+charge+dur);
  osc.connect(band);band.connect(low);osc.connect(low);low.connect(env);env.connect(out);
  osc.start(t0);osc.stop(t0+charge+dur+.05);
  const len=Math.floor(ac.sampleRate*(dur+.1));
  const buffer=ac.createBuffer(1,len,ac.sampleRate);const data=buffer.getChannelData(0);
  const rnd=lcg(move.counter*7919+17);
  for(let i=0;i<len;i++)data[i]=(rnd()*2-1)*(1-i/len);
  const noise=ac.createBufferSource();noise.buffer=buffer;
  const nf=ac.createBiquadFilter();nf.type='lowpass';nf.frequency.value=move.style==='quake'?700:1800;
  const ng=ac.createGain();ng.gain.value=spec.noise*spec.gain*.6;
  noise.connect(nf);nf.connect(ng);ng.connect(out);noise.start(t0+charge);
  const thump=ac.createOscillator();thump.type='sine';
  thump.frequency.setValueAtTime(120,t0+charge+.05);thump.frequency.exponentialRampToValueAtTime(38,t0+charge+.45);
  const tg=ac.createGain();tg.gain.setValueAtTime(.0001,t0+charge);tg.gain.exponentialRampToValueAtTime(.7*spec.gain,t0+charge+.07);tg.gain.exponentialRampToValueAtTime(.0001,t0+charge+.5);
  thump.connect(tg);tg.connect(out);thump.start(t0+charge);thump.stop(t0+charge+.55);
 },[genome,ensureAudio]);

 const spriteCenter=useCallback(()=>{
  const node=root.current;
  const sprite=node?.querySelector('[data-spark-beast="true"] canvas') as HTMLElement|null;
  if(!node)return{x:0,y:0};
  const box=node.getBoundingClientRect();
  if(!sprite)return{x:box.width/2,y:box.height/2};
  const r=sprite.getBoundingClientRect();
  return{x:r.left-box.left+r.width/2,y:r.top-box.top+r.height*.52};
 },[]);

 const attack=useCallback((trigger:'tap'|'timer'|'chat')=>{
  if(!moveset||busy.current)return;
  const move=pickAttack(moveset,counter.current++,trigger);
  if(!move)return;
  busy.current=true;
  setToast({text:`${name} used ${move.name}!`,crit:move.crit,id:move.counter});
  void roar(move);
  if(soundRef.current&&move.counter%2===0)window.dispatchEvent(new CustomEvent('beastbox:spark-chirp',{detail:{channel:'habitat',intensity:.9}}));
  const node=root.current;
  if(reduced||!node){
   // Reduced motion: no roaming, shake or flying particles, just a soft glow and the move name.
   node?.animate?.([{opacity:1},{opacity:.82},{opacity:1}],{duration:500});
   window.setTimeout(()=>{busy.current=false;},900);
   return;
  }
  const box=node.getBoundingClientRect();
  const from=spriteCenter();
  const side=from.x<box.width/2?1:-1;
  const to={x:Math.max(box.width*.12,Math.min(box.width*.88,from.x+side*box.width*(.3+((move.counter*37)%20)/100))),y:Math.max(box.height*.2,Math.min(box.height*.8,from.y-box.height*.12+((move.counter*53)%25)/100*box.height))};
  fx.current={move,start:performance.now(),from,to,particles:[],struck:false,seed:move.counter*2654435761};
  setPhase('charge');
 },[moveset,name,roar,reduced,spriteCenter]);

 // Effects renderer: charge-up, strike (beam / slash / burst / quake), impact particles, shake and hit flash.
 useEffect(()=>{
  if(phase==='idle')return;
  const canvas=fxCanvas.current,node=root.current,current=fx.current;
  if(!canvas||!node||!current)return;
  const ctx=canvas.getContext('2d');
  if(!ctx)return;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  const box=node.getBoundingClientRect();
  canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  const {move,from,to}=current;
  const rnd=lcg(current.seed);
  const habitat=node.parentElement;
  let frame=0;
  const spawn=(x:number,y:number,count:number,speed:number,hue:number)=>{
   for(let i=0;i<count;i++){
    const a=rnd()*Math.PI*2,v=speed*(.35+rnd());
    current.particles.push({x,y,vx:Math.cos(a)*v,vy:Math.sin(a)*v,life:0,max:.5+rnd()*.6,size:1.5+rnd()*3.5,hue:hue+(rnd()-.5)*30});
   }
  };
  let last=performance.now();
  const loop=(now:number)=>{
   const dt=Math.min(.05,(now-last)/1000);last=now;
   const t=now-current.start;
   const charge=move.chargeMs,strike=move.strikeMs;
   ctx.clearRect(0,0,box.width,box.height);
   ctx.globalCompositeOperation='lighter';
   const c=`hsl(${move.hue} 100% 62%)`,glow=`hsl(${move.accentHue} 100% 70%)`;
   if(t<charge){
    // Charge-up: a tightening ring and inward sparks around the sprite.
    const k=t/charge;
    ctx.strokeStyle=c;ctx.lineWidth=2+k*4;ctx.shadowColor=c;ctx.shadowBlur=18;
    ctx.beginPath();ctx.arc(from.x,from.y,70-k*42,0,Math.PI*2);ctx.stroke();
    const halo=ctx.createRadialGradient(from.x,from.y,0,from.x,from.y,24+k*30);
    halo.addColorStop(0,`hsla(${move.accentHue} 100% 75% / ${.15+k*.3})`);halo.addColorStop(1,'transparent');
    ctx.fillStyle=halo;ctx.beginPath();ctx.arc(from.x,from.y,24+k*30,0,Math.PI*2);ctx.fill();
    // Target lock: a spinning reticle where the strike will land.
    ctx.strokeStyle=glow;ctx.lineWidth=1.5;ctx.globalAlpha=.4+k*.5;
    for(let i=0;i<4;i++){const a=t/300+i*Math.PI/2;ctx.beginPath();ctx.arc(to.x,to.y,16+(1-k)*14,a,a+.9);ctx.stroke();}
    ctx.globalAlpha=1;
    if(rnd()<.8){const a=rnd()*Math.PI*2,r=80+rnd()*40;current.particles.push({x:from.x+Math.cos(a)*r,y:from.y+Math.sin(a)*r,vx:-Math.cos(a)*r*2.2,vy:-Math.sin(a)*r*2.2,life:0,max:.4,size:2+rnd()*2,hue:move.hue});}
    node.style.setProperty('--charge',String(1+k*.12));
   }else if(t<charge+strike){
    const k=(t-charge)/strike;
    node.style.setProperty('--charge','1');
    if(!current.struck){
     current.struck=true;
     setPhase('strike');
     spawn(to.x,to.y,move.particles,260,move.hue);
     spawn(from.x,from.y,Math.round(move.particles/2),140,move.accentHue);
     habitat?.animate?.(Array.from({length:8},(_,i)=>({translate:`${(i%2?1:-1)*move.shake*(1-i/8)}px ${((i*3)%2?-1:1)*move.shake*.6*(1-i/8)}px`})).concat([{translate:'0 0'}]),{duration:380,easing:'ease-out'});
     flash.current?.animate?.([{opacity:0},{opacity:move.crit?.9:.65},{opacity:0}],{duration:260});
     node.querySelector('[data-spark-beast="true"] canvas')?.animate?.([{filter:'brightness(1)'},{filter:'brightness(2.6) saturate(1.6)'},{filter:'brightness(1)'}],{duration:220});
    }
    ctx.shadowColor=c;ctx.shadowBlur=24;
    if(move.style==='beam'){
     const w=move.width*(1.2-Math.abs(k-.35))*2.2;
     const g=ctx.createLinearGradient(from.x,from.y,to.x,to.y);g.addColorStop(0,glow);g.addColorStop(1,c);
     ctx.strokeStyle=g;ctx.lineCap='round';ctx.lineWidth=Math.max(1,w);
     ctx.beginPath();ctx.moveTo(from.x,from.y);ctx.lineTo(to.x,to.y);ctx.stroke();
     ctx.strokeStyle='#fff';ctx.lineWidth=Math.max(1,w*.35);ctx.beginPath();ctx.moveTo(from.x,from.y);ctx.lineTo(to.x,to.y);ctx.stroke();
    }else if(move.style==='slash'){
     for(let i=0;i<3;i++){
      const kk=Math.max(0,Math.min(1,k*2.2-i*.25));if(kk<=0)continue;
      const r=46+i*10,a0=-2.4+i*.5;
      ctx.strokeStyle=i===1?'#fff':c;ctx.lineWidth=(move.width*.7)*(1-kk*.6);
      ctx.beginPath();ctx.arc(to.x,to.y,r,a0,a0+kk*2.2);ctx.stroke();
     }
    }else if(move.style==='burst'){
     ctx.strokeStyle=c;ctx.lineWidth=move.width*.6*(1-k);
     ctx.beginPath();ctx.arc(to.x,to.y,10+k*90,0,Math.PI*2);ctx.stroke();
     ctx.strokeStyle=glow;ctx.beginPath();ctx.arc(from.x,from.y,10+k*60,0,Math.PI*2);ctx.stroke();
    }else{
     for(let i=0;i<3;i++){
      const kk=Math.max(0,k-i*.15);
      ctx.strokeStyle=i%2?glow:c;ctx.lineWidth=move.width*.5*(1-kk);
      ctx.beginPath();ctx.ellipse(from.x,from.y+30,20+kk*box.width*.45,6+kk*box.height*.12,0,0,Math.PI*2);ctx.stroke();
     }
    }
    // Impact star at the target.
    const star=(1-k)*(18+move.width*2);
    ctx.fillStyle='#fff';ctx.shadowColor=c;ctx.shadowBlur=30;
    ctx.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4+k,r=i%2?star*.35:star;ctx.lineTo(to.x+Math.cos(a)*r,to.y+Math.sin(a)*r);}ctx.closePath();ctx.fill();
    if(k>.3&&rnd()<.35)spawn(to.x,to.y,4,180,move.accentHue);
   }
   // Particles live through charge, strike and the fade that follows.
   ctx.shadowBlur=8;
   for(const p of current.particles){
    p.life+=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vx*=.96;p.vy=p.vy*.96+30*dt;
    const a=Math.max(0,1-p.life/p.max);if(a<=0)continue;
    ctx.globalAlpha=a;ctx.fillStyle=`hsl(${p.hue} 100% 66%)`;ctx.shadowColor=ctx.fillStyle;
    ctx.beginPath();ctx.arc(p.x,p.y,p.size*(.6+a*.6),0,Math.PI*2);ctx.fill();
   }
   ctx.globalAlpha=1;
   current.particles=current.particles.filter(p=>p.life<p.max);
   if(t<charge+strike+700){frame=requestAnimationFrame(loop);return;}
   ctx.clearRect(0,0,box.width,box.height);
   node.style.setProperty('--charge','1');
   fx.current=null;busy.current=false;setPhase('idle');
  };
  frame=requestAnimationFrame(loop);
  return()=>cancelAnimationFrame(frame);
 },[phase==='idle']);// eslint-disable-line react-hooks/exhaustive-deps

 // Self-started attacks on a seeded timer while the habitat is on screen.
 useEffect(()=>{
  if(!moveset||!visible||reduced)return;
  let timer=0;
  const arm=()=>{timer=window.setTimeout(()=>{attack('timer');arm();},nextAttackDelay(moveset,counter.current));};
  timer=window.setTimeout(()=>{attack('timer');arm();},1800);
  return()=>window.clearTimeout(timer);
 },[moveset,visible,reduced,attack]);

 // Chat events: a new line in the shared care chat, or an explicit beastbox:beast-chat event.
 const chatCount=Array.isArray(session?.chat)?session.chat.length:0;
 const lastChat=useRef<number|null>(null);
 useEffect(()=>{
  if(lastChat.current!==null&&chatCount>lastChat.current)attack('chat');
  lastChat.current=chatCount;
 },[chatCount,attack]);
 useEffect(()=>{
  const onChat=()=>attack('chat');
  window.addEventListener('beastbox:beast-chat',onChat);
  return()=>window.removeEventListener('beastbox:beast-chat',onChat);
 },[attack]);

 // Idle voice: an occasional chirp in the beast's own generated voice once sound is on.
 useEffect(()=>{
  if(!sound||!visible)return;
  const clock=window.setInterval(()=>{if(!busy.current)window.dispatchEvent(new CustomEvent('beastbox:spark-chirp',{detail:{channel:'habitat',intensity:.55}}));},9000);
  return()=>window.clearInterval(clock);
 },[sound,visible]);

 useEffect(()=>{
  if(!toast)return;
  const id=window.setTimeout(()=>setToast(null),1800);
  return()=>window.clearTimeout(id);
 },[toast]);

 useEffect(()=>()=>{void audio.current?.close().catch(()=>{});},[]);

 function setSoundOn(next:boolean){
  soundRef.current=next;setSound(next);
  if(next)void ensureAudio();
 }
 function onTap(){
  // Browser autoplay rules: the first tap is the user gesture that wakes the voice.
  if(!soundRef.current&&!userMuted.current)setSoundOn(true);
  attack('tap');
 }

 return <div ref={root} className={styles.arena} data-beast-arena="true" data-phase={phase}
   data-attack-style={fx.current?.move.style||'none'} data-reduced-motion={reduced} data-sound={sound?'on':'off'}>
  <SparkBeastCompanion profile={profile} fallbackLook={fallbackLook} state={state} audioChannel="habitat"
   onGenome={onGenome} label={label}/>
  <canvas ref={fxCanvas} className={styles.fx} aria-hidden="true"/>
  <div ref={flash} className={styles.flash} aria-hidden="true"/>
  <button type="button" className={styles.hit} onClick={onTap} disabled={!moveset}
   aria-label={`Tap ${name} to attack`}/>
  <div className={styles.tools}>
   <button type="button" className={styles.tool} aria-pressed={sound}
    aria-label={sound?'Mute the habitat beast':'Turn on the habitat beast sound'}
    onClick={()=>{const next=!sound;userMuted.current=!next;setSoundOn(next);}}>
    {sound?<Volume2 size={14}/>:<VolumeX size={14}/>}<span>{sound?'Sound on':'Sound off'}</span>
   </button>
   <button type="button" className={styles.tool} onClick={onTap} disabled={!moveset} aria-label="Make the beast attack">
    <Zap size={14}/><span>Attack</span>
   </button>
  </div>
  <p className={styles.toast} role="status" aria-live="polite" data-move-toast="true" data-crit={toast?.crit?'true':undefined} key={toast?.id??'none'}>
   {toast?<><strong>{toast.text}</strong>{toast.crit?<em> Critical!</em>:null}<small>Seeded move · recorded IBM counts, no live quantum link</small></>:null}
  </p>
 </div>;
}
