#!/usr/bin/env python3
"""Cory's voice/music CST12 packet -> ONE idempotent Azure Rigetti QVM SIMULATOR job (rigetti.sim.qvm).
SIMULATED, not QPU. No IBM. Raw audio never present in CI; only the committed numeric packet."""
import hashlib,json,math,os
from pathlib import Path
from azure_final_ibm_qvm import parse_counts
ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'experiment-input/cory-voice-quantum-love-cst12-20261015.json'
OUT=ROOT/'_azure_cory_voice_20261015'
TARGET='rigetti.sim.qvm';SHOTS=512
AUDIO_SHA='a88bb03daab51300b68f33cb2749a0433989eae34e085db1a075882f8a1109a9'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def sha(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def write(n,v):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def build_quil(p):
 g=p['cst12_aggregated'];q=p['cst12_quarter_means']
 lines=['DECLARE ro BIT[2]','H 0','CNOT 0 1']
 for i in range(12):
  c=0.4*g[i]+0.15*sum(qq[i] for qq in q);th=1.2*c
  if th:lines.append(f"{['RX','RY','RZ'][i%3]}({th:.17g}) {i%2}")
 lines+=['MEASURE 0 ro[0]','MEASURE 1 ro[1]']
 return '\n'.join(lines)+'\n'
def verify(p):
 if p.get('schema')!='beastbox-cosmos-music-derived-12d-audio-qpu-input-v1' or p.get('song_original_file_sha256')!=AUDIO_SHA or p.get('window_count')!=48:raise ValueError('wrong packet')
 if p.get('original_song_media_uploaded_to_public_git') is not False:raise ValueError('privacy flag')
 g=p['cst12_aggregated']
 if len(g)!=12 or any(not(0<=x<=1) for x in g) or any(g[i]!=0 for i in [4,5,6,7,9]):raise ValueError('bad channels')
def main():
 p=json.loads(PACKET.read_text());verify(p);quil=build_quil(p)
 name='beastbox-cory-voice-'+AUDIO_SHA[:12]+'-'+p['audio_packet_sha256'][:12]+'-qvm'
 source={'audio_file_sha256':AUDIO_SHA,'audio_cst12_packet_sha256':p['audio_packet_sha256'],'quil_sha256':hashlib.sha256(quil.encode()).hexdigest(),'ibm_jobs':0}
 write('input.json',{'job_name':name,'target':TARGET,'shots':SHOTS,'quil':quil,'source':source})
 if os.getenv('BEAST_AZURE_QVM_ONE_JOB')!='YES_ONE_FREE_SIMULATOR' or not os.environ.get('AZURE_QUANTUM_CONNECTION_STRING'):raise RuntimeError('Missing explicit Azure simulator authorization')
 from qdk.azure import Workspace
 ws=Workspace.from_connection_string(os.environ['AZURE_QUANTUM_CONNECTION_STRING'])
 target=ws.get_targets(TARGET)
 if getattr(target,'name',None)!=TARGET:raise RuntimeError('target is not Rigetti QVM')
 m=[j for j in ws.list_jobs(name_match=name) if j.details.name==name]
 if len(m)>1:raise RuntimeError('ambiguous prior job')
 sub=0
 if m:job=m[0]
 else:job=target.submit(quil,name,shots=SHOTS);sub=1
 write('submission.json',{'job_id':str(job.id),'target':TARGET,'submitted_this_attempt':sub})
 print('CORY_VOICE_QVM_JOB_ID='+str(job.id),flush=True)
 raw=job.get_results();counts=parse_counts(raw,SHOTS)
 parity=(counts['00']+counts['11']-counts['01']-counts['10'])/SHOTS
 probs=[counts[k]/SHOTS for k in ('00','01','10','11')];ent=-sum(x*math.log2(x) for x in probs if x)/2
 res={'schema':'beastbox-cory-voice-azure-qvm-result-v1','label':'SIMULATED','source_class':'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU','target':TARGET,'job_name':name,'job_id':str(job.id),'shots':SHOTS,'counts':counts,'counts_sha256':sha(counts),'zz_parity':parity,'entropy_norm':round(ent,6),'source':source,'submitted_this_attempt':sub,'physical_quantum_shots':0,'ibm_jobs_submitted':0,'model_calls':0}
 write('result.json',res);print('CORY_VOICE_QVM_RESULT='+canonical(res),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  write('failure.json',{'error_type':type(e).__name__,'credential_recorded':False});raise
