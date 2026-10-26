// Browser sensors for the consent panel (sound level, device motion, camera light). Each channel is started only if the person ticked it; a refused or missing sensor
// reports 'denied'/'unavailable' and never a value. Only a single number per channel leaves this file: no audio, no frames, no waveform.
import type {EnvChannel} from './environment-link.mjs';
export type Want={light:boolean;sound:boolean;motion:boolean};
export type Sample={light:EnvChannel;sound:EnvChannel;motion:EnvChannel};
const off:EnvChannel={state:'off'};
const meas=(level:number,source?:string):EnvChannel=>({state:'MEASURED',level:Math.max(0,Math.min(1,level)),...(source?{source}:{})});
type Cleanup=()=>void;
export async function startSensors(want:Want,onSample:(s:Sample)=>void):Promise<{stop:Cleanup;initial:Sample}>{
 const cur:Sample={light:off,sound:off,motion:off};const cleanups:Cleanup[]=[];
 const push=()=>onSample({...cur});
 const denied=(e:unknown):EnvChannel=>({state:/NotAllowed|Permission|Security/i.test(String((e as Error)?.name||e))?'denied':'unavailable'});
 if(want.sound){
  try{const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false}});
   const Ctx=(window.AudioContext||(window as any).webkitAudioContext);const ctx=new Ctx();const an=ctx.createAnalyser();an.fftSize=512;ctx.createMediaStreamSource(stream).connect(an);
   const buf=new Float32Array(an.fftSize);const id=window.setInterval(()=>{an.getFloatTimeDomainData(buf);let s=0;for(const v of buf)s+=v*v;cur.sound=meas(Math.min(1,Math.sqrt(s/buf.length)*4));buf.fill(0);},1000);
   cleanups.push(()=>{clearInterval(id);stream.getTracks().forEach(t=>t.stop());void ctx.close();});}
  catch(e){cur.sound=denied(e);}
 }
 if(want.motion){
  try{const DM:any=(window as any).DeviceMotionEvent;if(!DM)throw new Error('unavailable');
   if(typeof DM.requestPermission==='function'&&(await DM.requestPermission())!=='granted'){cur.motion={state:'denied'};}
   else{let level:number|null=null;const on=(e:DeviceMotionEvent)=>{const a=e.acceleration,g=e.accelerationIncludingGravity;
     const m=a&&a.x!==null?Math.hypot(a.x||0,a.y||0,a.z||0):g&&g.x!==null?Math.abs(Math.hypot(g.x||0,g.y||0,g.z||0)-9.81):null;if(m!==null)level=Math.min(1,m/8);};
    window.addEventListener('devicemotion',on);const id=window.setInterval(()=>{cur.motion=level===null?{state:'unavailable'}:meas(level);},1000);cleanups.push(()=>{window.removeEventListener('devicemotion',on);clearInterval(id);});cur.motion={state:'unavailable'};}}
  catch(e){cur.motion=denied(e);}
 }
 if(want.light){// Light is the camera's brightness: ONE number from a tiny canvas; frames are never kept. The caller only asks for it while the camera switch is on and no pulse is being read (the camera does one job at a time).
  try{const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:64,height:48}});const v=document.createElement('video');v.muted=true;v.playsInline=true;v.srcObject=stream;await v.play();
   const c=document.createElement('canvas');c.width=8;c.height=6;const g=c.getContext('2d',{willReadFrequently:true});
   const id=window.setInterval(()=>{if(!g)return;g.drawImage(v,0,0,8,6);const d=g.getImageData(0,0,8,6).data;let t=0;for(let i=0;i<d.length;i+=4)t+=(d[i]+d[i+1]+d[i+2])/3;cur.light=meas(t/(d.length/4)/255,'camera-brightness');g.clearRect(0,0,8,6);},1000);
   cleanups.push(()=>{clearInterval(id);stream.getTracks().forEach(t=>t.stop());v.srcObject=null;});cur.light={state:'unavailable'};}
  catch(e){cur.light=denied(e);}
 }
 push();const tick=window.setInterval(push,1000);cleanups.push(()=>clearInterval(tick));
 return {initial:{...cur},stop:()=>{cleanups.forEach(f=>{try{f();}catch{}});}};
}
