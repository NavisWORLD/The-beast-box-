// Real IBM Bio Connection: on-device capture. Camera frames and microphone samples are reduced to NUMBERS in memory
// and the buffers are dropped when the measurement ends. Nothing here uploads, stores or publishes raw media.
import {analysePpg,PPG_RULES,type PpgResult} from './ppg.mjs';
export type Light={red_mean:number;green_mean:number;blue_mean:number;red_ac_dc:number};
export type AudioFeatures={enabled:boolean;rms_mean:number;zcr:number;centroid_norm:number};
export type Progress={elapsed_s:number;total_s:number;finger:boolean;red:number;provisional_bpm:number|null;torch:'on'|'requested'|'unavailable'};
export type Measurement={ppg:PpgResult;light:Light;audio:AudioFeatures|null;torch:Progress['torch']};
export const MEASURE_SECONDS=30;
const SIZE=24;
const mean=(a:number[])=>a.length?a.reduce((s,x)=>s+x,0)/a.length:0;
/** Start fingertip PPG. Resolves with numbers only. `signal` aborts and releases the camera/torch/mic. */
export async function measureFingertip(opts:{withMic:boolean;onProgress:(p:Progress)=>void;signal:AbortSignal;seconds?:number}):Promise<Measurement>{
 const total=opts.seconds||MEASURE_SECONDS;
 if(typeof window==='undefined'||!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)throw new Error('Camera needs a secure (https) page in a browser with camera access.');
 let cam:MediaStream|null=null,mic:MediaStream|null=null,audioCtx:AudioContext|null=null,video:HTMLVideoElement|null=null;
 let torch:Progress['torch']='unavailable';
 let t:number[]=[],r:number[]=[],g:number[]=[],b:number[]=[];
 const au={rms:[] as number[],zcr:[] as number[],cen:[] as number[]};
 const release=()=>{try{cam?.getTracks().forEach(x=>{try{x.stop();}catch{}});}catch{}try{mic?.getTracks().forEach(x=>x.stop());}catch{}try{void audioCtx?.close();}catch{}if(video){video.srcObject=null;video.remove();}};
 try{
  cam=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:160},height:{ideal:120},frameRate:{ideal:30,min:15}},audio:false});
  const track=cam.getVideoTracks()[0];
  try{await track.applyConstraints({advanced:[{torch:true} as MediaTrackConstraintSet]});torch='requested';}catch{torch='unavailable';}
  video=document.createElement('video');video.setAttribute('playsinline','true');video.muted=true;video.style.cssText='position:fixed;width:1px;height:1px;opacity:0;pointer-events:none;left:-9px';document.body.appendChild(video);video.srcObject=cam;await video.play();
  const cv=document.createElement('canvas');cv.width=SIZE;cv.height=SIZE;const cx=cv.getContext('2d',{willReadFrequently:true});if(!cx)throw new Error('Canvas unavailable.');
  let analyser:AnalyserNode|null=null,td:Float32Array<ArrayBuffer>|null=null,fd:Uint8Array<ArrayBuffer>|null=null;
  if(opts.withMic){
   try{mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
    const AC=window.AudioContext||(window as unknown as {webkitAudioContext:typeof AudioContext}).webkitAudioContext;audioCtx=new AC();await audioCtx.resume();
    analyser=audioCtx.createAnalyser();analyser.fftSize=1024;audioCtx.createMediaStreamSource(mic).connect(analyser);td=new Float32Array(analyser.fftSize);fd=new Uint8Array(analyser.frequencyBinCount);
   }catch{analyser=null;}
  }
  const t0=performance.now();let lastUi=0,lastAu=0,done=false;
  const sampleAudio=(now:number)=>{if(!analyser||!td||!fd||now-lastAu<100)return;lastAu=now;analyser.getFloatTimeDomainData(td);let s=0,z=0;for(let i=0;i<td.length;i++){s+=td[i]*td[i];if(i&&(td[i]>=0)!==(td[i-1]>=0))z++;}au.rms.push(Math.min(1,Math.sqrt(s/td.length)*4));au.zcr.push(z/td.length);analyser.getByteFrequencyData(fd);let num=0,den=0;for(let i=0;i<fd.length;i++){num+=i*fd[i];den+=fd[i];}au.cen.push(den>0?num/den/fd.length:0);};
  const grab=(now:number)=>{cx.drawImage(video!,0,0,SIZE,SIZE);const d=cx.getImageData(4,4,SIZE-8,SIZE-8).data;let sr=0,sg=0,sb=0,n=0;for(let i=0;i<d.length;i+=4){sr+=d[i];sg+=d[i+1];sb+=d[i+2];n++;}t.push(now);r.push(sr/n);g.push(sg/n);b.push(sb/n);};
  await new Promise<void>((resolve,reject)=>{
   const onAbort=()=>{done=true;reject(new DOMException('Measurement cancelled','AbortError'));};
   if(opts.signal.aborted)return onAbort();opts.signal.addEventListener('abort',onAbort,{once:true});
   const tick=(now:number)=>{
    if(done)return;
    const el=(now-t0)/1000;grab(now);sampleAudio(now);
    if(now-lastUi>500){lastUi=now;const rr=r.length?r[r.length-1]:0,gg=g.length?g[g.length-1]:0;
     const finger=rr>=PPG_RULES.min_red&&rr-gg>=PPG_RULES.min_red_minus_green;
     let prov:number|null=null;if(el>=14&&finger){const a=analysePpg({t,v:r,g},{...PPG_RULES,min_duration_s:6,min_beats:6,min_sqi:.4});prov=a.bpm!==null&&a.sqi>=.4?Math.round(a.bpm):null;}
     opts.onProgress({elapsed_s:Math.min(total,el),total_s:total,finger,red:Math.round(rr),provisional_bpm:prov,torch});}
    if(el>=total){done=true;opts.signal.removeEventListener('abort',onAbort);resolve();return;}
    const v=video as HTMLVideoElement&{requestVideoFrameCallback?:(cb:(n:number)=>void)=>number};
    if(v.requestVideoFrameCallback)v.requestVideoFrameCallback(n=>tick(performance.now()||n));else requestAnimationFrame(tick);};
   const v0=video as HTMLVideoElement&{requestVideoFrameCallback?:(cb:(n:number)=>void)=>number};
   if(v0.requestVideoFrameCallback)v0.requestVideoFrameCallback(()=>tick(performance.now()));else requestAnimationFrame(tick);
  });
  const ppg=analysePpg({t,v:r,g});
  const lightRaw={red_mean:mean(r),green_mean:mean(g),blue_mean:mean(b),red_ac_dc:ppg.red_ac_dc??0};
  const audio:AudioFeatures|null=opts.withMic&&au.rms.length>20?{enabled:true,rms_mean:mean(au.rms),zcr:mean(au.zcr),centroid_norm:mean(au.cen)}:null;
  return {ppg,light:lightRaw,audio,torch};
 }finally{t=[];r=[];g=[];b=[];au.rms.length=0;au.zcr.length=0;au.cen.length=0;release();}
}
/** SHA-256 hex with WebCrypto (async). */
export async function sha256Hex(s:string):Promise<string>{const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('');}
