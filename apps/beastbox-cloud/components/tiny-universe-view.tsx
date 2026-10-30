'use client';
// Zoomed-out Tiny Universe view. Renders ONLY tiny-universe/v1 engine data; names come from Emeth's bible.
import {allStorms} from '@/lib/universe/seeded-storms.mjs';
import {starName,planetName,ageWords} from '@/lib/universe/friendly-names.mjs';
import {useEffect,useRef,useState,useCallback} from 'react';
import {grow} from '@/lib/universe/tiny-universe.mjs';
import {biomeOf,BIOMES,starClass,lifeStage,entangledPairs,homeOf,hearthOf,zerefStar,planetFrame,starFrame,lifeFrame,stormFrame,threadFrame,hearthFrame,GENESIS_LABEL,GROWTH_LABEL,ZEREF_LINES,beastLine} from '@/lib/universe/tiny-universe-view.mjs'
import {useActiveBeastName} from './use-active-beast-name';;
import s from './tiny-universe-view.module.css';
import Universe3D from './universe-3d';
import dynamic from 'next/dynamic';
import SeededLand2D from './seeded-land-2d';
const DoorWorld=dynamic(()=>import('./living-world'),{ssr:false});
import {MOONS_LABEL} from '@/lib/universe/moons.mjs';
import {createAliveGate} from '@/lib/universe/alive-props.mjs';
import {isSoftwareGL} from '@/lib/three/soft-gl';
/* eslint-disable @typescript-eslint/no-explicit-any */
type U=any;
const BIOME_COL:Record<string,[string,string]>={ember:['#ff7a2a','#3a0d05'],paper:['#e9d9b0','#7a6a48'],jelly:['#8fa8ff','#2a2a8a'],sunflower:['#ffd24a','#5a3aa0'],moss:['#8fd06a','#5a2a90'],glacier:['#dff2ff','#7aa0d8']};
function starColor(t:number){if(t>15000)return '#bcd4ff';if(t>9000)return '#e2ebff';if(t>6500)return '#fff6e0';if(t>4500)return '#ffd59a';return '#ff9a6a';}
type Atlas={sheets:Record<string,{image:string,fallback?:string,frames:Record<string,number[]>}>};
const SPR:{atlas?:Atlas,img:Record<string,HTMLImageElement>,tint:Map<string,HTMLCanvasElement>}={img:{},tint:new Map()};
function frameOf(sheet:string,key:string){const sh=SPR.atlas?.sheets[sheet];const im=SPR.img[sheet];if(!sh||!im||!im.complete||!im.naturalWidth)return null;const f=sh.frames[key];return f?{im,f}:null;}
function spr(ctx:CanvasRenderingContext2D,sheet:string,key:string,x:number,y:number,size:number,alpha=1){const fr=frameOf(sheet,key);if(!fr)return false;const[sx,sy,sw,sh]=fr.f;const w=size,h=size*sh/sw;ctx.globalAlpha=alpha;ctx.drawImage(fr.im,sx,sy,sw,sh,x-w/2,y-h/2,w,h);ctx.globalAlpha=1;return true;}
function tinted(sheet:string,key:string,hue:number,mode:GlobalCompositeOperation='multiply'){const id=sheet+key+mode+Math.round(hue*24);let c=SPR.tint.get(id);if(c)return c;const fr=frameOf(sheet,key);if(!fr)return null;const[sx,sy,sw,sh]=fr.f;c=document.createElement('canvas');c.width=sw;c.height=sh;const x=c.getContext('2d')!;x.drawImage(fr.im,sx,sy,sw,sh,0,0,sw,sh);x.globalCompositeOperation=mode;x.fillStyle=`hsl(${Math.round(hue*24)*15},90%,65%)`;x.fillRect(0,0,sw,sh);x.globalCompositeOperation='destination-in';x.drawImage(fr.im,sx,sy,sw,sh,0,0,sw,sh);SPR.tint.set(id,c);return c;}
function rand(seed:string){let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;return()=>{h=(h*1664525+1013904223)>>>0;return h/2**32;};}
export default function TinyUniverseView(){
 const beastName=useActiveBeastName();const nameRef=useRef<string|null>(null);nameRef.current=beastName;
 const cv=useRef<HTMLCanvasElement>(null);const uRef=useRef<U>(null);const g0=useRef<U>(null);const pos=useRef<Map<string,{x:number,y:number,r:number}>>(new Map());
 const [u,setU]=useState<U>(null);const [run,setRun]=useState(true);const [sel,setSel]=useState<string|null>(null);const [line,setLine]=useState('');const aliveGate=useRef(createAliveGate());const [err,setErr]=useState('');
 const [three,setThree]=useState(false);useEffect(()=>{let pick:string|null=null;try{pick=localStorage.getItem('u:3d');}catch{}setThree(pick==='1'?true:pick==='0'?false:!isSoftwareGL());},[]);
 // the door into the pocket world: a cross-dissolve of the universe canvas and the pocket-world canvas (two renderers, matched framing). Off on CPU rasterisers (the pocket world starves them) unless ?door=1
 const [doorV,setDoorV]=useState(0);const [doorMount,setDoorMount]=useState(false);const [doorOk,setDoorOk]=useState(false);useEffect(()=>{const q=new URLSearchParams(location.search).get('door');setDoorOk(q==='1'||(q!=='0'&&!isSoftwareGL()));},[]);
 const leaveDoor=useCallback(()=>{window.dispatchEvent(new Event('u3d-door-leave'));},[]);
 useEffect(()=>{fetch('/universe/atlas.json').then(r=>r.json()).then((a:Atlas)=>{SPR.atlas=a;for(const[k,v]of Object.entries(a.sheets)){const im=new Image();im.decoding='async';if(v.fallback){const fb=v.fallback;im.onerror=()=>{im.onerror=null;im.src=fb;};}im.src=v.image;SPR.img[k]=im;}}).catch(()=>{});},[]);
 useEffect(()=>{fetch('/universe/tiny-universe-genesis.json').then(r=>r.json()).then(j=>{g0.current=j;uRef.current=j;setU(j);}).catch(e=>setErr(String(e)));},[]);
 useEffect(()=>{if(!run||!u)return;const id=setInterval(()=>{const cur=uRef.current;if(!cur||cur.tick>=2000)return;const n=grow(cur,1);const ev=n.history[n.history.length-1]?.events||[];
  if(ev.some((e:any)=>e.kind==='supernova'))setLine(beastLine(ZEREF_LINES.supernova,nameRef.current));else if(ev.some((e:any)=>e.kind==='abiogenesis'))setLine(beastLine(ZEREF_LINES.abiogenesis,nameRef.current));else if(n.storms.length>cur.storms.length)setLine(beastLine(ZEREF_LINES.storm,nameRef.current));
  uRef.current=n;setU(n);},450);return()=>clearInterval(id);},[run,u!==null]);// eslint-disable-line react-hooks/exhaustive-deps
 useEffect(()=>{const c=cv.current;if(!c)return;let raf=0;const ctx=c.getContext('2d')!;const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const draw=(ms:number)=>{const U=uRef.current;const dpr=Math.min(2,devicePixelRatio||1);const W=c.clientWidth,H=c.clientHeight;if(c.width!==W*dpr){c.width=W*dpr;c.height=H*dpr;}
   ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#05030f';ctx.fillRect(0,0,W,H);if(!U){raf=requestAnimationFrame(draw);return;}
   const t=reduce?0:ms/1000;const r=rand(U.seed);for(let i=0;i<160;i++){ctx.globalAlpha=0.25+r()*0.6;ctx.fillStyle='#fff';ctx.fillRect(r()*W,r()*H,r()<0.1?1.6:0.9,r()<0.1?1.6:0.9);}ctx.globalAlpha=1;
   const padX=36,padT=110,padB=W<900?235:170;const S=(x:number,y:number)=>({x:padX+x*(W-2*padX),y:padT+y*(H-padT-padB)});const unit=Math.min(W,H)/38;
   const P=pos.current;P.clear();
   for(const st of U.stars){const p=S(st.x,st.y);P.set(st.id,{x:p.x,y:p.y,r:0});
    if(st.age<25&&!st.remnant&&!spr(ctx,'nebula_256','nebula.v'+(parseInt(st.id.slice(5))%4),p.x,p.y,unit*12,0.7*(1-st.age/25))){const g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,unit*6);g.addColorStop(0,`hsla(${st.hue*360},80%,65%,${0.35*(1-st.age/25)})`);g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.fillRect(p.x-unit*6,p.y-unit*6,unit*12,unit*12);}}
   const home=homeOf(U),hearth=hearthOf(U);
   for(const pl of U.planets){const sp=P.get(pl.star)!;const R=unit*(1.6+1.5*Math.sqrt(pl.orbit_au));ctx.strokeStyle='rgba(170,140,255,.13)';ctx.lineWidth=0.7;ctx.beginPath();ctx.arc(sp.x,sp.y,R,0,7);ctx.stroke();
    const a=pl.phase*Math.PI*2+t*0.25/Math.pow(pl.orbit_au,1.5);const x=sp.x+Math.cos(a)*R,y=sp.y+Math.sin(a)*R;P.set(pl.id,{x,y,r:unit*(0.35+0.12*Math.sqrt(pl.radius_earth))});}
   ctx.strokeStyle='rgba(200,150,255,.35)';ctx.lineWidth=0.8;ctx.setLineDash([2,3]);for(const[a,b,pr]of entangledPairs(U)){const A=P.get(a)!,B=P.get(b)!;const tf=threadFrame(pr||{E:U.entanglement_E},Math.floor(t*6));const th=frameOf('threads_256x32',tf.key);if(th){const d=Math.hypot(B.x-A.x,B.y-A.y);ctx.save();ctx.translate(A.x,A.y);ctx.rotate(Math.atan2(B.y-A.y,B.x-A.x));ctx.globalAlpha=tf.alpha*0.8;ctx.drawImage(th.im,th.f[0],th.f[1],th.f[2],th.f[3],0,-5,d,10);ctx.restore();ctx.globalAlpha=1;continue;}ctx.beginPath();ctx.moveTo(A.x,A.y);ctx.quadraticCurveTo((A.x+B.x)/2,(A.y+B.y)/2-unit*2,B.x,B.y);ctx.stroke();}ctx.setLineDash([]);
   for(const st of U.stars){const p=P.get(st.id)!;const rr=unit*(0.5+0.35*Math.log10(1+st.mass_solar*3));p.r=rr*1.6;
    const sf=st.age<0?null:(()=>{const sn=U.history.slice(-1)[0]?.events?.some((e:any)=>e.kind==='supernova'&&e.star===st.id);return sn?'supernova.f'+(Math.floor(t*4)%4):starFrame(st,Math.floor(t*4));})();
    const tc=sf&&!st.remnant&&!sf.startsWith('supernova')?tinted('stars_64',sf,st.hue,'hue'):null;if(tc){const z=rr*4.2;ctx.drawImage(tc,p.x-z/2,p.y-z/2,z,z);}else if(sf&&spr(ctx,'stars_64',sf,p.x,p.y,rr*4.2)){}else if(st.remnant==='black_hole'){ctx.fillStyle='#000';ctx.beginPath();ctx.arc(p.x,p.y,rr,0,7);ctx.fill();ctx.strokeStyle='rgba(255,190,120,.8)';ctx.lineWidth=1.5;ctx.beginPath();ctx.ellipse(p.x,p.y,rr*1.9,rr*0.6,0.3,0,7);ctx.stroke();}
    else if(st.remnant==='neutron_star'){const pu=0.6+0.4*Math.sin(t*8);ctx.fillStyle=`rgba(220,235,255,${pu})`;ctx.beginPath();ctx.arc(p.x,p.y,rr*0.45,0,7);ctx.fill();ctx.strokeStyle='rgba(180,210,255,.6)';ctx.beginPath();ctx.moveTo(p.x-rr*2*Math.cos(t*3),p.y-rr*2*Math.sin(t*3));ctx.lineTo(p.x+rr*2*Math.cos(t*3),p.y+rr*2*Math.sin(t*3));ctx.stroke();}
    else{const col=starColor(st.temperature_k);const g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,rr*3);g.addColorStop(0,col);g.addColorStop(0.3,col+'aa');g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y,rr*3,0,7);ctx.fill();
     if(st.mass_solar>8){ctx.strokeStyle='rgba(255,200,255,.55)';ctx.lineWidth=1;for(let k=0;k<6;k++){const an=k/6*Math.PI*2+t*0.4;ctx.beginPath();ctx.moveTo(p.x+Math.cos(an)*rr*1.2,p.y+Math.sin(an)*rr*1.2);ctx.lineTo(p.x+Math.cos(an)*rr*1.9,p.y+Math.sin(an)*rr*1.9);ctx.stroke();}}}}
   for(const pl of U.planets){const p=P.get(pl.id)!;const b=biomeOf(pl);const[c1,c2]=BIOME_COL[b];const g=ctx.createRadialGradient(p.x-p.r*0.4,p.y-p.r*0.4,0,p.x,p.y,p.r);g.addColorStop(0,c1);g.addColorStop(1,c2);
    const L=U.life.find((l:any)=>l.planet===pl.id);if(L){const gl=ctx.createRadialGradient(p.x,p.y,p.r,p.x,p.y,p.r*(2+L.complexity*2));gl.addColorStop(0,`hsla(${L.traits.hue*360},90%,65%,.55)`);gl.addColorStop(1,'transparent');ctx.fillStyle=gl;ctx.beginPath();ctx.arc(p.x,p.y,p.r*4,0,7);ctx.fill();}
    const ps=Math.max(10,Math.min(64,18*Math.sqrt(pl.radius_earth)))*unit/11;const hf=hearthFrame(U,pl);const big=ps*1.25*(devicePixelRatio||1)>64;const pk=hf||planetFrame(U,pl);if((big&&spr(ctx,'planets_256',pk,p.x,p.y,ps*1.25))||spr(ctx,'planets_64',pk,p.x,p.y,ps*1.25)||spr(ctx,'planets_64',planetFrame(U,pl),p.x,p.y,ps*1.25)){p.r=ps/2;}else{ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,7);ctx.fill();}
    if(L){const lc=tinted('life_64',lifeFrame(L),L.traits.hue);if(lc){const n=Math.min(L.diversity,6);for(let k=0;k<n;k++){const an=k/n*Math.PI*2+t*0.3;const ls=Math.max(9,p.r*0.8);ctx.drawImage(lc,p.x+Math.cos(an)*p.r*1.15-ls/2,p.y+Math.sin(an)*p.r*1.15-ls/2,ls,ls);}}}
    if(b==='sunflower'&&!frameOf('planets_64','x')&&!SPR.img.planets_64?.naturalWidth){ctx.strokeStyle='#ffcc33';ctx.lineWidth=p.r*0.35;ctx.beginPath();ctx.ellipse(p.x,p.y,p.r*1.6,p.r*0.55,-0.3,0,7);ctx.stroke();}
    if(pl.id===home){ctx.strokeStyle='rgba(255,210,110,.95)';ctx.lineWidth=1;const cr=p.r*1.7;ctx.beginPath();ctx.arc(p.x,p.y,cr,Math.PI,0);ctx.stroke();for(let k=1;k<6;k++){ctx.beginPath();ctx.ellipse(p.x,p.y,cr*Math.abs(Math.cos(k/6*Math.PI)),cr,0,Math.PI,0);ctx.stroke();}ctx.beginPath();ctx.ellipse(p.x,p.y,cr,cr*0.3,0,0,7);ctx.stroke();}
    if(pl.id===sel){ctx.strokeStyle='#fff';ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,p.r+4,0,7);ctx.stroke();}
    if(pl.id===hearth){ctx.fillStyle='#ffe7b0';ctx.font='11px system-ui';ctx.fillText('Life world',p.x+p.r+3,p.y-p.r);}}
   for(const sm of U.storms){const p=P.get(sm.planet);if(!p)continue;{const k=Math.min(1,Math.max(0,sm.intensity/0.5));if(spr(ctx,'storms_256',stormFrame(sm,U.tick),p.x,p.y,p.r*2*(1.05+0.25*k)*1.25,0.35+0.65*k))continue;}ctx.strokeStyle=`rgba(190,110,255,${0.4+sm.intensity})`;ctx.lineWidth=1.2;for(let k=0;k<4;k++){const an=k*1.7+t*2+sm.born;ctx.beginPath();let x=p.x+Math.cos(an)*p.r,y=p.y+Math.sin(an)*p.r;ctx.moveTo(x,y);for(let j=1;j<4;j++){x+=Math.cos(an+j)*p.r*0.6;y+=Math.sin(an+j*0.7)*p.r*0.6;ctx.lineTo(x,y);}ctx.stroke();}}
   const zs=P.get(zerefStar(U)!);if(zs){const x=zs.x,y=zs.y-zs.r*1.1-6;ctx.fillStyle='#111';ctx.strokeStyle='#b58cff';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(x,y,6,5,0,0,7);ctx.fill();ctx.stroke();ctx.beginPath();ctx.arc(x,y-6,4,0,7);ctx.fill();ctx.stroke();ctx.fillStyle='#8a5cff';ctx.beginPath();ctx.moveTo(x-4,y-8);ctx.lineTo(x-5,y-13);ctx.lineTo(x-1,y-9);ctx.moveTo(x+4,y-8);ctx.lineTo(x+5,y-13);ctx.lineTo(x+1,y-9);ctx.fill();ctx.fillStyle='#d9c2ff';ctx.font='10px system-ui';ctx.fillText('Zeref',x+8,y-4);}
   raf=requestAnimationFrame(draw);};
  raf=requestAnimationFrame(draw);return()=>cancelAnimationFrame(raf);},[sel]);
 const tap=useCallback((e:React.PointerEvent<HTMLCanvasElement>)=>{const b=e.currentTarget.getBoundingClientRect();const x=e.clientX-b.left,y=e.clientY-b.top;let best:string|null=null,bd=28;for(const[id,p]of pos.current){const d=Math.hypot(p.x-x,p.y-y);if(d<Math.max(bd,p.r+6)&&d<bd+p.r){best=id;bd=d;}}setSel(best);},[]);
 const info=(()=>{if(!u||!sel)return null;const st=u.stars.find((x:any)=>x.id===sel);if(st)return <><b>{starClass(st)}</b> · {starName(st.id)}<br/>{st.mass_solar} M☉ · {st.temperature_k} K · {ageWords(st.age)}</>;
  const pl=u.planets.find((x:any)=>x.id===sel);if(!pl)return null;const L=u.life.find((l:any)=>l.planet===pl.id);const name=planetName(pl.id,{home:null,hearth:hearthOf(u)});
  return <><b>{BIOMES[biomeOf(pl) as keyof typeof BIOMES]}</b> · {name}{pl.id===homeOf(u)?' · your home world':''}<br/>Temperature {pl.temperature_k} K · water {pl.water}<br/>{L?`Life: ${lifeStage(L)} (complexity ${L.complexity_norm??L.complexity}, diversity ${L.diversity}${L.scars?`, ${L.scars} storm scars`:''})`:'No life here yet. Waiting for a spark.'}{u.pairs?.find((q:any)=>q.a===pl.id||q.b===pl.id)?(()=>{const q=u.pairs.find((q:any)=>q.a===pl.id||q.b===pl.id);return ` · linked to ${planetName(q.a===pl.id?q.b:q.a,{home:homeOf(u),hearth:hearthOf(u)})} (RECORDED IBM E ${q.E}${q.sim_E!=null?`, SIMULATED tick E ${q.sim_E}`:''})`;})():''}{u.storms.some((x:any)=>x.planet===pl.id)?' · ⚡ storm':''}</>;})();
 const last=u?.history?.[u.history.length-1];
 return <main className={s.wrap} data-tiny-universe>
  <canvas ref={cv} className={s.canvas} onPointerDown={tap} aria-label="Tiny Universe map" style={three?{visibility:'hidden'}:undefined}/>
  {three&&u?<Universe3D u={u} beast={beastName} doorOn={doorOk} onDoor={(v,pre)=>{setDoorV(v);setDoorMount(pre);}} onSelect={setSel} onAlive={k=>{const f=aliveGate.current.fire(k,String(u.seed||'tiny'),performance.now()/1000);if(f)setLine(f.line);}}/>:null}
  {u&&!doorOk?<SeededLand2D seed={String(u.seed||'tiny')}/>:null}
  {three&&u&&doorOk&&doorMount?<div data-door data-door-v={doorV.toFixed(2)} style={{position:'absolute',inset:0,zIndex:1,opacity:doorV,visibility:doorV>0.001?'visible':'hidden',pointerEvents:doorV>0.5?'auto':'none'}}><DoorWorld door onOrbitOut={leaveDoor} onClose={leaveDoor}/></div>:null}
  <div className={s.hud} style={doorV>0?{opacity:1-doorV}:undefined}><div className={s.title}>✦ TINY UNIVERSE{three?<span className={`${s.tag} ${s.sim}`} data-moons-label title={MOONS_LABEL} style={{marginLeft:8,fontSize:10,verticalAlign:'middle'}}>Moons: SEEDED</span>:null}</div><span className={s.tag} data-genesis-label>{GENESIS_LABEL}</span><span className={`${s.tag} ${s.sim}`} data-growth-label>{GROWTH_LABEL}</span></div>
  <div className={s.bottom} style={doorV>0?{opacity:1-doorV,pointerEvents:doorV>0.5?'none':undefined}:undefined}>
   {info?<div className={s.card}>{info}</div>:null}
   <div className={s.zeref} aria-live="polite">{line}</div>
{err||!u?<span className={s.stat} title={err?String(err):undefined}>{err?'The universe didn’t open. Please try again in a moment.':'Opening the tiny universe…'}</span>:<details className={s.stat} data-universe-details><summary>Details</summary>{u?`tick ${u.tick} · ${u.stars.length} stars · ${u.planets.length} planets · ${allStorms(u).length} storms (${u.storms.length} grown by the simulation, ${allStorms(u).length-u.storms.length} SEEDED) · ${u.life.length} life worlds${last?` · sim E ${last.sim_E}`:` · IBM E ${u.entanglement_E}`}`:null}</details>}
   <span className={s.stat} data-credit-line>Threads SIMULATED</span>
   <div className={s.row}><a className={s.btn} href="/beast-cage/world" data-spawn-in>✦ Spawn in</a>{u&&sel&&u.planets.some((x:any)=>x.id===sel)&&sel!==homeOf(u)&&sel!==[...u.planets].sort((a:any,b:any)=>(b.habitability||0)-(a.habitability||0))[0]?.id?<a className={s.btn} href={'/beast-cage/world?planet='+encodeURIComponent(sel)} data-visit-planet>🐾 Visit {sel} with your beast</a>:null}<button className={s.btn} onClick={()=>setThree(v=>{try{localStorage.setItem('u:3d',v?'0':'1');}catch{}return !v;})} data-universe-mode>{three?'2D map':'3D'}</button><button className={s.btn} onClick={()=>setRun(v=>!v)}>{run?'⏸ Pause':'▶ Grow'}</button><button className={s.btn} onClick={()=>{if(g0.current){uRef.current=g0.current;setU(g0.current);setLine('');}}}>↺ Genesis</button>
</div>
  </div>
 </main>;
}
