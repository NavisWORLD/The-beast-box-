#!/usr/bin/env python3
"""Local-only: user's voice/music file -> derived CST12 numeric packet.
The raw audio (and any embedded text track) is NEVER committed; only hash + numbers.
Uses the COSMOS_MUSIC_SUITE CSTStateEngine (leaky 12-channel state) at engine commit deebc53.
Usage: python cory_voice_cst12_features.py AUDIO PATH_TO_cosmos_music_src OUT.json"""
import hashlib,json,subprocess,sys
import numpy as np
audio,src,out=sys.argv[1:4]
sys.path.insert(0,src)
from cosmos_music.state import CSTStateEngine
raw=open(audio,'rb').read();fsha=hashlib.sha256(raw).hexdigest()
pcm=subprocess.run(['ffmpeg','-v','error','-i',audio,'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','-'],capture_output=True,check=True).stdout
psha=hashlib.sha256(pcm).hexdigest()
x=np.frombuffer(pcm,dtype='<i2').astype(np.float64)/32768.0;sr=8000;dur=len(x)/sr
# frame-level (50 ms) RMS + spectral
fl=400;nf=len(x)//fl;fr=x[:nf*fl].reshape(nf,fl)
rms=np.sqrt((fr**2).mean(1))
spec=np.abs(np.fft.rfft(fr*np.hanning(fl),axis=1));freqs=np.fft.rfftfreq(fl,1/sr)
bands={'low_0_250':(0,250),'lowmid_250_1000':(250,1000),'mid_1000_2500':(1000,2500),'high_2500_4000':(2500,4001)}
tot=spec.sum()+1e-12;band_share={k:float(spec[:,(freqs>=a)&(freqs<b)].sum()/tot) for k,(a,b) in bands.items()}
cent=(spec*freqs).sum(1)/(spec.sum(1)+1e-12)
flux=np.r_[0,np.maximum(0,np.diff(spec,axis=0)).sum(1)];flux/=flux.max()+1e-12
# tempo: autocorrelation of onset flux, 50-200 bpm
o=flux-flux.mean();ac=np.correlate(o,o,'full')[len(o)-1:]
lags=np.arange(len(ac));fps=sr/fl;bl=lags[(lags>=fps*60/200)&(lags<=fps*60/50)]
lag=bl[np.argmax(ac[bl])];bpm=float(60*fps/lag);tc=float(ac[lag]/(ac[0]+1e-12))
# pitch-lock proxy: spectral peakiness (max/mean) in voice range 80-1000 Hz
vr=(freqs>=80)&(freqs<=1000);peak=spec[:,vr].max(1)/(spec[:,vr].mean(1)+1e-12)
W=48;edges=np.linspace(0,nf,W+1).astype(int);eng=CSTStateEngine();frames=[];rms_ref=np.percentile(rms,95)+1e-12
for i in range(W):
 s=slice(edges[i],edges[i+1]);ve=float(np.clip(rms[s].mean()/rms_ref,0,1))
 pl=float(np.clip((np.median(peak[s])-1)/20,0,1));pf=float(np.clip(flux[s].mean()*4,0,1))
 ht=float(np.clip(cent[s].mean()/2000,0,1))
 st=eng.update(voice_energy=ve,pitch_lock=pl,phrase_flux=pf,tempo_coherence=float(np.clip(tc,0,1)),bpm=bpm,harmonic_tension=ht,dt=dur/W)
 frames.append([round(v,9) for v in st.vector()])
F=np.array(frames);agg=[round(float(v),9) for v in F.mean(0)];qm=[[round(float(v),9) for v in F[q*12:(q+1)*12].mean(0)] for q in range(4)]
pkt={'schema':'beastbox-cosmos-music-derived-12d-audio-qpu-input-v1','song_original_file_sha256':fsha,'decoded_pcm_s16le_8khz_sha256':psha,'original_size_bytes':len(raw),'duration_seconds':round(dur,5),'sample_rate':sr,'window_count':W,
 'summary':{'estimated_bpm':round(bpm,3),'tempo_autocorr_coherence':round(tc,4),'rms_mean_dbfs':round(float(20*np.log10(rms.mean()+1e-12)),2),'rms_peak_dbfs':round(float(20*np.log10(rms.max()+1e-12)),2),'loud_frame_fraction_above_-30dbfs':round(float((20*np.log10(rms+1e-12)>-30).mean()),4),'spectral_centroid_hz_mean':round(float(cent.mean()),1),'band_energy_share':{k:round(v,4) for k,v in band_share.items()}},
 'provenance':{'engine_repository':'NavisWORLD/infinite-adaptive-audio-12d-universe-engine','engine_commit':'deebc53ad34d028e8a9bcaeab8d2a73b310c75f2','engine_file':'COSMOS_MUSIC_SUITE/python/src/cosmos_music/state.py','extractor':'scripts/cory_voice_cst12_features.py','data_source':"Cory's own voice/music recording, locally decoded, 48 consecutive windows",'scope':'musical numeric parameters only; not sensor/physiological values','hardware_audio_type':'numerical 12-channel rotation parameter controls, NOT digitized audio loaded as quantum state'},
 'cst12_channel_names':['voice_energy','pitch_lock','phrase_flux','tempo_coherence','motion_energy','tilt_x','tilt_y','rotation_flux','pulse_phase','pulse_stability','harmonic_tension','synaptic_memory'],
 'cst12_aggregated':agg,'cst12_quarter_means':qm,'cst12_last_frame':frames[-1],'unobserved_sensor_slots':[4,5,6,7,9],'original_song_media_uploaded_to_public_git':False,'embedded_text_track_published':False}
pkt['audio_packet_sha256']=hashlib.sha256(json.dumps({k:v for k,v in pkt.items()},sort_keys=True,separators=(',',':')).encode()).hexdigest()
open(out,'w').write(json.dumps(pkt,indent=2,sort_keys=True)+'\n');print(json.dumps(pkt['summary']),agg)
