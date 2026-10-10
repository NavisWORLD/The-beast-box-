#!/usr/bin/env python3
"""Five fresh physical IBM Sampler jobs, conditioned by the actual user media.

DO NOT call artwork photons, processed song features, or archived heartbeat
features a live physical light/biometric input. RX/RY/RZ gates receive classical
12-channel values extracted before this workflow. A new Sampler job is attempted
for each distinct QBEAST only while the 300 QPU-second aggregate cap permits.
Stable IBM tags prevent re-submission after CI retries or interruptions.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,os,sys

from ibm_open_plan_preflight import quota_receipt

SOURCE=Path('experiment-input/five-creature-real-media-12d-20261010.json')
OUT=Path('_ibm_five_multisource_qbeasts_20261010')
QPU_CAP=24
TOTAL_OWNER_CAP=300
SHOTS=4096
PUBS=('bell_zz','bell_xx','decoupled_zz','decoupled_xx')
REQUIRED_SONG='4410ed871310ae2ce4429c7f525b93105f1a5d4521213fe052f0ecefea9a7e47'
REQUIRED_VIDEOS=('540ac6eb5a8a81f1faa370c4f8d3e281c48a6046ff90dab14ea1355956e4ffa9',
 'ef1e0982371a0d74ab25ee994f51f011bd6efa9b4e7fa5c25ca7a39acf4358f5')
EXPECTED_NAMES=('Zeref-Nightcat-Dragon','Umbrascale-Starseed','Pistonwyrm-Gearseed','Heartflare-Moonfire','Moonwraith-Cassette-Kit')

def stamp():return datetime.now(timezone.utc).isoformat()
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(data):return hashlib.sha256(canonical(data)).hexdigest()
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
def validate():
 p=json.loads(SOURCE.read_text())
 if p.get('schema')!='beastbox-5qbeast-real-media-12d-prehardware-v1':raise ValueError('Missing real original media packet')
 if p.get('source_song_sha256')!=REQUIRED_SONG or (p.get('source_long_video_sha256'),p.get('source_wraith_video_sha256'))!=REQUIRED_VIDEOS:
  raise ValueError('Wrong original song or actual video sources')
 if p.get('source_images_combined_sha256')!='203e36b275fdc2e3b0b0381add3d71a99bd61ef31899ca5915aa44a2e921cd13' or p.get('image_count')!=30:
  raise ValueError('Original 30-image feature corpus missing or replaced')
 if p.get('full_source_manifest_sha256')!='7e34156b41e37c65cc1b8bba6810ca27764afc52cfaa9b5c64c7e146e61598ab':
  raise ValueError('Unpinned source media manifest')
 if p.get('source_heartbeat_original_mp3_unavailable') is not True or not p.get('sources_derived_before_hardware'):
  raise ValueError('Heartbeat was not correctly labeled as archived audio-only feature source')
 if [a.get('name') for a in p.get('creatures',[])]!=list(EXPECTED_NAMES):
  raise ValueError('Missing one of five unique exact source creatures')
 if len(set(a.get('primary_image_sha256') for a in p['creatures']))!=5:raise ValueError('Duplicate primary images')
 for beast in p['creatures']:
  v=beast.get('global_12d')
  if not isinstance(v,list) or len(v)!=12 or not all(type(z) in (int,float) and math.isfinite(z) and 0<=z<=1 for z in v):
   raise ValueError('Invalid 12-channel multimedia controls: '+beast['name'])
  if len(beast.get('windows48_sha256',''))!=64:raise ValueError('Full 48-window source trace missing')
 return p

def circuits(vec):
 from qiskit import QuantumCircuit
 rows=[]
 for entangled in (True,False):
  for basis in ('z','x'):
   name=('bell' if entangled else 'decoupled')+'_'+basis+basis
   qc=QuantumCircuit(2,name=name)
   qc.h(0)
   if entangled:qc.cx(0,1)
   for i,v in enumerate(vec):
    # All 12 channels contain original image+song+both video+preserved
    # audio-derived heartbeat information BEFORE the quantum gate submission.
    theta=1.25*v
    if i%3==0:qc.rx(theta,i%2)
    elif i%3==1:qc.ry(theta,i%2)
    else:qc.rz(theta,i%2)
   if basis=='x':qc.h(0);qc.h(1)
   qc.measure_all()
   rows.append((name,qc))
 assert [n for n,_ in rows]==list(PUBS)
 return rows

def counts_for(result):
 c={str(k).replace(' ',''):int(v) for k,v in result.join_data().get_counts().items()}
 if any(len(k)!=2 or set(k)-{'0','1'} or v<0 for k,v in c.items()) or sum(c.values())!=SHOTS:
  raise ValueError('Actual IBM count map invalid')
 return dict(sorted(c.items()))

def run():
 from qiskit.transpiler import generate_preset_pass_manager
 from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
 p=validate()
 save(OUT/'source-commitment.json',{'source_manifest_sha256':p['full_source_manifest_sha256'],
  'compiled_from_30_art_sources_two_original_videos_song_and_audio_heartbeat':True,
  'original_heartbeat_mp3_available':False,'no_raw_media_uploaded_to_ibm':True,
  'five_input_digests':{b['name']:b['windows48_sha256'] for b in p['creatures']}})
 if os.getenv('BEAST_REAL_QPU_FIVE_MEDIA')!='YES_FIVE_TAGGED_REAL_JOBS':
  raise RuntimeError('Five-job explicit authorization flag missing')
 token=os.getenv('IBM_QUANTUM_TOKEN','').strip()
 if not token:raise RuntimeError('IBM_QUANTUM_TOKEN unavailable: zero hardware submissions')
 service=QiskitRuntimeService(channel='ibm_quantum_platform',token=token,plans_preference=['open'])
 instance=service.active_instance()
 if not instance:raise RuntimeError('No authenticated Open Plan instance')
 # One runner, one process: prevent the 5 jobs from racing against each other.
 for i,b in enumerate(p['creatures']):
  name=b['name'];place=OUT/f'{i+1}-{name.lower()}'
  tag=f'navisworld-five-media-{i+1}-{p["full_source_manifest_sha256"][:12]}-v1'
  try:
   prior=service.jobs(limit=100,program_id='sampler',job_tags=[tag])
   if len(prior)>1:raise RuntimeError('Ambiguous duplicate tagged real QPU job; fail closed')
   new=not bool(prior)
   if new:
    q=quota_receipt(service.usage(),str(instance))
    save(place/'preflight.json',q)
    if q['already_consumed_seconds']+QPU_CAP>TOTAL_OWNER_CAP or q['remaining_seconds']<QPU_CAP:
     raise RuntimeError('Owner 300-second cumulative QPU budget exhausted: no submission')
    backend=service.least_busy(simulator=False,operational=True,min_num_qubits=2)
    if backend.configuration().simulator:raise RuntimeError('Simulator not allowed')
    originals=circuits(b['global_12d']);nulls=circuits([0]*12)
    if any(str(a[1])==str(b0[1]) for a,b0 in zip(originals,nulls)):
     raise RuntimeError('Media ablation did not change all circuit gates')
    manager=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=261010)
    isa=[manager.run(c) for _,c in originals]
    if len(isa)!=4 or any(c.depth()>300 for c in isa):raise RuntimeError('Unsafe compiled QPU circuit')
    save(place/'pre-hardware.json',{'beast_alias':name,'tag':tag,'full_48_windows_sha256':b['windows48_sha256'],
       'primary_original_image_sha256':b['primary_image_sha256'],'global_12d':b['global_12d'],
       'src_manifest_sha256':p['full_source_manifest_sha256'],'compiled_sha256':[hashlib.sha256(str(c).encode()).hexdigest() for c in isa],
       'physical_optical_input':False,'source_is_classical_media_features':True,
       'max_qpu_seconds':QPU_CAP,'requested_shots_per_pub':SHOTS,
       'individual_media_ablation_passed':True,'preflight':q})
    sampler=SamplerV2(mode=backend)
    sampler.options.max_execution_time=QPU_CAP
    sampler.options.environment.job_tags=[tag,'beast-reality-probe','5qbeast-real-media-20261010']
    job=sampler.run(isa,shots=SHOTS)
   else:job=prior[0]
   save(place/'submission.json',{'utc':stamp(),'job_id':str(job.job_id()),
      'tag':tag,'new_real_hardware_submission':new,'shots_requested':4*SHOTS,'qpu_cap_seconds':QPU_CAP,
      'original_media_sha256':p['full_source_manifest_sha256'],'credential_recorded':False})
   print('MEDIA_FIVE_QPU_SUBMISSION='+json.dumps({'creature':name,'job_id':str(job.job_id()),'fresh_submitted':new}),flush=True)
   measured=job.result()
   if len(measured)!=4 or str(job.status())!='DONE':raise RuntimeError('No completed physical IBM results')
   counts={label:counts_for(measured[j]) for j,label in enumerate(PUBS)}
   meta=job.metrics() or {}
   receipt={'schema':'beastbox-five-real-media-ibm-20261010-v1','alias':name,'source_class':'RECORDED_IBM_HARDWARE',
    'job_id':str(job.job_id()),'backend_name':str(job.backend().name),'status':'DONE',
    'shots':4*SHOTS,'counts':counts,'counts_sha256':digest(counts),'source_manifest_sha256':p['full_source_manifest_sha256'],
    'input_windows48_sha256':b['windows48_sha256'],'primary_image_sha256':b['primary_image_sha256'],
    'hardware_metrics':meta,'recorded_utc':stamp(),
    'no_chsh_test':True,'no_optical_or_quantum_state_transfer':True}
   save(place/'measurement_receipt.json',receipt)
   print('MEDIA_FIVE_REAL_QPU_DONE='+json.dumps({'name':name,'job':receipt['job_id'],'backend':receipt['backend_name'],
     'shots':receipt['shots'],'counts_sha256':receipt['counts_sha256']}),flush=True)
  except Exception as exc:
   save(place/'failure.json',{'utc':stamp(),'alias':name,'type':type(exc).__name__,
     'message':str(exc)[:220],'note':'Inspect submission separately; never treat a failure as new quantum data'})
   print('MEDIA_FIVE_REAL_QPU_BLOCKED='+name+':'+type(exc).__name__,file=sys.stderr,flush=True)
   raise

if __name__=='__main__':
 run()
