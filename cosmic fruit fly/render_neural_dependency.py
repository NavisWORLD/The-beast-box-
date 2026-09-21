"""Evidence-bound rendering of executed neural-dependency trials (not a live animal).

Every camera picture is reconstructed from the saved trial seed/condition and
matched to the archived camera hash; neural activity is read from the ledger.
Decorative sprite bobbing is not evidence of acquired locomotion in this task.
"""
from __future__ import annotations
import argparse, json, hashlib, math, subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from fly_movement import HERE,DATA,load_graph,sha256
from hard_mode import GESTURES,INTENTS,COLORS
from fusion_hard_mode import camera_observation
from render_build_grow import (ASSET,W,H,NAVY,CYAN,GREEN,WHITE,MUTED,YELLOW,PINK,PURPLE,RED,
    panel,text,coords,fly,graph_layout,brain_panel)
from neural_dependency import OUT,PHASES

FPS=4; FRAMES_PER_TICK=4
PHASE_COUNTS={'train':16,'novel_noise':18,'reversal_train':12,
              'reversal_novel_noise':18,'offspring_transfer_noise':16}
PHASE_LABEL={'train':'SUPERVISED TRAINING','novel_noise':'HELD-OUT / NOISY CAMERA',
             'reversal_train':'RULE REVERSAL / TRAIN',
             'reversal_novel_noise':'REVERSED HELD-OUT','offspring_transfer_noise':'SOFTWARE OFFSPRING'}


