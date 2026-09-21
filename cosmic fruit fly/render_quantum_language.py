"""Evidence-bound >7min simulation replay: visible 42, historic quantum, sandbox text.

Rendering can interpolate pose but may not invent new brain/sensor measurements.
Video is not live IBM or biological camera footage. Decorative forest not sensor input.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from fly_movement import HERE, DATA, load_graph, sha256
from render_build_grow import (ASSET, W,H,NAVY,CYAN,YELLOW,GREEN,PURPLE,WHITE,MUTED,PINK,
    panel,text, graph_layout,world_and_ui)
from sandbox_ecology import retinal_image,interpret_retina,POSITIONS
from run_quantum_language import OUT
from quantum_language import DATA as QDATA
FPS=6
FRAMES_PER_TICK=2


def overlay(img,step,run,source_frame):
    d=ImageDraw.Draw(img)
    # Replace only lower-right readout. The original lower-left live 42 graph
    # and world/camera remain from source-verified existing renderer.
    panel(d,(622,570,1267,705))
    text(d,(635,579),'HISTORICAL IBM REPLAY   /   SANDBOX TYPING',14,CYAN)
    text(d,(635,601),'JOB: '+str(step['quantum_job'] or 'OFF')[:20],11,WHITE)
    text(d,(950,601),f'Q DRIVE: {step["quantum_value"]:+.5f}',11,YELLOW)
    d.rectangle((639,626,1260,660),fill=(14,35,54),outline=(57,138,155))
    words=step['world'].get('typed_words',[])
    now=' '.join(words[-38:])
    # Keep the most recent words and wrap two lines; no new tokens.
    while len(now)>90:now=now[now.find(' ')+1:]
    text(d,(644,629),('> '+now[:64]) if now else '> _',12,GREEN)
    if len(now)>64:text(d,(644,644),'  '+now[64:],10,GREEN)
    text(d,(636,669),'FLYWIRE ANATOMY | VIRTUAL SENSORS | NO RECORDED BIO PACKET',10,MUTED)
    text(d,(636,687),'IBM HISTORICAL SUMMARY ONLY | NO LIVE QPU | NOT LEARNED LANGUAGE',10,PINK)
    panel(d,(23,17,548,89))
    text(d,(37,26),'* COSMIC FRUIT FLY  // Q+TEXT',18,CYAN)
    text(d,(39,58),f'SEED {run["seed"]+1}/6 | TICK {step["tick"]+1:03d}/{run["steps"]} | TRACE REPLAY',12,WHITE)
    return img


def run(start,end,target,preview=False):
    result=json.loads((OUT/'results.json').read_text())
    if sha256(OUT/'runs.jsonl')!=result['ledger_sha256'] or sha256(QDATA)!=result['quantum_derived_file_sha256'] or sha256(DATA)!=result['anatomy_data_sha256']:
        raise RuntimeError('evidence source has changed; fail closed')
    for file,digest in result['code_sha256'].items():
        if sha256(HERE/file)!=digest:raise RuntimeError('code changed since run: '+file)
    raw=[json.loads(s) for s in (OUT/'runs.jsonl').read_text().splitlines()]
    runs=sorted([r for r in raw if r['experiment_arm']=='real_quantum_typing' and start<=r['seed']<end],key=lambda r:r['seed'])
    if len(runs)!=end-start:raise ValueError('missing replay traces')
    data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    expected=sum(len(r['trace'])*FRAMES_PER_TICK for r in runs)
    if preview:
        r=runs[0];step=r['trace'][min(140,len(r['trace'])-1)]
        frame=overlay(world_and_ui(step,r,world,data,layout,0),step,r,0)
        target.parent.mkdir(parents=True,exist_ok=True);frame.save(target)
        print('PREVIEW',target)
        return {'preview':str(target)}
    target.parent.mkdir(parents=True,exist_ok=True)
    args=['ffmpeg','-hide_banner','-loglevel','error','-y',
      '-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0',
      '-an','-c:v','libx264','-preset','ultrafast','-crf','27','-r','24','-pix_fmt','yuv420p',
      '-movflags','+faststart',str(target)]
    process=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    n=0
    try:
        for r in runs:
            for i,step in enumerate(r['trace']):
                shown={name:POSITIONS[name] for name in step['shown']}
                if interpret_retina(retinal_image(step['sensor_pose'][:2],step['sensor_pose'][2],shown))!=step['vision']:
                    raise RuntimeError('camera mismatch on tick '+str(step['tick']))
                after=r['trace'][i+1] if i+1<len(r['trace']) and r['trace'][i+1]['stage']==step['stage'] else None
                for s in range(FRAMES_PER_TICK):
                    fr=overlay(world_and_ui(step,r,world,data,layout,n,s/FRAMES_PER_TICK,after),step,r,n)
                    process.stdin.write(fr.tobytes());n+=1
            print('RENDERED SEED',r['seed'],'total_frames',n,flush=True)
        process.stdin.close()
        stderr=process.stderr.read().decode()
        rc=process.wait()
        if rc:raise RuntimeError('FFmpeg error: '+stderr[-2500:])
    except BaseException:
        process.kill();raise
    if n!=expected:raise RuntimeError('wrong frame count')
    return {'frames':n,'seconds':n/FPS,'file':str(target),'sha256':sha256(target)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=3)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.start,a.end,a.output,a.preview),indent=2))
