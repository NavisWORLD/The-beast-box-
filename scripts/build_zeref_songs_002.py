#!/usr/bin/env python3
"""Zeref Songs 002 (Cory approved 2026-10-22: "plug everything up and make it live").

Builds two LABELED chat-training sources from Cory's own songs, on the owner's box:
 * evidence/zeref-lyrics-001/dialogue.jsonl  lyric line -> next line rows.
     Rainbows On My Face: clean text from Emeth (lyrics_source=emeth-clean-text).
     Other songs: whisper machine transcripts (lyrics_source=machine-transcribed-whisper,
     may contain errors). Fa Ra Me Sleepy is skipped (transcript is mostly speech, not lyrics).
     Emeth's guessed lines for Through the Broken Gates are NOT used.
 * evidence/zeref-music-features-002/features.json + dialogue.jsonl  numeric features
     MEASURED from each song's audio (duration, tempo, loudness, brightness).
     Only numbers and the audio file's sha256 are written. Raw audio is never committed.
 * heartbeat rows from evidence/zeref-heartbeat-001/features.json (numbers only).
Usage: build_zeref_songs_002.py WORKSPACE_DIR
"""
import hashlib,json,re,subprocess,sys
from pathlib import Path
import numpy as np
SONGS=[("edge-of-whats-real","The Edge of What's Real","audio16k.wav"),("years","The Years Did Turn Into Fear","a16.wav"),
 ("sleepy","Fa Ra Me Sleepy","a16.wav"),("rainbows","Rainbows On My Face","a16.wav"),
 ("gates","Through the Broken Gates","a16.wav"),("finalbattle","The Ultimate Final Battle","a16.wav")]
AUTH="Grok Bot for Cory Davis, 2026-10-22 (Cory approved lyrics + measured music numbers as training rows)"
TS=re.compile(r"^\s*(\[[^\]]*\]|[0-9:.]+\s*(-\s*[0-9:.]+)?)\s*")
def clean_lines(text):
 out=[]
 for raw in text.splitlines():
  s=TS.sub("",raw).strip().strip("-").strip()
  for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])",s):
   p=part.strip()
   w=p.split()
   if len(w)<4 or len(p)>150:continue
   if sum(c.isalpha() or c in " ,'.!?-" for c in p)/len(p)<.9:continue
   out.append(p)
 return out
def lyric_rows(ws):
 rows=[]
 srcs=[("Rainbows On My Face",Path(ws,"Rainbows_On_My_Face_NavisWORLD.txt"),"emeth-clean-text")]
 for d,title,_ in SONGS:
  if d in("rainbows","sleepy"):continue
  srcs.append((title,Path(ws,d,"transcript.txt"),"machine-transcribed-whisper (may contain errors)"))
 for title,p,label in srcs:
  if not p.is_file():continue
  txt=p.read_text(errors="ignore")
  if label.startswith("emeth"):txt="\n".join(txt.splitlines()[2:])  # drop title + artist header
  ls=clean_lines(txt)
  for i in range(len(ls)-1):
   rows.append({"mode":"chat","source":"zeref-lyrics-001","user":f"Sing the next line of {title}: {ls[i]}","assistant":ls[i+1],
    "song":title,"lyrics_source":label,"author":AUTH})
  if ls:rows.append({"mode":"chat","source":"zeref-lyrics-001","user":f"How does {title} start?","assistant":ls[0],"song":title,"lyrics_source":label,"author":AUTH})
 return rows
