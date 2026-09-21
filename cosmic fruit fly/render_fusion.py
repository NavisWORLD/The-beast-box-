"""Polished pixel-art video of a verified executed fusion trace.

World art and particles are DECORATIVE. A different 96x64 pixel raster is the
actual virtual retina used by the experiment. Each trial's camera SHA must match.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from fly_movement import HERE, DATA, load_graph, sha256
from hard_mode import GESTURES,INTENTS,COLORS,ALL_POS
from fusion_hard_mode import OUT, PHASES, camera_observation, MOCK_BIO_ID
from render_build_grow import (ASSET,W,H,NAVY,CYAN,GREEN,WHITE,MUTED,YELLOW,PINK,PURPLE,RED,
    panel,text,coords,fly,graph_layout,brain_panel)

FPS=4
FRAMES_PER_TICK=4
PHASE_COUNTS={'train':38,'novel_noise':21,'reversal_train':32,
              'reversal_novel_noise':19,'offspring_transfer_noise':16}
PHASE_LABEL={'train':'SUPERVISED TRAINING','novel_noise':'HELD-OUT / OCCLUDED',
             'reversal_train':'RULE REVERSAL / TRAIN',
             'reversal_novel_noise':'REVERSED HELD-OUT','offspring_transfer_noise':'SOFTWARE OFFSPRING'}


def sources(out=OUT):
    r=json.loads((out/'results.json').read_text())
    if sha256(out/'runs.jsonl')!=r['ledger_sha256'] or sha256(DATA)!=r['source_sha256']['flywire_subset']:
        raise RuntimeError('source or ledger hash mismatch')
    for n,expected in r['code_sha256'].items():
        if sha256(HERE/n)!=expected:raise RuntimeError('experiment code changed: '+n)
    rows=[json.loads(line) for line in (out/'runs.jsonl').read_text().splitlines()]
    a=next(v for v in rows if v['seed']==0 and v['arm']=='mock_fusion')
    assert len(a['trace'])==168
    chosen=[]
    for phase,n in PHASE_COUNTS.items():
        candidates=[x for x in a['trace'] if x['phase']==phase]
        assert len(candidates)>=n
        chosen.extend(candidates[(len(candidates)-1)*i//(n-1)] for i in range(n))
    assert len(chosen)==126
    return r,rows,chosen


def render_frame(trial,shot,tick,sub,frame_no,world,data,layout):
    im=Image.new('RGB',(W,H),NAVY);im.paste(world,(20,16));d=ImageDraw.Draw(im)
    obj=trial['object'];px,py=coords(*trial['pos'])
    t=(frame_no%56)/56*math.tau
    # Original executable layer: sprite motion, pulsing highlights, reflective water, and particles.
    glow=round(12+3*math.sin(t))
    for rad in (glow+15,glow+5):
        d.ellipse((px-rad,py-rad,px+rad,py+rad),outline=(238,190,89),width=1)
    d.ellipse((px-8,py-8,px+8,py+8),fill=COLORS[obj],outline=WHITE,width=2)
    for p in range(12):
        dx=(p*137+frame_no*2)%883
        dy=(p*79+frame_no*(p%3+1))%490
        x=33+dx;y=38+dy
        if 165<x<862 and 173<y<549:
            d.point((x,y),fill=(234,244,161) if p%3==0 else (109,224,210))
    start=(trial['pos'][0]-1.18,trial['pos'][1]);progress=(tick+sub/FRAMES_PER_TICK)/4
    fx,fy=coords(start[0]+.66*progress,start[1]+.035*math.sin(t))
    d.line((fx,fy,px,py),fill=(81,201,225),width=1)
    for p in range(5):
        x=fx+round(17*math.cos(t+p*math.tau/5)); y=fy+round(13*math.sin(t+p*math.tau/5))
        d.point((x,y),fill=(243,226,142))
    fly(d,fx,fy,0,frame_no,offspring=trial['phase']=='offspring_transfer_noise',scale=1.16)
    text(d,(px-36,py-42),obj.upper(),12,YELLOW)
    panel(d,(21,14,712,90))
    text(d,(35,23),'COSMIC FRUIT FLY  /  BIO x QUANTUM',18,CYAN)
    text(d,(37,59),f'SEED 01 / 08   |   {PHASE_LABEL[trial["phase"]]}   |   TRIAL {trial["trial"]+1:03d}/168',11,WHITE)
    panel(d,(23,100,704,171))
    text(d,(36,107),'TASK  //  DECODE 3 SYMBOLS TO UNLOCK RESOURCE',14,CYAN)
    text(d,(36,141),f'OBJECT {obj.upper():<9}  GESTURE {trial["gesture"].upper():<10} INTENT {trial["intent"].upper()}',12,YELLOW)
    feat,margin,hsh,rgb=camera_observation(obj,GESTURES.index(trial['gesture']),
                               INTENTS.index(trial['intent']),trial['seed'],trial['trial'],trial['noisy_camera'])
    if hsh!=trial['camera_sha256'] or [list(z) for z in feat]!=trial['features']:
        raise RuntimeError(f'virtual retinal trace mismatch {trial["trial"]}')
    panel(d,(923,15,1268,221))
    text(d,(938,23),'FLY VIRTUAL RETINA / 96x64',13,CYAN)
    im.paste(Image.fromarray(rgb,'RGB').resize((302,144),Image.Resampling.NEAREST),(940,53))
    d=ImageDraw.Draw(im)
    text(d,(939,202),'PIXELS, NOT DECORATIVE WORLD ART',10,MUTED)
    panel(d,(923,228,1268,330))
    text(d,(937,234),'SENSING / DECISION CONFIDENCE',12,CYAN)
    for y,label,val,col in ((263,'PIXEL MARGIN',trial['margin'],YELLOW),
                            (292,'NEURAL GATE',trial['confidence'],CYAN)):
        text(d,(938,y),label,10,WHITE)
        d.rectangle((1052,y,1192,y+11),fill=(34,55,69))
        d.rectangle((1052,y,1052+round(140*max(0,min(1,val))),y+11),fill=col)
        text(d,(1199,y),f'{val:.2f}',10,col)
    panel(d,(923,338,1268,561))
    text(d,(937,346),'SANDBOX TEXT / WORLD GATE',13,CYAN)
    final=tick==3
    d.rectangle((939,381,1256,428),fill=(7,34,48),outline=GREEN if final and trial['reward'] else YELLOW,width=2)
    phrase=trial['predicted'] if final else '_  _  _'
    text(d,(949,391),'> '+phrase,16,GREEN if final and trial['reward'] else YELLOW)
    if final:
        text(d,(938,442),'EXPECTED: '+trial['target'],12,MUTED)
        text(d,(939,472),'GATE: '+trial['gate'],12,GREEN if trial['reward'] else RED)
        text(d,(939,499),'RESOURCE: '+('UNLOCKED' if trial['reward'] else 'LOCKED'),14,GREEN if trial['reward'] else RED)
    else:
        text(d,(939,449),'TEACHER LABEL HIDDEN UNTIL OUTPUT',10,MUTED)
        text(d,(939,482),'RESULT ONLY AFTER DECISION',12,YELLOW)
    text(d,(938,532),'SIMULATED OFFSPRING' if trial['phase']=='offspring_transfer_noise' else 'PERMISSIONED LOCAL TEXT ONLY',10,PINK)
    brain_panel(d,data,shot,layout)
    panel(d,(621,570,1268,706))
    text(d,(633,578),'CST/dyn12  +  INDEPENDENT AUXILIARY CHANNELS',13,CYAN)
    for i,value in enumerate(shot['dyn12']):
        x=635+i*18;bh=max(1,round(abs(value)*25))
        d.rectangle((x,639-bh,x+11,639),fill=CYAN if value>=0 else PURPLE)
    text(d,(860,612),'BIO (SIMULATED)',11,PINK)
    text(d,(860,631),f'{shot["bio"]:+.5f}   NOT VERIFIED PHYSIOLOGY',10,WHITE)
    text(d,(860,653),'IBM (HISTORICAL)',11,YELLOW)
    text(d,(860,672),f'{shot["quantum"]:+.5f}   REPLAY, NOT LIVE',10,WHITE)
    text(d,(634,668),'N42 READOUT',10,MUTED)
    text(d,(634,685),f'{trial["readout"]:+.5f}  /  {trial["arm"].upper()}',10,WHITE)
    # The closing overlay summarizes the measured matched arms, not an invented
    # per-frame comparison. Only show it during the final sampled trials.
    if trial['phase']=='offspring_transfer_noise' and trial['trial']>=160:
        r=json.loads((OUT/'results.json').read_text())['summary']
        score=lambda arm: f"{r[arm]['novel_noise']['correct']}/{r[arm]['novel_noise']['total']}"
        panel(d,(22,181,904,319))
        text(d,(36,191),'MEASURED ABLATIONS / 8 SEEDS / 16,128 TRIALS',14,CYAN)
        text(d,(37,223),'BASELINE '+score('baseline')+'      IBM REPLAY '+score('quantum_only'),13,WHITE)
        text(d,(37,249),'MOCK BIO '+score('mock_bio_only')+'      MOCK FUSION '+score('mock_fusion'),13,WHITE)
        text(d,(37,277),'REAL BIO: NOT EXECUTED  /  NO ESTABLISHED PERFORMANCE BENEFIT',11,YELLOW)
    return im


def render(out=OUT,destination=None,preview=False):
    result,rows,selected=sources(out)
    data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    if preview:
        candidate=next(t for t in selected if t['phase']=='offspring_transfer_noise')
        render_frame(candidate,candidate['snapshots'][3],3,3,720,world,data,layout).save(destination)
        return {'preview':str(destination),'ledger_sha256':result['ledger_sha256']}
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1280x720','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast',
        '-crf','29','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        for k,t in enumerate(selected):
            for tick,snap in enumerate(t['snapshots']):
                for sub in range(FRAMES_PER_TICK):
                    im=render_frame(t,snap,tick,sub,count,world,data,layout)
                    proc.stdin.write(im.tobytes());count+=1
            if (k+1)%10==0:print(f'RENDERED {k+1}/{len(selected)} trials; {count} frames',flush=True)
        proc.stdin.close();err=proc.stderr.read().decode();rc=proc.wait()
        if rc:raise RuntimeError(f'ffmpeg exit {rc}: {err[-1600:]}')
    except BaseException:
        proc.kill();raise
    manifest={'file':dest.name,'frames':count,'fps':FPS,'duration_seconds':count/FPS,
        'sha256':sha256(dest),'ledger_sha256':result['ledger_sha256'],
        'selection':'126 deterministic evenly spaced trials across five phases of seed-0 mock-fusion run',
        'camera_validation':'each image regenerated from actual virtual camera and sha256 checked',
        'boundaries':'mock bio, historic QPU-summary replay, modeled neural activity; NOT live animal or physiology'}
    (out/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true')
    args=p.parse_args();print(json.dumps(render(args.out,args.output,args.preview),indent=2))
