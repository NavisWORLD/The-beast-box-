"""Render actual executed hard-mode camera/neural/text/gate traces to an MP4.

The world art is decorative and NOT the simulator's 96x64 camera. Correct labels
are shown to the viewer only after prediction; no target reaches the decoder.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from fly_movement import HERE,DATA,load_graph,sha256
from quantum_language import DATA as QDATA
from hard_mode import OUT, COLORS, ALL_POS, INTENT_GLYPHS, GLYPHS, GESTURES, INTENTS, observed
from render_build_grow import (ASSET,W,H,NAVY,CYAN,GREEN,WHITE,MUTED,YELLOW,PINK,PURPLE,RED,
        panel,text,coords,fly,graph_layout,brain_panel)
FPS=4
FRAMES_PER_STEP=4
PHASE_LABEL={
    'train':'TEACHER TRAINING', 'retained':'TRAINED PAIRS',
    'novel_noise':'NOVEL + SENSOR DISTRACTORS',
    'reversal_train':'RULE FLIP / RETRAIN',
    'reversal_retained':'REVERSED RETAINED PAIRS',
    'reversal_novel_noise':'REVERSED NOVEL + NOISE',
    'offspring_transfer_noise':'SOFTWARE OFFSPRING TRANSFER'
}
# A selected subset of the executed trace; other trials remain in runs.jsonl.
PHASE_COUNTS={'train':15,'retained':18,'novel_noise':19,'reversal_train':14,
              'reversal_retained':14,'reversal_novel_noise':16,'offspring_transfer_noise':16}


def read_sources():
    result=json.loads((OUT/'results.json').read_text())
    assert sha256(OUT/'runs.jsonl')==result['ledger_sha256'],'ledger changed'
    assert sha256(DATA)==result['source_sha256']['flywire_subset']
    assert sha256(QDATA)==result['source_sha256']['ibm_replay']
    for filename,exp in result['code_sha256'].items():
        if sha256(HERE/filename)!=exp: raise RuntimeError('changed code '+filename)
    runs=[json.loads(s) for s in (OUT/'runs.jsonl').read_text().splitlines()]
    row=next(r for r in runs if r['seed']==0 and r['arm']=='original_replay')
    assert len(row['trace'])==264
    selected=[]
    for phase,n in PHASE_COUNTS.items():
        candidates=[t for t in row['trace'] if t['phase']==phase]
        # Spread representative trials across the whole phase; avoid cherry-picking reward.
        indices=[(len(candidates)-1)*i//(n-1) for i in range(n)]
        selected.extend(candidates[i] for i in indices)
    assert len(selected)==112
    return result,row,selected


def frame(trial,shot,tick,sub,index,world,data,layout):
    im=Image.new('RGB',(W,H),NAVY);im.paste(world,(20,16))
    d=ImageDraw.Draw(im)
    obj=trial['object'];px,py=coords(*trial['pos'])
    d.ellipse((px-24,py-24,px+24,py+24),outline=YELLOW,width=3)
    d.ellipse((px-9,py-9,px+9,py+9),fill=COLORS[obj],outline=WHITE,width=2)
    start=(trial['pos'][0]-1.18,trial['pos'][1]); fx,fy=coords(start[0]+.14*(tick+sub/FRAMES_PER_STEP),start[1])
    d.line((fx,fy,px,py),fill=CYAN,width=2)
    fly(d,fx,fy,0,index,offspring=trial['phase']=='offspring_transfer_noise',scale=1.12)
    text(d,(px-29,py-43),obj.upper(),11,YELLOW)
    panel(d,(23,17,683,89))
    text(d,(37,25),'* COSMIC FRUIT FLY  /  HARD MODE',18,CYAN)
    text(d,(38,57),f'TRIAL {trial["trial"]+1:03d}/264 | {PHASE_LABEL[trial["phase"]]}',12,WHITE)
    panel(d,(24,98,665,165))
    text(d,(36,107),'TASK: DECODE 3 TOKENS -> OPEN RESOURCE GATE',14,CYAN)
    text(d,(37,137),f'{obj.upper():<8} {trial["gesture"].upper():<9} {trial["intent"].upper():<8}',13,YELLOW)
    # Verify exact visual observation used during this saved tick; no synthetic re-animation of brain.
    rgbfeat,rgb=observed(obj,GESTURES.index(trial['gesture']),INTENTS.index(trial['intent']),
        'noisy' if trial['noisy_camera'] else 'clean',trial['trial']%3)
    if hashlib.sha256(rgb.tobytes()).hexdigest()!=trial['camera_sha256']:
        raise RuntimeError('camera replay hash mismatch '+str(trial['trial']))
    if [list(t) for t in rgbfeat]!=trial['features']:
        raise RuntimeError('feature replay mismatch '+str(trial['trial']))
    panel(d,(924,15,1267,220));text(d,(938,23),'FLY VIRTUAL CAMERA / 96x64',13,CYAN)
    im.paste(Image.fromarray(rgb,'RGB').resize((291,151),Image.Resampling.NEAREST),(943,55))
    d=ImageDraw.Draw(im)
    text(d,(938,204),'NOISY VISION: '+('ON' if trial['noisy_camera'] else 'OFF'),11,PINK if trial['noisy_camera'] else GREEN)
    panel(d,(924,227,1267,331))
    text(d,(938,233),'SENSORY SYMBOL CHANNELS',13,CYAN)
    for n,col in enumerate((rgbfeat[0],rgbfeat[1],rgbfeat[2])):
        x=944+91*n;d.rectangle((x,267,x+29,294),fill=tuple(col),outline=WHITE,width=2)
    text(d,(944,304),'OBJECT    GESTURE     INTENT',10,MUTED)
    panel(d,(924,338,1267,561))
    text(d,(938,346),'IN-MEMORY TEXT / WORLD GATE',13,CYAN)
    final=tick==3
    text(d,(939,371),'PREDICTION:',11,MUTED)
    d.rectangle((938,392,1255,433),fill=(9,30,44),outline=CYAN,width=2)
    words=trial['predicted'] if final else '_  _  _'
    text(d,(948,400),'> '+words,18,GREEN if final and trial['reward'] else YELLOW)
    text(d,(940,443),'TEACHER: '+('AFTER PREDICTION' if trial['teacher_feedback_provided'] else 'NO TEST FEEDBACK'),10,PINK if trial['teacher_feedback_provided'] else GREEN)
    if final:
        text(d,(939,466),'EVAL TARGET: '+trial['target'],12,WHITE)
        text(d,(939,491),'GATE: '+trial['gate'],12,GREEN if trial['reward'] else RED)
        text(d,(939,517),'RESOURCE: '+('UNLOCKED' if trial['reward'] else 'LOCKED'),13,GREEN if trial['reward'] else RED)
    else:
        text(d,(939,474),'TARGET HIDDEN FROM DECODER',11,MUTED)
        text(d,(939,502),'CHECKED ONLY AFTER OUTPUT',10,MUTED)
    brain_panel(d,data,shot,layout)
    panel(d,(621,570,1267,705))
    text(d,(634,580),'dyn12   /   HISTORICAL IBM REPLAY',13,CYAN)
    for i,v in enumerate(shot['dyn12']):
        bh=round(abs(v)*31);x=635+19*i
        if bh:d.rectangle((x,637-bh,x+12,637),fill=CYAN if v>=0 else PURPLE)
    text(d,(636,650),f'QUANTUM DRIVE: {shot["quantum"]:+.5f}   SOURCE: REPLAY, NOT LIVE',10,YELLOW)
    text(d,(635,675),'REAL-DERIVED EDGES / SIMULATED FIRING / TEACHER-SUPERVISED TEXT',10,MUTED)
    return im


def render(output:Path,preview=False):
    result,row,trials=read_sources();data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    output.parent.mkdir(parents=True,exist_ok=True)
    if preview:
        chosen=next(t for t in trials if t['phase']=='offspring_transfer_noise')
        frame(chosen,chosen['snapshots'][-1],3,3,0,world,data,layout).save(output)
        return {'preview':str(output)}
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
         '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an',
         '-c:v','libx264','-preset','ultrafast','-crf','29','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        for k,t in enumerate(trials):
            for tick,shot in enumerate(t['snapshots']):
                for sub in range(FRAMES_PER_STEP):
                    img=frame(t,shot,tick,sub,count,world,data,layout)
                    p.stdin.write(img.tobytes());count+=1
            if (k+1)%10==0:print('rendered',k+1,'of',len(trials),'frames',count,flush=True)
        p.stdin.close();err=p.stderr.read().decode();rc=p.wait()
        if rc: raise RuntimeError('ffmpeg failed: '+err[-2000:])
    except BaseException:
        p.kill();raise
    manifest={'frames':count,'fps':FPS,'duration_seconds':count/FPS,'sha256':sha256(output),
        'ledger_sha256':result['ledger_sha256'],'selection':'112 deterministic evenly spaced trials across seven phases from full 264-trial seed-0 primary run',
        'warning':'rendered simulation, fixed grammar, simulated sensors; no live QPU or physical fruit fly'}
    (OUT/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--preview',action='store_true');a=ap.parse_args()
    print(json.dumps(render(a.output,a.preview),indent=2))
