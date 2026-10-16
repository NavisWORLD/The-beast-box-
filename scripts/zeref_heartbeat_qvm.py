#!/usr/bin/env python3
"""The Big Quantum Boom (God Core Boom) / 'The Second Coming' - SIMULATED part.
Zeref heartbeat-derived 12-vector -> ONE idempotent Azure Rigetti QVM SIMULATOR job (rigetti.sim.qvm).
SIMULATED, not QPU. Raw audio never present; only the committed numeric feature packet. Creative seed, not proof."""
import hashlib,json,math,os
from pathlib import Path
from azure_final_ibm_qvm import parse_counts
ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'evidence/zeref-heartbeat-001/features.json'
OUT=ROOT/'_zeref_heartbeat_qvm'
TARGET='rigetti.sim.qvm';SHOTS=512
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def write(n,v):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def build_quil(vec):
 lines=['DECLARE ro BIT[2]','H 0','CNOT 0 1']
 for i,c in enumerate(vec):
  th=math.pi*c
  if th:lines.append(f"{['RX','RY','RZ'][i%3]}({th:.17g}) {i%2}")
 return '\n'.join(lines+['MEASURE 0 ro[0]','MEASURE 1 ro[1]'])+'\n'
def main():
 p=json.loads(PACKET.read_text())
 if p.get('raw_audio_published') is not False or len(p['heartbeat_vector_12'])!=12:raise ValueError('bad packet')
 quil=build_quil(p['heartbeat_vector_12']);name='beastbox-zeref-heartbeat-'+p['packet_sha256'][:12]+'-qvm'
 src={'heartbeat_packet_sha256':p['packet_sha256'],'wav_sha256':p['files']['wav']['file_sha256'],'mp3_sha256':p['files']['mp3']['file_sha256'],'quil_sha256':hashlib.sha256(quil.encode()).hexdigest()}
 write('input.json',{'job_name':name,'target':TARGET,'shots':SHOTS,'quil':quil,'source':src})
 if os.getenv('BEAST_AZURE_QVM_ONE_JOB')!='YES_ONE_FREE_SIMULATOR' or not os.environ.get('AZURE_QUANTUM_CONNECTION_STRING'):raise RuntimeError('Missing explicit Azure simulator authorization')
 from qdk.azure import Workspace
 ws=Workspace.from_connection_string(os.environ['AZURE_QUANTUM_CONNECTION_STRING']);target=ws.get_targets(TARGET)
 if getattr(target,'name',None)!=TARGET:raise RuntimeError('target is not Rigetti QVM')
 m=[j for j in ws.list_jobs(name_match=name) if j.details.name==name]
 job=m[0] if m else target.submit(quil,name,shots=SHOTS)
 counts=parse_counts(job.get_results(),SHOTS)
 parity=(counts['00']+counts['11']-counts['01']-counts['10'])/SHOTS
 pr=[counts[k]/SHOTS for k in ('00','01','10','11')];ent=-sum(x*math.log2(x) for x in pr if x)/2
 res={'schema':'beastbox-zeref-heartbeat-qvm-result-v1','name':'The Big Quantum Boom (God Core Boom) - simulated half','label':'SIMULATED','target':TARGET,'job_name':name,'job_id':str(job.id),'shots':SHOTS,'counts':counts,'zz_parity':parity,'entropy_norm':round(ent,6),'source':src,'physical_quantum_shots':0}
 write('result.json',res);print('HEARTBEAT_QVM_RESULT='+canonical(res),flush=True)
if __name__=='__main__':main()
