// Real IBM Bio Connection: fingertip photoplethysmography (PPG) on the device.
// Pure and deterministic: no DOM, no clock reads, no unseeded randomness. Input is the per-frame mean of the
// camera's red channel (and green, for finger detection) with each frame's time in milliseconds.
// Output is NUMBERS ONLY (bpm, HRV, signal quality). A pulse is reported MEASURED only when the signal passes
// the quality gate below; otherwise the result is {valid:false, reason} and nothing is made up.
export const PPG_RULES=Object.freeze({
  fs_hz:30,            // uniform resample rate
  settle_s:3,          // first seconds dropped (auto-exposure and torch settling)
  min_duration_s:20,   // analysed window must be at least this long
  min_beats:15,
  min_sqi:0.6,         // quality threshold for "MEASURED"
  min_bpm:40,max_bpm:200,
  min_red:90,          // fingertip over the lens with torch: red is bright
  min_red_minus_green:40,
  refractory_s:0.33,
  min_hrv_ibis:15,
});
const sum=a=>{let s=0;for(const x of a)s+=x;return s;};
const mean=a=>a.length?sum(a)/a.length:0;
const sd=a=>{if(a.length<2)return 0;const m=mean(a);let s=0;for(const x of a)s+=(x-m)*(x-m);return Math.sqrt(s/a.length);};
const median=a=>{if(!a.length)return 0;const b=[...a].sort((x,y)=>x-y);const n=b.length;return n%2?b[(n-1)/2]:(b[n/2-1]+b[n/2])/2;};
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const r4=x=>Math.round(x*1e4)/1e4;

/** Linear resample onto a uniform grid at fs Hz. t in ms (strictly increasing), v same length. */
export function resampleUniform(t,v,fs=PPG_RULES.fs_hz){
  const n=Math.min(t.length,v.length);if(n<2)return {x:[],fs};
  const t0=t[0],t1=t[n-1],dt=1000/fs,out=[];let j=0;
  for(let k=0;t0+k*dt<=t1;k++){const tk=t0+k*dt;while(j<n-2&&t[j+1]<tk)j++;const a=t[j],b=t[j+1],f=b>a?(tk-a)/(b-a):0;out.push(v[j]+(v[j+1]-v[j])*clamp(f,0,1));}
  return {x:out,fs};
}
function movingAverage(x,w){const n=x.length,out=new Array(n),h=Math.floor(w/2);let acc=0,lo=0,hi=-1;for(let i=0;i<n;i++){const a=Math.max(0,i-h),b=Math.min(n-1,i+h);while(hi<b){hi++;acc+=x[hi];}while(lo<a){acc-=x[lo];lo++;}out[i]=acc/(hi-lo+1);}return out;}
/** Remove slow drift (1 s moving average), smooth (about 0.13 s), invert so blood-volume peaks point up. */
export function conditionSignal(x,fs){const base=movingAverage(x,Math.round(fs*1.0)|1);const d=x.map((v,i)=>base[i]-v);return movingAverage(d,Math.max(3,Math.round(fs*.13)|1));}
/** Peak picking with an adaptive threshold and a refractory period (keeps the higher peak). */
export function findPeaks(s,fs,{refractory_s=PPG_RULES.refractory_s}={}){
  const thr=.25*sd(s),ref=Math.round(refractory_s*fs),peaks=[];
  for(let i=1;i<s.length-1;i++){if(s[i]>thr&&s[i]>=s[i-1]&&s[i]>s[i+1]){const last=peaks[peaks.length-1];if(last!==undefined&&i-last<ref){if(s[i]>s[last])peaks[peaks.length-1]=i;}else peaks.push(i);}}
  return peaks;
}
/** Sub-sample peak position by parabolic interpolation (deterministic). */
export function refinePeak(s,i){if(i<1||i>=s.length-1)return i;const a=s[i-1],b=s[i],c=s[i+1],d=a-2*b+c;return d<0?i+clamp(.5*(a-c)/d,-.5,.5):i;}
/** Normalised autocorrelation at lag; 1 = perfectly periodic. */
export function autocorr(s,lag){const n=s.length-lag;if(n<8)return 0;const m=mean(s);let num=0,d0=0,d1=0;for(let i=0;i<n;i++){const a=s[i]-m,b=s[i+lag]-m;num+=a*b;d0+=a*a;d1+=b*b;}return d0>0&&d1>0?num/Math.sqrt(d0*d1):0;}
/** Best period (seconds) in the allowed bpm range by autocorrelation; returns {period_s, strength}. */
export function acfPeriod(s,fs,{min_bpm=PPG_RULES.min_bpm,max_bpm=PPG_RULES.max_bpm}={}){
  const lo=Math.floor(fs*60/max_bpm),hi=Math.ceil(fs*60/min_bpm);let best=0,bl=0;
  for(let l=lo;l<=hi;l++){const a=autocorr(s,l);if(a>best){best=a;bl=l;}}
  if(bl>1){const a0=autocorr(s,bl-1),a2=autocorr(s,bl+1),den=a0-2*best+a2;if(den<0)return {period_s:(bl+clamp(.5*(a0-a2)/den,-.5,.5))/fs,strength:clamp(best,0,1)};}
  return {period_s:bl/fs,strength:clamp(best,0,1)};
}
/** Drop inter-beat intervals outside the bpm range or more than 30 percent from the local median. */
export function cleanIbis(ibisMs,{min_bpm=PPG_RULES.min_bpm,max_bpm=PPG_RULES.max_bpm}={}){
  const lo=60000/max_bpm,hi=60000/min_bpm,ok=ibisMs.filter(v=>v>=lo&&v<=hi);if(ok.length<3)return ok;
  const out=[];for(let i=0;i<ok.length;i++){const w=ok.slice(Math.max(0,i-4),Math.min(ok.length,i+5));const m=median(w);if(Math.abs(ok[i]-m)<=.3*m)out.push(ok[i]);}
  return out;
}
export function rmssd(ibis){if(ibis.length<2)return null;let s=0;for(let i=1;i<ibis.length;i++){const d=ibis[i]-ibis[i-1];s+=d*d;}return Math.sqrt(s/(ibis.length-1));}

