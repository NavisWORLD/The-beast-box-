#!/usr/bin/env python3
"""Derive Cory's-music features (Zeref Music 001). Raw audio is NEVER committed:
only sha256 + derived numbers. Usage: zeref_music_features.py OUT_JSON slug=title=path ..."""
import hashlib,json,subprocess,sys,tempfile,os
import numpy as np,librosa
KEYS=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MAJ=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]);MIN=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
def key_of(ch):
 best=None
 for i in range(12):
  for mode,prof in(("major",MAJ),("minor",MIN)):
   r=float(np.corrcoef(ch,np.roll(prof,i))[0,1])
   if best is None or r>best[0]:best=(r,f"{KEYS[i]} {mode}")
 return best
def feat(slug,title,path):
 raw=open(path,"rb").read();tmp=tempfile.mktemp(suffix=".wav");subprocess.run(["ffmpeg","-v","error","-y","-i",path,"-ac","1","-ar","22050",tmp],check=True);y,sr=librosa.load(tmp,sr=22050,mono=True);os.remove(tmp)
 dur=len(y)/sr;tempo,beats=librosa.beat.beat_track(y=y,sr=sr);tempo=float(np.atleast_1d(tempo)[0])
 ch=librosa.feature.chroma_cqt(y=y,sr=sr).mean(axis=1);conf,key=key_of(ch)
 rms=librosa.feature.rms(y=y)[0];hop=512;fps=sr/hop;n=max(1,int(dur//10))
 curve=[round(float(20*np.log10(np.mean(rms[int(i*10*fps):int((i+1)*10*fps)])+1e-9)),2) for i in range(n)]
 cen=librosa.feature.spectral_centroid(y=y,sr=sr)[0]
 mf=librosa.feature.mfcc(y=y,sr=sr,n_mfcc=13);bnd=librosa.segment.agglomerative(mf,8)
 secs=[round(float(t),1) for t in librosa.frames_to_time(bnd,sr=sr)]
 en=float(np.mean(rms));
 return {"slug":slug,"title":title,"audio_sha256":hashlib.sha256(raw).hexdigest(),"audio_bytes":len(raw),
  "duration_s":round(dur,2),"tempo_bpm":round(tempo,2),"beat_count":int(len(beats)),
  "key_estimate":key,"key_confidence":round(conf,3),"chroma_mean":[round(float(c),3) for c in ch/ch.max()],
  "loudness_dbfs_mean":round(float(20*np.log10(en+1e-9)),2),"loudness_curve_10s_dbfs":curve,
  "energy_0_1":round(min(1.0,en/0.25),3),"spectral_centroid_hz_mean":round(float(cen.mean()),1),
  "brightness_0_1":round(min(1.0,float(cen.mean())/4000),3),"section_starts_s":secs}
out=sys.argv[1];songs=[feat(*a.split("=",2)) for a in sys.argv[2:]]
json.dump({"schema":"zeref-music-features-v1","method":"librosa "+librosa.__version__+" (beat_track, chroma_cqt + Krumhansl key profiles, RMS, spectral centroid, MFCC agglomerative 8 sections)",
 "raw_audio_committed":False,"songs":songs},open(out,"w"),indent=1);print(json.dumps([(s["title"],s["tempo_bpm"],s["key_estimate"]) for s in songs]))
