#!/usr/bin/env python3
"""Measured IBM counts -> one idempotent Azure Rigetti QVM job. Classical transfer only."""
import hashlib,json,math,os,re
from pathlib import Path
from azure_final_ibm_qvm import parse_counts
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'_ibm_wraith_videoaudio_light12d_20261009/measurement_receipt.json'
OUT=ROOT/'_azure_wraith_videoaudio_light12d_20261009'
JOB='db4rg5klf4us73c34tqg'
DIGEST='de17933e5400a6c18467bd3a454af5f32147135f517c8ef656fc0e5d36ec5377'
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
 genome={'domain':'NAVISWORLD::IBM::WRAITH_IMAGE_VIDEOAUDIO_LIGHT12D::QBEAST::V1','job_id':JOB,'backend':'ibm_marrakesh','counts':counts}
 if sha(genome)!=receipt.get('beast_genesis_digest_sha256') or sha(genome)!='25758f92862ba868ac762ec3234180f92ad8cafae2bce655c20f2b81e2747f7a':raise ValueError('Genome digest failed')
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
 packet=receipt.get('wraith_multisource_pre_hardware') or {}
 if packet.get('original_glyph_sha256')!='303c9d2865195f0f1f7c19eaf889fa989270435e4a3047a7eb6d4b6c6de0449d' or packet.get('original_video_sha256')!='ef1e0982371a0d74ab25ee994f51f011bd6efa9b4e7fa5c25ca7a39acf4358f5' or packet.get('qpu_summary_sha256')!='ceede33f8d78a88f8d69e315490558e9bc21c8b88cf935bd8b1e6c52d57e2f04' or packet.get('video_motion_and_audio_are_qpu_gate_controls') is not True:
  raise ValueError('Must use actual glyph AND sound-and-light video before original IBM physical measurement')
 angles=[math.acos(max(-1,min(1,cor['bell_ZZ']-cor['decoupled_ZZ']))),math.acos(max(-1,min(1,cor['bell_XX']-cor['decoupled_XX'])))]
 quil='DECLARE ro BIT[2]\nH 0\nCNOT 0 1\n'+f'RX({angles[0]:.17g}) 0\nRY({angles[1]:.17g}) 1\n'+'MEASURE 0 ro[0]\nMEASURE 1 ro[1]\n'
 name='beastbox-wraith-videoaudio-'+JOB+'-'+DIGEST[:12]+'-qvm'
 source={'original_glyph_sha256':'303c9d2865195f0f1f7c19eaf889fa989270435e4a3047a7eb6d4b6c6de0449d',
 'original_video_sha256':'ef1e0982371a0d74ab25ee994f51f011bd6efa9b4e7fa5c25ca7a39acf4358f5',
 'wraith_12d_sha256':'ceede33f8d78a88f8d69e315490558e9bc21c8b88cf935bd8b1e6c52d57e2f04',
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
 print('WRAITH_AZURE_QVM_JOB_ID='+str(job.id),flush=True)
 raw=job.get_results()
 write('raw-result.json',{'job_id':str(job.id),'provider_result':raw})
 counts=parse_counts(raw,512)
 result={'schema':'beastbox-wraith-videoaudio-azure-live-qvm-result-v1','source_class':'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU','target':TARGET,'job_name':name,'job_id':str(job.id),'shots':512,'counts':counts,'counts_sha256':sha(counts),'source':source,'submitted_this_attempt':submitted,'physical_quantum_shots':0,'azure_cosmos_db_writes':0,'model_calls':0}
 write('result.json',result)
 print('WRAITH_AZURE_QVM_RESULT='+canonical(result),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  write('failure.json',{'error_type':type(e).__name__,'credential_recorded':False})
  raise