def sources(out=OUT):
    result=json.loads((out/'results.json').read_text())
    source=result['source_file_sha256']
    if sha256(out/'runs.jsonl')!=result['ledger_sha256'] or sha256(DATA)!=source['flywire_subset']:
        raise RuntimeError('ledger/connectome hash mismatch')
    for key,path in [('audio_packet',HERE/'data'/'audio_source_feature_packet.json'),
                     ('qpu_counts',HERE/'data'/'linked_ibm_marrakesh_counts.json')]:
        if sha256(path)!=source[key]:raise RuntimeError(f'{key} source changed')
    rows=[json.loads(line) for line in (out/'runs.jsonl').read_text().splitlines()]
    arm=next(row for row in rows if row['arm']=='original_audio_qpu' and row['seed']==0)
    if len(arm['trace'])!=168:raise ValueError('expected complete 168 trial trace')
    chosen=[]
    for phase,n in PHASE_COUNTS.items():
        candidates=[x for x in arm['trace'] if x['phase']==phase]
        assert len(candidates)>=n
        chosen.extend(candidates[(len(candidates)-1)*i//(n-1)] for i in range(n))
    assert len(chosen)==80
    return result,chosen


def frame(trial,shot,tick,sub,frame_no,world,data,layout,summary):
    img=Image.new('RGB',(W,H),NAVY);img.paste(world,(20,16));d=ImageDraw.Draw(img)
    obj=trial['object'];px,py=coords(*trial['pos'])
    wave=math.tau*((frame_no%48)/48.)
    for r in (16,24):d.ellipse((px-r,py-r,px+r,py+r),outline=(239,183,76),width=1)
    d.ellipse((px-8,py-8,px+8,py+8),fill=COLORS[obj],outline=WHITE,width=2)
    start=(trial['pos'][0]-1.18,trial['pos'][1]);fx,fy=coords(start[0],start[1]+.02*math.sin(wave))
    fly(d,fx,fy,0,frame_no,offspring=trial['phase']=='offspring_transfer_noise',scale=1.05)
    text(d,(px-25,py-31),obj.upper(),11,YELLOW)
    for k in range(14):
        x=40+(k*131+frame_no*2)%847;y=44+(k*83+frame_no*(k%3+1))%465
        if 172<x<858 and 176<y<549:d.point((x,y),fill=(234,230,127))

    panel(d,(20,14,714,90));text(d,(34,21),'COSMIC FRUIT FLY / NEURAL RELAY TEST',18,CYAN)
    text(d,(37,57),f'SEED 01/08  |  {PHASE_LABEL[trial["phase"]]}  |  TRIAL {trial["trial"]+1:03d}/168',10,WHITE)
    panel(d,(20,97,710,171));text(d,(37,104),'TASK: NEURAL READOUT -> THREE TOKENS -> RESOURCE',13,CYAN)
    text(d,(37,138),f'{obj.upper():<9}  {trial["gesture"].upper():<10}  {trial["intent"].upper()}',13,YELLOW)

    feat,margin,hsh,rgb=camera_observation(obj,GESTURES.index(trial['gesture']),
        INTENTS.index(trial['intent']),trial['seed'],trial['trial'],trial['noisy_camera'])
    if hsh!=trial['camera_sha256'] or [list(v) for v in feat]!=trial['features']:
        raise RuntimeError(f'virtual retina does not match archived trial {trial["trial"]}')
    # Verify the fixed, label-free retinal encoder too.
    from neural_dependency import raw_retina_code
    if list(np_round(raw_retina_code(rgb)))!=trial['raw_retina_code']:
        raise RuntimeError('retinal encoder mismatch')

    panel(d,(922,15,1268,220));text(d,(937,23),'VIRTUAL FLY RETINA / 96x64',13,CYAN)
    img.paste(Image.fromarray(rgb,'RGB').resize((304,144),Image.Resampling.NEAREST),(939,52));d=ImageDraw.Draw(img)
    text(d,(940,200),'RECOMPUTED + CAMERA HASH CHECKED',10,MUTED)
    panel(d,(922,228,1268,334))
    text(d,(935,237),'ACTUAL DECODER INPUT',13,CYAN)
    text(d,(936,267),'N42 downstream: '+('ACTIVE' if trial['hidden_nonzero'] else 'ZERO'),11,GREEN if trial['hidden_nonzero'] else RED)
    text(d,(935,294),'24 NON-SENSORY NODES ONLY',11,WHITE)
    panel(d,(922,340,1268,560))
    text(d,(938,349),'LEARNED TEXT / WORLD GATE',13,CYAN)
    final=tick==3
    d.rectangle((939,384,1255,436),fill=(8,34,49),outline=GREEN if final and trial['reward'] else YELLOW,width=2)
    phrase=trial['predicted'] if final else '_  _  _'
    text(d,(947,397),'> '+phrase,16,GREEN if final and trial['reward'] else YELLOW)
    if final:
        text(d,(938,447),'TARGET: '+trial['target'],12,MUTED)
        text(d,(940,477),'GATE: '+trial['gate'],12,GREEN if trial['reward'] else RED)
        text(d,(941,507),'REWARD: '+('1' if trial['reward'] else '0'),13,GREEN if trial['reward'] else RED)
    else:
        text(d,(939,453),'SUPERVISION HIDDEN UNTIL PREDICTION',10,MUTED)
        text(d,(940,486),'PERMITTED LOCAL TEXT ONLY',11,WHITE)
    text(d,(936,534),'PARENT-STATE COPY' if trial['phase']=='offspring_transfer_noise' else 'SOFTWARE TASK / NO HOST AUTHORITY',10,PINK)
    brain_panel(d,data,shot,layout)
    panel(d,(621,570,1268,706))
    text(d,(633,578),'dyn12 + ARCHIVED AUDIO/QPU REPLAY',13,CYAN)
    for i,value in enumerate(shot['dyn12']):
        x=635+i*18;bh=max(1,round(abs(value)*26))
        d.rectangle((x,640-bh,x+11,640),fill=CYAN if value>=0 else PURPLE)
    text(d,(858,596),f'AUDIO SEG {shot["audio_segment"]:>2} DRIVE {shot["audio"]:+.4f}',11,PINK)
    text(d,(858,620),f'QPU {shot["quantum"]:+.4f} {shot["qpu_bits_histogram_surrogate"] or "OFF"}',11,YELLOW)
    text(d,(857,643),'MEMORIAL AUDIO != PHYSIOLOGY',10,WHITE)
    text(d,(857,666),'IBM MARRAKESH / ARCHIVED COUNTS',10,MUTED)
    text(d,(635,671),'NEURAL RELAY REQUIRED FOR NOUN',11,GREEN)
    text(d,(635,690),'NO PROPAGATION = NO OUTPUT',10,RED)
    if trial['phase']=='offspring_transfer_noise' and trial['trial']>=157:
        score=lambda name:f"{summary[name]['novel_noise']['correct']}/{summary[name]['novel_noise']['total']}"
        panel(d,(22,181,905,319))
        text(d,(36,189),'MEASURED / 8 SEEDS / 13,440 TRIALS',14,CYAN)
        text(d,(37,222),'RELAY NO AUX '+score('original_no_aux')+'  AUDIO+QPU '+score('original_audio_qpu'),12,WHITE)
        text(d,(37,247),'REWIRED '+score('rewired_audio_qpu')+'   NO PROP '+score('no_propagation_audio_qpu'),12,WHITE)
        text(d,(37,275),'NEURAL DEPENDENCY != UNIQUE TOPOLOGY ADVANTAGE',11,YELLOW)
    return img


def np_round(v):
    return [round(float(x),6) for x in v]


def render(out=OUT,destination=None,preview=False):
    result,chosen=sources(out);data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    if preview:
        trial=next(t for t in chosen if t['phase']=='novel_noise' and t['reward'])
        frame(trial,trial['snapshots'][3],3,3,100,world,data,layout,result['summary']).save(destination)
        return {'preview':str(destination),'ledger_sha256':result['ledger_sha256']}
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1280x720','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast',
        '-crf','29','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        for k,t in enumerate(chosen):
            for tick,snap in enumerate(t['snapshots']):
                for sub in range(FRAMES_PER_TICK):
                    im=frame(t,snap,tick,sub,count,world,data,layout,result['summary'])
                    proc.stdin.write(im.tobytes());count+=1
            if (k+1)%10==0:print(f'RENDERED {k+1}/{len(chosen)} trials ({count} frames)',flush=True)
        proc.stdin.close();err=proc.stderr.read().decode();rc=proc.wait()
        if rc:raise RuntimeError(f'ffmpeg failed {rc}: {err[-1600:]}')
    except BaseException:
        proc.kill();raise
    manifest={'file':dest.name,'frames':count,'fps':FPS,'duration_seconds':count/FPS,
      'sha256':sha256(dest),'ledger_sha256':result['ledger_sha256'],
      'selection':'80 deterministically sampled trials from five seed-0 phases; source condition original_audio_qpu',
      'camera_validation':'every frame re-rasterizes camera, checks its hash and label-free RGB sensor feature',
      'claim_boundaries':'modeled neural relay with labeled teacher, not biology or live IBM; decorative fly motion only'}
    (out/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true')
    a=p.parse_args();print(json.dumps(render(a.out,a.output,a.preview),indent=2))