/**
 * analysePpg({t,v,g?}) -> {valid, reason?, bpm, hrv_rmssd_ms, sqi, beats, duration_s, fs_hz, red_mean, green_mean, red_ac_dc}
 * t: ms timestamps, v: red-channel mean per frame, g: green-channel mean per frame (optional, finger check).
 * valid is true ONLY when a finger is detected, the window is long enough, and SQI passes the threshold.
 */
export function analysePpg({t,v,g=null},rules=PPG_RULES){
  const fail=(reason,extra={})=>({valid:false,reason,bpm:null,hrv_rmssd_ms:null,sqi:0,beats:0,duration_s:0,fs_hz:rules.fs_hz,...extra});
  if(!Array.isArray(t)||!Array.isArray(v)||t.length<rules.fs_hz*5||t.length!==v.length)return fail('too_few_frames');
  for(let i=1;i<t.length;i++)if(!(t[i]>t[i-1]))return fail('bad_timestamps');
  const i0=t.findIndex(x=>x-t[0]>=rules.settle_s*1000);if(i0<0)return fail('too_short');
  const T=t.slice(i0),V=v.slice(i0),G=g&&g.length===v.length?g.slice(i0):null;
  const red_mean=mean(V),green_mean=G?mean(G):null;
  if(!(red_mean>=rules.min_red)||(G&&!(red_mean-green_mean>=rules.min_red_minus_green)))return fail('no_finger',{red_mean:r4(red_mean),green_mean:green_mean===null?null:r4(green_mean)});
  const {x,fs}=resampleUniform(T,V,rules.fs_hz);const duration_s=x.length/fs;
  if(duration_s<rules.min_duration_s)return fail('too_short',{duration_s:r4(duration_s),red_mean:r4(red_mean)});
  const s=conditionSignal(x,fs);if(!(sd(s)>0))return fail('flat_signal',{red_mean:r4(red_mean)});
  const peaks=findPeaks(s,fs).map(i=>refinePeak(s,i));const rawIbis=[];for(let i=1;i<peaks.length;i++)rawIbis.push((peaks[i]-peaks[i-1])/fs*1000);
  const ibis=cleanIbis(rawIbis);
  const base={duration_s:r4(duration_s),red_mean:r4(red_mean),green_mean:green_mean===null?null:r4(green_mean),red_ac_dc:r4(clamp(sd(x)/Math.max(1e-9,red_mean),0,1))};
  if(ibis.length<3)return fail('no_pulse',base);
  const bpmPeaks=60000/median(ibis);const ac=acfPeriod(s,fs);const bpmAcf=ac.period_s>0?60/ac.period_s:0;
  const agree=bpmAcf>0&&Math.abs(bpmAcf-bpmPeaks)/bpmPeaks<=.08?1:0;
  const expected=duration_s*bpmPeaks/60;const coverage=clamp(ibis.length/Math.max(1,expected-1),0,1);
  const cv=sd(ibis)/mean(ibis);const regularity=1-clamp(cv/.25,0,1);
  const sqi=r4(clamp(.35*ac.strength+.25*coverage+.2*regularity+.2*agree,0,1));
  const beats=ibis.length+1;
  const out={...base,bpm:r4(bpmPeaks),sqi,beats,fs_hz:fs,hrv_rmssd_ms:ibis.length>=rules.min_hrv_ibis?r4(rmssd(ibis)):null,ibi_cv:r4(cv)};
  if(!(bpmPeaks>=rules.min_bpm&&bpmPeaks<=rules.max_bpm))return {...out,valid:false,reason:'bpm_out_of_range'};
  if(beats<rules.min_beats)return {...out,valid:false,reason:'too_few_beats'};
  if(sqi<rules.min_sqi)return {...out,valid:false,reason:'low_signal_quality'};
  return {...out,valid:true,reason:null};
}
export const PPG_REASONS=Object.freeze({
  too_few_frames:'Not enough camera frames.',bad_timestamps:'Camera timing was not usable.',too_short:'Hold your finger still for the whole 30 seconds.',
  no_finger:'No fingertip detected. Cover the rear camera and the light with your fingertip.',flat_signal:'The signal was flat.',no_pulse:'No pulse found in the signal.',
  bpm_out_of_range:'The rate was outside 40 to 200 bpm, so it is not counted.',too_few_beats:'Too few clean beats to count.',low_signal_quality:'The signal was too noisy.',
});