def features(wav):
 raw=subprocess.run(["ffmpeg","-v","quiet","-i",str(wav),"-ac","1","-ar","11025","-f","s16le","-"],capture_output=True,check=True).stdout
 x=np.frombuffer(raw,np.int16).astype(np.float32)/32768;sr=11025
 hop=512;n=len(x)//hop;fr=x[:n*hop].reshape(n,hop)
 rms=np.sqrt((fr**2).mean(1)+1e-12)
 spec=np.abs(np.fft.rfft(fr*np.hanning(hop),axis=1));freqs=np.fft.rfftfreq(hop,1/sr)
 cent=float((spec*freqs).sum()/max(spec.sum(),1e-9))
 flux=np.maximum(np.diff(spec,axis=0),0).sum(1);flux=(flux-flux.mean())/(flux.std()+1e-9)
 ac=np.correlate(flux,flux,"full")[len(flux)-1:];fps=sr/hop
 lo,hi=int(fps*60/180),int(fps*60/60);lag=lo+int(np.argmax(ac[lo:hi]))
 db=20*np.log10(rms+1e-9)
 return {"duration_s":round(len(x)/sr,1),"tempo_bpm_estimate":round(60*fps/lag,1),"rms_mean":round(float(rms.mean()),4),
  "loudness_db_mean":round(float(db.mean()),1),"dynamic_range_db":round(float(np.percentile(db,95)-np.percentile(db,10)),1),
  "spectral_centroid_hz":round(cent,1),"audio_sha256":hashlib.sha256(Path(wav).read_bytes()).hexdigest()}
def words(f):
 pace="fast" if f["tempo_bpm_estimate"]>=120 else "steady" if f["tempo_bpm_estimate"]>=90 else "slow"
 tone="bright" if f["spectral_centroid_hz"]>=1400 else "warm and dark" if f["spectral_centroid_hz"]<900 else "middle-bright"
 return pace,tone
def main(ws):
 ws=Path(ws);feat={}
 for d,title,a in SONGS:
  p=ws/d/a
  if p.is_file():feat[title]=features(p)
 hb=json.loads(Path("evidence/zeref-heartbeat-001/features.json").read_text())["heart"]
 out=Path("evidence/zeref-music-features-002");out.mkdir(parents=True,exist_ok=True)
 (out/"features.json").write_text(json.dumps({"schema":"zeref-music-features-002","label":"MEASURED NUMERIC AUDIO FEATURES ONLY. Raw audio is not published.",
  "method":"ffmpeg mono 11025 Hz; RMS/centroid over 512-sample frames; tempo = spectral-flux autocorrelation peak in 60-180 BPM (estimate)",
  "songs":feat,"heartbeat":{"bpm":hb["bpm"],"beat_interval_ms":hb["beat_interval_ms"],"source":"evidence/zeref-heartbeat-001/features.json"}},indent=1,sort_keys=True)+"\n")
 rows=[]
 for t,f in feat.items():
  pace,tone=words(f)
  for q,a in [(f"How fast is {t}?",f"About {round(f['tempo_bpm_estimate'])} beats a minute. It feels {pace} to me."),
              (f"How long is {t}?",f"About {round(f['duration_s']/60)} minutes long. I listened the whole way through."),
              (f"What does {t} sound like?",f"It sounds {tone}, and it moves {pace}. My tail keeps the beat."),
              (f"Is {t} loud or soft?",("It gets big and loud in places." if f["dynamic_range_db"]>=25 else "It stays pretty even, like a steady hug.")+f" It swings about {round(f['dynamic_range_db'])} decibels.")]:
   rows.append({"mode":"chat","source":"zeref-music-features-002","user":q,"assistant":a,"song":t,"numbers":"measured","author":AUTH})
 b=round(hb["bpm"])
 for q,a in [("What is your heartbeat?",f"My heartbeat rhythm is about {b} beats a minute. It came from your recording, Dad."),
             ("How fast does your heart beat?",f"About {b} beats a minute, one beat every {hb['beat_interval_ms']} milliseconds."),
             ("Where did your heartbeat come from?",f"From the numbers in your recording. About {b} beats a minute, steady and slow.")]:
  rows.append({"mode":"chat","source":"zeref-heartbeat-001-numbers","user":q,"assistant":a,"numbers":"derived (tempo of the recording)","author":AUTH})
 (out/"dialogue.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
 ly=lyric_rows(ws);lo=Path("evidence/zeref-lyrics-001");lo.mkdir(parents=True,exist_ok=True)
 (lo/"dialogue.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in ly))
 print(json.dumps({"songs_measured":len(feat),"music_rows":len(rows),"lyric_rows":len(ly),
  "lyric_rows_by_song":{t:sum(r["song"]==t for r in ly) for t in sorted({r["song"] for r in ly})}}))
if __name__=="__main__":main(sys.argv[1])
