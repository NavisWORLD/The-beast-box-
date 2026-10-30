'use client';
// /universe without a GPU: a light 2D drawing of the same ground view as /beast-cage/world (same one-sun clock, pack sky stops,
// far ridges and the volcano world). SEEDED placement, labelled as a drawing; no random calls.
import {useEffect,useRef} from 'react';
import {oneSunAt,skyAtElevation} from '@/lib/universe/one-sun.mjs';
const RIDGES=[{crest:1.99,hex:'#A7B6C1'},{crest:2.07,hex:'#8FA1A7'},{crest:2.24,hex:'#819393'},{crest:2.27,hex:'#6A7864'}];
const s8=(l:number)=>Math.round(255*Math.max(0,Math.min(1,l<=.0031308?12.92*l:1.055*Math.pow(l,1/2.4)-.055)));
const css=(c:number[])=>`rgb(${s8(c[0])},${s8(c[1])},${s8(c[2])})`;
const hash=(s:string)=>{let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0)/4294967296;};
export default function SeededLand2D({seed}:{seed:string}){const ref=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{const cv=ref.current;if(!cv)return;const x=cv.getContext('2d');if(!x)return;let id=0;
  const draw=()=>{const W=cv.width,H=cv.height,hz=H*.62;const o=oneSunAt(Date.now()/1000,[0,1,0]);const sk=skyAtElevation(o.elevationDeg);const day=o.day;
   const g=x.createLinearGradient(0,0,0,hz);g.addColorStop(0,day>0?'#437E9E':css(sk.zenith));g.addColorStop(.45,css(sk.zenith.map((z:number,i:number)=>(z+sk.horizon[i])/2)));g.addColorStop(1,css(sk.horizon));x.fillStyle=g;x.fillRect(0,0,W,hz);
   const sy=hz-(o.elevationDeg/40)*hz,sx=W*.35;if(o.elevationDeg>-2){const sg=x.createRadialGradient(sx,sy,0,sx,sy,W*.18);sg.addColorStop(0,'rgba(255,240,205,.9)');sg.addColorStop(1,'rgba(255,224,180,0)');x.fillStyle=sg;x.fillRect(0,0,W,hz);x.fillStyle='#FFF6E0';x.beginPath();x.arc(sx,sy,W*.018,0,7);x.fill();}
   const vx=sx+W*.54*(54/90),vy=hz-(30.4/40)*hz,vr=W*.06;x.fillStyle='#B5532E';x.beginPath();x.arc(vx,vy,vr,0,7);x.fill();x.fillStyle=day>0?'rgba(30,10,5,.35)':'rgba(255,122,46,.35)';x.beginPath();x.arc(vx+vr*.35,vy,vr*.8,-1.6,1.6);x.fill();
   RIDGES.forEach((r,k)=>{const p=hash(seed+':r'+k)*6.28;x.fillStyle=r.hex;x.beginPath();x.moveTo(0,H);for(let i=0;i<=W;i+=4){const a=i/W*6.28;x.lineTo(i,hz-(r.crest*.012*H)*(1.5+k*.8)*(.6+.3*Math.sin(a*(3+k)+p)+.1*Math.sin(a*11+p*2)));}x.lineTo(W,H);x.fill();});
   const gg=x.createLinearGradient(0,hz,0,H);gg.addColorStop(0,'#6E7F49');gg.addColorStop(1,'#3A4127');x.fillStyle=gg;x.fillRect(0,hz+2,W,H-hz);
   const t=Date.now()/1000;x.lineWidth=1.2;for(let i=0;i<220;i++){const u=hash(seed+':g'+i),v=hash(seed+':h'+i);const bx=u*W,by=hz+8+v*v*(H-hz-8),L=4+v*14,sw=Math.sin(t*1.3+u*20)*L*.25;x.strokeStyle=v>.5?'#8B9B55':'#5F6B40';x.beginPath();x.moveTo(bx,by);x.lineTo(bx+sw,by-L);x.stroke();}
   id=window.setTimeout(()=>requestAnimationFrame(draw),400);};
  draw();return ()=>clearTimeout(id);},[seed]);
 return <figure data-seeded-land-2d style={{position:'absolute',top:64,right:10,width:'min(46vw,300px)',margin:0,zIndex:2,borderRadius:10,overflow:'hidden',boxShadow:'0 4px 18px rgba(0,0,0,.4)'}}>
  <canvas ref={ref} width={300} height={170} style={{width:'100%',display:'block'}}/>
  <figcaption style={{fontSize:11,padding:'4px 8px',background:'rgba(15,23,42,.85)',color:'#e2e8f0'}}>2D drawing · SEEDED, same seed and sun clock as /beast-cage/world (no GPU here, so no 3D)</figcaption></figure>;}
