#!/usr/bin/env python3
"""Measured IBM counts -> one idempotent Azure Rigetti QVM job. Classical transfer only."""
import hashlib,json,math,os,re
from pathlib import Path
from azure_final_ibm_qvm import parse_counts
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'_ibm_lumenwisp_native_pixel12d_20261009/measurement_receipt.json'
OUT=ROOT/'_azure_lumenwisp_native_pixel12d_20261009'
JOB='db4sba4lf4us73c36910'
DIGEST='62effbad67bf75e985c0250e0c8a6b1d94f92d8c9e46d25e52a81975461bcce7'
TARGET='rigetti.sim.qvm'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def write(name,value):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def verify(receipt):
 if any((receipt.get('schema')!='navisworld-ibm-longer-onejob-physics-receipt-v1',receipt.get('source_class')!='RECORDED_IBM_HARDWARE',receipt.get('backend_name')!='ibm_marrakesh',receipt.get('job_id')!=JOB,receipt.get('job_status')!='DONE',receipt.get('shot_count')!=16384)):raise ValueError('Unverified IBM hardware source')
 counts=receipt.get('measurements')
 if not isinstance(counts,dict) or set(counts)!={'bell_zz','bell_xx','decoupled_zz','decoupled_xx'} or sha(counts)!=DIGEST or receipt.get('counts_digest_sha256')!=DIGEST:raise ValueError('IBM full count digest failed')
 genome={'domain':'NAVISWORLD::IBM::LUMENWISP_WRAITH_OFFSPRING_NATIVE_PIXEL12D::QBEAST::V1','job_id':JOB,'backend':'ibm_marrakesh','counts':counts}
 if sha(genome)!=receipt.get('beast_genesis_digest_sha256') or sha(genome)!='aaedadcf744d361a9b01bbb591d29904e35cc5298ddceda8f10e08b2a4abd928':raise ValueError('Genome digest failed')
 cor={}
 for basis,distribution in counts.items():
  if not isinstance(distribution,dict) or set(distribution)!={'00','01','10','11'} or any(type(v)!=int or v<0 for v in distribution.values()) or sum(distribution.values())!=4096:raise ValueError('Shot count or shape invalid')
  expectation=(distribution['00']+distribution['11']-distribution['01']-distribution['10'])/4096
  name=basis[:-2]+basis[-2:].upper()
  if receipt.get('expectations',{}).get(name)!=expectation:raise ValueError('Measured expectation differs')
  cor[name]=expectation
 return cor
def main():
 if not os.environ.get('AZURE_QUANTUM_CONNECTION_STRING') or os.getenv('BEAST_AZURE_QVM_ONE_JOB')!='YES_ONE_FREE_SIMULATOR':raise RuntimeError('Missing explicit Azure simulator authorization')
 receipt=json.loads(INPUT.read_text());cor=verify(receipt)
 packet=receipt.get('second_generation_pre_hardware') or {}
 if packet.get('parent_qbeast_id')!='bb-4a61a8d5' or packet.get('parent_ibm_job_id')!='db4rg5klf4us73c34tqg' or packet.get('feature_packet_sha256')!='47dd7682ace55167c070e6703d8cb3defedb7c44e1302054533996d7b0097720':
  raise ValueError('Wrong verified Wraith sprite-derived QPU input')
 angles=[math.acos(max(-1,min(1,cor['bell_ZZ']-cor['decoupled_ZZ']))),math.acos(max(-1,min(1,cor['bell_XX']-cor['decoupled_XX'])))]
 quil='DECLARE ro BIT[2]\nH 0\nCNOT 0 1\n'+f'RX({angles[0]:.17g}) 0\nRY({angles[1]:.17g}) 1\n'+'MEASURE 0 ro[0]\nMEASURE 1 ro[1]\n'
 name='beastbox-lumenwisp-native-sprite-'+JOB+'-'+DIGEST[:12]+'-qvm'
 source={'parent_qbeast_id':'bb-4a61a8d5','parent_ibm_job_id':'db4rg5klf4us73c34tqg',
  'native_spritelight_12d_sha256':'47dd7682ace55167c070e6703d8cb3defedb7c44e1302054533996d7b0097720',
  'ibm_job_id':JOB,'ibm_backend':'ibm_marrakesh','ibm_counts_sha256':DIGEST,
  'classical_measurement_transfer':True,'expectations':cor,'rotation_angles_rad':angles,'quil_sha256':hashlib.sha256(quil.encode()).hexdigest()}
 write('input.json',{'job_name':name,'target':TARGET,'shots':512,'quil':quil,'source':source})
 from qdk.azure import Workspace
 workspace=Workspace.from_connection_string(os.environ['AZURE_QUANTUM_CONNECTION_STRING'])
 target=workspace.get_targets(TARGET)
 if getattr(target,'name',None)!=TARGET:raise RuntimeError('Actual target is not Rigetti QVM')
 matches=[j for j in workspace.list_jobs(name_match=name) if j.details.name==name]
 if len(matches)>1:raise RuntimeError('Ambiguous prior Azure simulator job')
 submitted=0
 if matches:job=matches[0]
 else:
  job=target.submit(quil,name,shots=512)
  submitted=1
 write('submission.json',{'job_id':str(job.id),'target':TARGET,'submitted_this_attempt':submitted})
 print('LUMENWISP_AZURE_QVM_JOB_ID='+str(job.id),flush=True)
 raw=job.get_results()
 write('raw-result.json',{'job_id':str(job.id),'provider_result':raw})
 counts=parse_counts(raw,512)
 result={'schema':'beastbox-lumenwisp-native-sprite-azure-live-qvm-result-v1','source_class':'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU','target':TARGET,'job_name':name,'job_id':str(job.id),'shots':512,'counts':counts,'counts_sha256':sha(counts),'source':source,'submitted_this_attempt':submitted,'physical_quantum_shots':0,'azure_cosmos_db_writes':0,'model_calls':0}
 write('result.json',result)
 print('LUMENWISP_AZURE_QVM_RESULT='+canonical(result),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  write('failure.json',{'error_type':type(e).__name__,'credential_recorded':False})
  raise
