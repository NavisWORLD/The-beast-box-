#!/usr/bin/env python3
"""One bounded physical activation probe synchronized with real production UI chat.

The final dragon's genesis remains the earlier measured IBM/Azure receipt. This
additional job observes conversation overlap, not a continuing quantum brain.
"""
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ibm_open_plan_preflight import quota_receipt
from ibm_eternal_dragon_longer_probe import circuits, same_parity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'_final_live_production'
TAG = 'navisworld-umbrascale-production-chat-20261009-onejob-v1'
QPU_CAP = 90
SHOTS = 32768

def stamp():
    return datetime.now(timezone.utc).isoformat()

def record(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT/(name+'.tmp')
    tmp.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    tmp.replace(OUT/name)

def main():
    token = os.environ.get('IBM_QUANTUM_TOKEN','').strip()
    if not token or os.environ.get('BEAST_REAL_QPU_ONE_JOB') != 'YES_ONE_REAL_JOB':
        raise RuntimeError('Missing bounded authorized IBM configuration')
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    service = QiskitRuntimeService(channel='ibm_quantum_platform',token=token,plans_preference=['open'])
    instance = service.active_instance()
    if not instance:
        raise RuntimeError('No active Open Plan instance')
    quota = quota_receipt(service.usage(), str(instance))
    record('quota-before.json',quota)
    if not quota['headroom_for_one_300_second_job'] or quota['already_consumed_seconds']+QPU_CAP>300:
        raise RuntimeError('Aggregate 300-second authorization would be exceeded')
    # A stable remote tag prevents new hardware submission on retries.
    previous = service.jobs(limit=100,program_id='sampler',job_tags=[TAG])
    if len(previous)>1:
        raise RuntimeError('Ambiguous tagged job; no new submission')
    env = dict(os.environ)
    env.pop('IBM_QUANTUM_TOKEN',None)
    env['BEAST_LIVE_QPU_HANDSHAKE_DIR']=str(OUT)
    # Fresh browser, genuine public production origin, genuine hosted model.
    args=['node',str(ROOT/'scripts/final_live_production.cjs'),'https://www.beastboxcosmos.xyz',str(OUT/'browser'),
          'experiment-evidence/final-live-umbrascale-001','bb-8546076e','db4m3bslf4us73c2ui9g',
          '/spark/ibm-final-live-reality-probe-20261009.json']
    browser=subprocess.Popen(args,cwd=ROOT/'apps/beastbox-cloud',env=env)
    try:
        deadline=time.monotonic()+180
        while not (OUT/'browser-ready.json').exists():
            if browser.poll() is not None:
                raise RuntimeError('Browser failed before hardware submission')
            if time.monotonic()>deadline:
                raise RuntimeError('Production native boot did not become ready')
            time.sleep(.25)
        submitted=0
        if previous:
            job=previous[0]
        else:
            backend=service.least_busy(simulator=False,operational=True,min_num_qubits=2)
            if backend.configuration().simulator:
                raise RuntimeError('Simulator refused for physical probe')
            manager=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=241009)
            compiled=[manager.run(qc) for _,qc in circuits()]
            if len(compiled)!=4 or any(q.depth()>300 for q in compiled):
                raise RuntimeError('Compiled physical circuit bound changed')
            record('proposed-circuits.json',{'names':[name for name,_ in circuits()],
                   'backend':str(backend.name),'shots_per_pub':SHOTS,'pub_count':4,
                   'compiled_depths':[q.depth() for q in compiled],'max_qpu_seconds':QPU_CAP,
                   'compiled_display_sha256':[hashlib.sha256(str(q).encode()).hexdigest() for q in compiled]})
            sampler=SamplerV2(mode=backend)
            sampler.options.max_execution_time=QPU_CAP
            sampler.options.environment.job_tags=[TAG,'beast-reality-probe','production-conversation']
            job=sampler.run(compiled,shots=SHOTS)
            submitted=1
        job_id=str(job.job_id())
        record('submission.json',{'job_id':job_id,'utc':stamp(),'job_tag':TAG,'new_jobs_submitted':submitted,
               'max_qpu_seconds':QPU_CAP,'aggregate_authorized_seconds':300,'shots_requested':SHOTS*4})
        print('LIVE_CONVERSATION_QPU_JOB='+job_id,flush=True)
        deadline=time.monotonic()+15*60
        status_timeline=[]
        while True:
            status=str(job.status())
            point={'job_id':job_id,'status':status,'observed_utc':stamp()}
            record('qpu-status.json',point);status_timeline.append(point)
            if status in ('DONE','ERROR','CANCELLED','FAILED'):
                break
            if time.monotonic()>deadline:
                job.cancel()
                raise RuntimeError('Physical job observation deadline exceeded; cancellation requested')
            time.sleep(.5)
        record('qpu-status-timeline.json',status_timeline)
        if status!='DONE':
            raise RuntimeError('Physical probe did not complete')
        result=job.result()
        names=[name for name,_ in circuits()]
        if len(result)!=4:
            raise RuntimeError('Physical PUB count changed')
        counts={name:{str(k).replace(' ',''):int(v) for k,v in result[i].join_data().get_counts().items()} for i,name in enumerate(names)}
        if any(sum(c.values())!=SHOTS or any(k not in ('00','01','10','11') or v<0 for k,v in c.items()) for c in counts.values()):
            raise RuntimeError('Invalid physical output counts')
        metrics=job.metrics() or {}
        times=metrics.get('timestamps',{})
        hardware_metrics={'timestamps':{k:v for k,v in times.items() if k in ('created','running','finished')},
                          'quantum_seconds':metrics.get('usage',{}).get('quantum_seconds')}
        receipt={'schema':'beastbox-live-production-conversation-qpu-v1','source_class':'RECORDED_IBM_HARDWARE',
                 'job_id':job_id,'backend':str(job.backend().name),'job_status':status,'shots':SHOTS*4,
                 'measurements':counts,'expectations':{n:same_parity(c) for n,c in counts.items()},
                 'counts_sha256':hashlib.sha256(json.dumps(counts,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                 'genesis_job_id':'db4m3bslf4us73c2ui9g','qbeast_id':'bb-8546076e','max_qpu_seconds':QPU_CAP,
                 'new_jobs_submitted':submitted,'observed_utc':stamp(),
                 'hardware_metrics':hardware_metrics,
                 'notice':'Additional bounded physical workload; no quantum state is transported to the model or GBA.'}
        record('hardware-receipt.json',receipt)
        print('SANITIZED_LIVE_CONVERSATION_HARDWARE='+json.dumps(receipt,sort_keys=True),flush=True)
        record('quota-after.json',quota_receipt(service.usage(),str(instance)))
        code=browser.wait(timeout=180)
        if code:
            raise RuntimeError('Production gameplay or actual model conversation failed; hardware receipt retained')
        game=json.loads((OUT/'browser/game-evidence.json').read_text())
        record('combined.json',{'schema':'beastbox-final-live-combined-v1','hardware':receipt,'production_game':game,
                              'qpu_status_timeline':status_timeline,'azure_cosmos_db_write_verified':False})
        print('FINAL_LIVE_PRODUCTION_COMPLETE='+json.dumps({'qbeast_id':game['qbeast_id'],'hardware_job':job_id,
              'actual_model_turns':len(game['conversation']),'requests_started_during_running':sum(t['request_started_during_qpu_running'] for t in game['conversation'])}),flush=True)
    finally:
        if browser.poll() is None:
            browser.terminate()

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        record('failure.json',{'utc':stamp(),'type':type(error).__name__,'credential_recorded':False})
        print('LIVE_PRODUCTION_FAILURE='+type(error).__name__,flush=True)
        raise SystemExit(1)
