/** Open Field perception: on-device camera/mic summaries for Zeref. Classical signal
 * processing only (no model, no images or audio kept). Only small numbers leave this module. */
export const PERCEPTION_SCHEMA='beastbox-field-perception-v1';
export const LOG_KEY='beastbox.fieldPerception.v1';
export const NUMERIC_KEYS=['t','brightness','hue','motion','gazeX','gazeY','loudness','pitchHz'];
const r2=n=>Math.round((Number.isFinite(n)?n:0)*100)/100;
/** rgba pixels (w*h*4) -> brightness 0..1, dominant hue 0..360, motion 0..1 vs prev, motion centroid -1..1 */
export function analyzeFrame(px,prev,w,h){
 let sum=0,rs=0,gs=0,bs=0,mot=0,mx=0,my=0;const n=w*h,gray=new Float32Array(n);
 for(let i=0;i<n;i++){const r=px[i*4],g=px[i*4+1],b=px[i*4+2];const y=(.299*r+.587*g+.114*b)/255;gray[i]=y;sum+=y;rs+=r;gs+=g;bs+=b;
  if(prev){const d=Math.abs(y-prev[i]);if(d>.12){mot++;mx+=(i%w)/w;my+=Math.floor(i/w)/h;}}}
 const R=rs/n,G=gs/n,B=bs/n,max=Math.max(R,G,B),min=Math.min(R,G,B);let hue=0;
 if(max>min){hue=max===R?60*(((G-B)/(max-min))%6):max===G?60*((B-R)/(max-min)+2):60*((R-G)/(max-min)+4);if(hue<0)hue+=360;}
 return {gray,brightness:r2(sum/n),hue:Math.round(hue),motion:r2(mot/n),gazeX:mot?r2(mx/mot*2-1):0,gazeY:mot?r2(my/mot*2-1):0};
}
/** time-domain samples -1..1 -> loudness 0..1 (RMS) + rough pitch via autocorrelation */
export function analyzeAudio(buf,sampleRate=48000){
 let s=0;for(const v of buf)s+=v*v;const rms=Math.sqrt(s/Math.max(1,buf.length));
 let best=0,lag=0;const lo=Math.floor(sampleRate/1000),hi=Math.min(buf.length>>1,Math.floor(sampleRate/70));
 if(rms>.01)for(let L=lo;L<hi;L++){let c=0;for(let i=0;i+L<buf.length;i+=2)c+=buf[i]*buf[i+L];if(c>best){best=c;lag=L;}}
 return {loudness:r2(Math.min(1,rms*4)),pitchHz:lag?Math.round(sampleRate/lag):0};
}
/** What Zeref notices + how he feels about it. Returns null if nothing notable. */
export function notice(p,prev){
 if(!p)return null;
 if(p.loudness>.6&&(!prev||prev.loudness<.4))return {event:'a loud sound',emotion:'fear'};
 if(p.motion>.08)return {event:p.gazeX<-.3?'something moving to the left':p.gazeX>.3?'something moving to the right':'something moving in front of him',emotion:'curiosity'};
 if(prev&&prev.brightness-p.brightness>.25)return {event:'the lights going dark',emotion:'fear'};
 if(prev&&p.brightness-prev.brightness>.25)return {event:'the lights getting bright',emotion:'joy'};
 if(p.pitchHz>150&&p.pitchHz<1000&&p.loudness>.15&&p.loudness<.6)return {event:'someone humming or talking',emotion:'joy'};
 return null;
}
/** Compact numeric-only experience record. Anything non-numeric is dropped. */
export function experience(p,now){
 const o={t:Math.floor(Number(now)||0)};for(const k of NUMERIC_KEYS.slice(1))o[k]=r2(Number(p?.[k]));return o;
}
export function isNumericExperience(o){
 return !!o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).every(k=>NUMERIC_KEYS.includes(k))&&Object.values(o).every(v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<1e13);
}
export function noticePrompt(n){return `You just noticed ${n.event} in the real room through the Open Field sensors. React in your own words.`.slice(0,380);}
