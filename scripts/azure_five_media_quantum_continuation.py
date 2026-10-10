#!/usr/bin/env python3
"""One real cloud Azure/Rigetti QVM continuation per NEW verified IBM job.

A simulator is not another physical QPU. Its inputs are classical statistics
computed from each brand-new physical IBM receipt; 512 shots per QVM job.
No new IBM jobs are launched by this script.
"""
from __future__ import annotations
import hashlib,json,math,os,sys
from pathlib import Path
from datetime import datetime,timezone
from azure_final_ibm_qvm import parse_counts
ROOT=Path(__file__).resolve().parents[1]
IBM=ROOT/'_ibm_five_multisource_qbeasts_20261010'
OUT=ROOT/'_azure_five_multisource_qbeasts_20261010'
TAG='beastbox-five-multimedia-20261010'
TARGET='rigetti.sim.qvm'
SHOTS=512
NAMES=('Zeref-Nightcat-Dragon','Umbrascale-Starseed','Pistonwyrm-Gearseed','Heartflare-Moonfire','Moonwraith-Cassette-Kit')
MANIFEST='7e34156b41e37c65cc1b8bba6810ca27764afc52cfaa9b5c64c7e146e61598ab'
EXPECTED_NEW_HARDWARE={
 'Zeref-Nightcat-Dragon':('db4tc8kvf2bc73cv3np0','ee0ecbc7d7073f6a130653ca8ed0f89f56876138a6dea49664477157f988e1bb'),
 'Umbrascale-Starseed':('db4tdtkvf2bc73cv3qng','c8ab49c149cdc4c2e6d1f23decd6f54cd8b3571b6c0b6f2546810752ba207376'),
 'Pistonwyrm-Gearseed':('db4te084qg6s73c2m3lg','cfe37f452193e1502c2390a68dd412712ae7f53bdc98dde90997bf2a22dc1882'),
 'Heartflare-Moonfire':('db4te4g4qg6s73c2m470','bc36ac7a9e6866b0c15314144d58847293499ab8a20d4725ea93ec274531cc97'),
 'Moonwraith-Cassette-Kit':('db4te7slf4us73c3888g','59c3ae19b5b8c3e0f03353ccdf5471dd5c5718fed5e4ee1969d0f57bb6f07aec')}

PUBS=('bell_zz','bell_xx','decoupled_zz','decoupled_xx')
def now():return datetime.now(timezone.utc).isoformat()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def verify(r,alias):
 if r.get('schema')!='beastbox-five-real-media-ibm-20261010-v1' or r.get('source_class')!='RECORDED_IBM_HARDWARE' or r.get('alias')!=alias or r.get('status')!='DONE' or not r.get('backend_name','').startswith('ibm_'):
  raise ValueError('Not the actual completed physical IBM source for '+alias)
 if (r.get('job_id'),r.get('counts_sha256'))!=EXPECTED_NEW_HARDWARE[alias]:
  raise ValueError('Source is not the exact new physical IBM job and counts for '+alias)
 if r.get('source_manifest_sha256')!=MANIFEST or r.get('shots')!=16384:
  raise ValueError('Wrong source media or hardware shots')
 c=r.get('counts')
 if not isinstance(c,dict) or set(c)!=set(PUBS) or digest(c)!=r.get('counts_sha256'):
  raise ValueError('Full four-PUB IBM count digest mismatch')
 expectation={}
 for name,counts in c.items():
  if not isinstance(counts,dict) or not all(k in ('00','01','10','11') and type(v)==int and v>=0 for k,v in counts.items()) or sum(counts.values())!=4096:
   raise ValueError('Corrupted authentic IBM PUB '+name)
  expectation[name]=(counts.get('00',0)+counts.get('11',0)-counts.get('01',0)-counts.get('10',0))/4096
 return expectation
def run():
 if os.environ.get('BEAST_AZURE_QVM_FIVE')!='YES_FIVE_EXISTING_IBM_RECEIPTS' or not os.environ.get('AZURE_QUANTUM_CONNECTION_STRING'):
  raise RuntimeError('Authorized Azure QVM settings unavailable; no simulator submission')
 from qdk.azure import Workspace
 workspace=Workspace.from_connection_string(os.environ['AZURE_QUANTUM_CONNECTION_STRING'])
 target=workspace.get_targets(TARGET)
 if getattr(target,'name',None)!=TARGET:raise RuntimeError('Not the actual cloud Rigetti simulator')
 for i,alias in enumerate(NAMES):
  place=OUT/f'{i+1}-{alias.lower()}'
  try:
   file=IBM/f'{i+1}-{alias.lower()}'/'measurement_receipt.json'
   if not file.exists():raise RuntimeError('No completed exact physical IBM receipt; cannot simulate substitute')
   r=json.loads(file.read_text());x=verify(r,alias)
   angles=[math.acos(max(-1.,min(1.,x['bell_zz']-x['decoupled_zz']))),
    math.acos(max(-1.,min(1.,x['bell_xx']-x['decoupled_xx'])))]
   quil='DECLARE ro BIT[2]\nH 0\nCNOT 0 1\n'+f'RX({angles[0]:.17g}) 0\nRY({angles[1]:.17g}) 1\nMEASURE 0 ro[0]\nMEASURE 1 ro[1]\n'
   job_name=TAG+'-'+str(i+1)+'-'+r['job_id']+'-'+r['counts_sha256'][:12]+'-sim'
   source={'ibm_job_id':r['job_id'],'ibm_backend':r['backend_name'],
      'ibm_full_counts_sha256':r['counts_sha256'],
      'source_manifest_sha256':MANIFEST,
      'classical_transferred_expectations':x,'angles_radians':angles,
      'program_sha256':hashlib.sha256(quil.encode()).hexdigest()}
   save(place/'input.json',{'target':TARGET,'job_name':job_name,'shots':SHOTS,'source':source,'quil':quil})
   matches=[j for j in workspace.list_jobs(name_match=job_name) if j.details.name==job_name]
   if len(matches)>1:raise RuntimeError('Duplicate remote Azure simulator jobs: refusing a new one')
   if matches:job=matches[0];submitted=0
   else:job=target.submit(quil,job_name,shots=SHOTS);submitted=1
   save(place/'submission.json',{'job_id':str(job.id),'name':job_name,'submitted_this_attempt':submitted,'utc':now()})
   print('FIVE_AZURE_QVM_SUBMISSION='+json.dumps({'alias':alias,'job_id':str(job.id),'submitted':submitted}),flush=True)
   raw=job.get_results()
   save(place/'raw_provider_result.json',{'job_id':str(job.id),'provider_result':raw})
   counts=parse_counts(raw,SHOTS)
   receipt={'schema':'beastbox-five-actual-azure-rigetti-qvm-20261010-v1',
      'source_class':'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU','creature':alias,
      'job_id':str(job.id),'target':TARGET,'shots':SHOTS,
      'counts':counts,'counts_sha256':digest(counts),'source':source,'submitted_this_attempt':submitted,
      'physical_quantum_shots':0,'model_calls':0,'not_a_quantum_state_transfer':True,'utc':now()}
   save(place/'result.json',receipt)
   print('FIVE_REAL_AZURE_QVM_RESULT='+json.dumps({'alias':alias,'job_id':str(job.id),'counts_sha256':receipt['counts_sha256']}),flush=True)
  except Exception as e:
   save(place/'failure.json',{'alias':alias,'type':type(e).__name__,'message':str(e)[:240],
       'not_a_real_azure_result':True,'utc':now()})
   raise
if __name__=='__main__':run()
