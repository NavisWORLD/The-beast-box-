"""Video renderer of saved compositional language trial traces.

The rendered moving fly follows measured *simulator* pose snapshots generated
by learn_compositional_text.trial_steps. Teacher labels shown in evaluation UI
are drawn AFTER prediction and were not available to the fly's observations.
The forest art is DECORATIVE, not the 96x64 virtual camera raster.
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from fly_movement import HERE, DATA, load_graph, sha256
from sandbox_ecology import POSITIONS, PALETTE
from learn_compositional_text import OUT, QDATA, sense_pixels, extract_features, NOUNS, GESTURES
from render_build_grow import (ASSET, W, H, NAVY, CYAN, GREEN, WHITE, MUTED, YELLOW, PINK,
   PURPLE, RED, panel, text, coords, fly, graph_layout, brain_panel)

FPS=4
FRAMES_PER_TICK=4
PHASE_LABEL={'train':'TEACH', 'retained':'KNOWN PAIRS', 'novel':'UNSEEN PAIRS',
             'reversal_train':'TEACH REVERSED CODE', 'reversal_retained':'KNOWN REVERSED PAIRS',
             'reversal_novel':'UNSEEN REVERSED PAIRS'}


def get_sources():
    result=json.loads((OUT/'results.json').read_text())
    if sha256(OUT/'runs.jsonl')!=result['ledger_sha256']:
        raise RuntimeError('experiment ledger checksum mismatch')
    if sha256(DATA)!=result['source_sha256']['flywire_derived_subset'] or sha256(QDATA)!=result['source_sha256']['ibm_nine_replay']:
        raise RuntimeError('source data checksum mismatch')
    for name,expected in result['code_sha256'].items():
        if sha256(HERE/name)!=expected:
            raise RuntimeError('code changed after experiment: '+name)
    runs=[json.loads(s) for s in (OUT/'runs.jsonl').read_text().splitlines()]
    chosen=[r for r in runs if r['seed']==0 and r['arm']=='original_replay']
    if len(chosen)!=1 or len(chosen[0]['trace'])!=60:
        raise RuntimeError('expected exactly 60 recorded language tasks')
    return result, chosen[0]


def frame_for_trial(trial,step,idx,sub,data,layout,world,stats,frame):
    image=Image.new('RGB',(W,H),NAVY)
    image.paste(world,(20,16))
    d=ImageDraw.Draw(image)
    px,py=step['pose']; nx,ny=px,py
    if idx<6:
        nextpose=trial['snapshots'][idx+1]['pose']
        nx=px*(1-sub/FRAMES_PER_TICK)+nextpose[0]*(sub/FRAMES_PER_TICK)
        ny=py*(1-sub/FRAMES_PER_TICK)+nextpose[1]*(sub/FRAMES_PER_TICK)
    object_xy=POSITIONS[trial['noun']]
    tx,ty=coords(*object_xy); x,y=coords(nx,ny)
    d.ellipse((tx-20,ty-20,tx+20,ty+20),outline=YELLOW,width=3)
    d.ellipse((tx-8,ty-8,tx+8,ty+8),fill=PALETTE[trial['noun']],outline=WHITE,width=2)
    d.line([(x,y),(tx,ty)],fill=CYAN,width=2)
    fly(d,x,y,0,frame,scale=1.10)
    panel(d,(23,17,684,89))
    text(d,(37,25),'* COSMIC FRUIT FLY  // LEARN TO TYPE',18,CYAN)
    text(d,(38,57),f'TRIAL {trial["trial"]+1:02d}/60   {PHASE_LABEL[trial["phase"]]}   LIVE SIM REPLAY',12,WHITE)
    panel(d,(24,98,615,165))
    text(d,(37,106),'OBJECTIVE: LEARN SYMBOL + GESTURE -> TWO WORDS',14,CYAN)
    text(d,(37,137),f'OBJECT: {trial["noun"].upper():<7}   GLYPH: {trial["gesture"].upper():<9}',13,YELLOW)
    # Environment-derived camera input is rerasterized and feature-checked.
    retina,glyph=sense_pixels(trial['noun'],tuple(step['pose']),GESTURES.index(trial['gesture']))
    feature=extract_features(retina,glyph)
    if tuple(feature[0])!=tuple(step['color_rgb']) or tuple(feature[1])!=tuple(step['glyph_rgb']):
        raise RuntimeError(f'camera/glyph mismatch at trial {trial["trial"]} tick {idx}')
    panel(d,(924,15,1267,210))
    text(d,(938,23),'VIRTUAL FLY CAMERA / 96x64',13,CYAN)
    image.paste(Image.fromarray(retina,'RGB').resize((288,142),Image.Resampling.NEAREST),(945,54))
    d=ImageDraw.Draw(image)
    panel(d,(924,214,1267,321))
    text(d,(938,220),'PIXEL INPUT / GESTURE GLYPH',13,CYAN)
    d.rectangle((944,253,978,287),fill=tuple(step['color_rgb']),outline=WHITE,width=2)
    d.rectangle((992,253,1026,287),fill=tuple(step['glyph_rgb']),outline=WHITE,width=2)
    text(d,(1040,252),'RGB ONLY',13,WHITE)
    text(d,(938,300),'NO LABEL / REWARD IN CAMERA',10,MUTED)
    panel(d,(924,327,1267,562))
    text(d,(938,335),'SANDBOX TERMINAL / LOCAL ONLY',13,CYAN)
    reveal=idx==6
    text(d,(939,364),'INPUT: OBJECT + GESTURE',11,MUTED)
    d.rectangle((939,389,1251,435),fill=(7,34,43),outline=CYAN,width=2)
    pred=trial['prediction'] if reveal else '_ _'
    text(d,(948,400),'> '+pred,20,GREEN if reveal and trial['reward'] else YELLOW)
    text(d,(940,445),'FEEDBACK: '+('TEACHER AFTER PREDICTION' if trial['teacher_feedback_provided'] else 'NONE; HELD OUT'),11,PINK if trial['teacher_feedback_provided'] else GREEN)
    if reveal:
        text(d,(939,470),'TRUTH (EVAL ONLY): '+trial['target'],12,WHITE)
        text(d,(939,494),'GATE: '+trial['approved'],11,GREEN if trial['reward'] else RED)
        text(d,(939,520),'CORRECT: '+('YES' if trial['reward'] else 'NO'),13,GREEN if trial['reward'] else RED)
    else:
        text(d,(939,473),'REWARD IS HIDDEN UNTIL OUTPUT',11,MUTED)
    # Existing graph renderer draws observed 42-state trace; no interpolated neurons.
    brain_panel(d,data,{'neural':step['neural']},layout)
    panel(d,(622,570,1267,705))
    text(d,(634,579),'dyn12  |  HISTORICAL QPU SUMMARY INPUT',13,CYAN)
    for i,v in enumerate(step['dyn12']):
        bh=round(abs(v)*31)
        xx=637+19*i
        d.rectangle((xx,640-bh,xx+11,640),fill=CYAN if v>=0 else PINK)
    text(d,(637,650),'Q DRIVE: '+f'{step["quantum"]:+.5f}'+'  |  IBM REPLAY, NOT LIVE',10,YELLOW)
    text(d,(635,675),'PIXEL ART DECORATIVE / NETWORK DYNAMICS ASSUMED / TEXT SUPERVISED',10,MUTED)
    return image


def render(out:Path,preview=False):
    result,run=get_sources()
    out.parent.mkdir(parents=True,exist_ok=True)
    data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    first=run['trace'][0]
    if preview:
        img=frame_for_trial(run['trace'][30],run['trace'][30]['snapshots'][-1],6,0,data,layout,world,result['summary']['original_replay'],0)
        img.save(out)
        return {'preview':str(out)}
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y', '-f','rawvideo','-pix_fmt','rgb24',
       '-s',f'{W}x{H}', '-r',str(FPS),'-i','pipe:0','-an',
       '-c:v','libx264','-preset','ultrafast','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        for trial in run['trace']:
            for i,step in enumerate(trial['snapshots']):
                for sub in range(FRAMES_PER_TICK):
                    image=frame_for_trial(trial,step,i,sub,data,layout,world,result['summary']['original_replay'],count)
                    p.stdin.write(image.tobytes());count+=1
            if trial['trial']%12==11:
                print('rendered_trials',trial['trial']+1,'frames',count,flush=True)
        p.stdin.close()
        err=p.stderr.read().decode();rc=p.wait()
        if rc:raise RuntimeError('FFMPEG: '+err[-4000:])
    except BaseException:
        p.kill()
        raise
    manifest={'frames':count,'fps':FPS,'duration_seconds':count/FPS,'sha256':sha256(out),
      'experiment_ledger_sha256':result['ledger_sha256'],'type':'rendered deterministic simulation replay; NOT live camera/QPU',
      'notes':'Teacher target displayed only on end-of-trial evaluation frame; text is supervised TWO TOKEN composition'}
    (OUT/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--preview',action='store_true')
    a=ap.parse_args();print(json.dumps(render(a.output,a.preview),indent=2))
