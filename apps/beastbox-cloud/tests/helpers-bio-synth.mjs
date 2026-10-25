// Deterministic synthetic PPG waveform (test-only LCG; no Math.random).
export function synth({bpm=72,secs=35,fs=30,noise=.3,hrv=.03,red=200,green=40,seed=12345}={}){
 let s=seed;const rnd=()=>{s=(s*1664525+1013904223)>>>0;return s/2**32;};
 const t=[],v=[],g=[];let beatT=0;const beats=[];const ibi=60/bpm;
 while(beatT<secs+2){beats.push(beatT);beatT+=ibi*(1+hrv*(rnd()*2-1));}
 for(let i=0;i<secs*fs;i++){const ts=i/fs;let val=0;for(const b of beats){const d=ts-b;if(d>=0&&d<1)val+=Math.exp(-((d-.15)**2)/(2*.05**2))+.35*Math.exp(-((d-.4)**2)/(2*.08**2));}
  t.push(1000+ts*1000);v.push(red-8*val+noise*(rnd()*2-1)+2*Math.sin(ts*.3));g.push(green+noise*(rnd()-.5));}
 return {t,v,g,rnd};
}
