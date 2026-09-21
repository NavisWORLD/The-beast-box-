"""160-episode executed-trace render. No invented fly positions or reward frames."""
from __future__ import annotations
import argparse
import json
import math
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
import render_moving_fly as v
from fly_movement import DATA,load_graph,sha256
from learn_to_forage import ARMS,PHASES

HERE=Path(__file__).resolve().parent
OUT=HERE/'learning_demo'
FPS=8
FRAMES_PER_EPISODE=10
W,H=1280,720
C={'real_wiring_learning':v.CYAN,'rewired_learning':v.VIOLET,
 'no_learning':v.WHITE,'frozen_after_training':v.AMBER}
LABEL={'real_wiring_learning':'REAL WIRING + LEARNING',
 'rewired_learning':'REWIRED + LEARNING','no_learning':'LEARNING OFF','frozen_after_training':'FROZEN AFTER TRAIN'}


def xy(x,y):return (int(94+(x+4.0)/8.0*654),int(575-(y+3.0)/6.0*390))


def anatomy_positions(data):
    groups={'lc4':0,'lplc2':1,'other':2}
    slots={i:[] for i in range(4)}
    for i,r in enumerate(data['roles']):slots[groups.get(r,3)].append(i)
    out={}
    for g,arr in slots.items():
        for j,i in enumerate(arr):out[i]=(844+g*102,173+round(146*(j+.5)/len(arr)))
    return out


def draw_fly(d,x,y,heading,phase,color,large=False):
    px,py=xy(x,y)
    s=1.0 if large else .52
    c=math.cos(-heading); si=math.sin(-heading)
    def pt(u,w):return (round(px+s*(c*u-si*w)),round(py+s*(si*u+c*w)))
    for sign in (-1,1):
        flap=9*math.sin(phase*1.5+sign)
        d.polygon([pt(-4,sign*4),pt(-25-flap,sign*24),pt(-12,sign*14)],fill=(36,71,90),outline=color)
    if large:
        for k in (-1,0,1):
            for sign in (-1,1):
                gait=math.sin(phase*.7+k*2.4+sign)*4
                d.line([pt(k*7,sign*5),pt(k*7-7,sign*(14+gait)),pt(k*7-1,sign*(17+gait))],fill=color,width=2)
    for u,rx,ry in ((-11,13,8),(1,10,8),(15,7,7)):
        cx,cy=pt(u,0);d.ellipse((cx-rx*s,cy-ry*s,cx+rx*s,cy+ry*s),fill=(40,61,77),outline=color,width=2 if large else 1)
    if large:
        for sign in (-1,1):
            cx,cy=pt(17,sign*4);d.ellipse((cx-3,cy-3,cx+3,cy+3),fill=v.AMBER)


def frame_at(frame_index,record,positions,data):
    ep_index=min(159,frame_index//FRAMES_PER_EPISODE)
    sub=frame_index%FRAMES_PER_EPISODE
    main=record['real_wiring_learning'][ep_index]
    phase=main['phase']
    accents={'train':v.CYAN,'heldout_layout':v.GREEN,'reversal':v.AMBER}
    phasecolor=accents[phase]
    im=Image.new('RGB',(W,H),v.BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,1280,7),fill=phasecolor)
    v.text(d,(40,18),'CORY DAVIS   //   BEAST BOX   //   COSMIC FRUIT FLY',20,v.CYAN,True)
    v.text(d,(40,49),'CAN THE FLY LEARN TO FIND FOOD?',32,v.TXT,True)
    v.text(d,(1053,55),f'{frame_index/FPS:05.1f} SEC',16,v.MUTED,mono=True)
    v.rect(d,(40,98,794,636));v.rect(d,(808,98,1240,355));v.rect(d,(808,367,1240,636))
    d.rounded_rectangle((56,112,777,145),radius=8,fill=(21,40,56))
    v.text(d,(67,119),f'EPISODE {ep_index+1:03d} / 160',17,v.TXT,True)
    v.text(d,(287,119),{'train':'TRAIN: REWARD FEEDBACK','heldout_layout':'TEST: UNSEEN STATION POSITIONS','reversal':'REVERSAL: FOOD RULE FLIPS'}[phase],16,phasecolor,True)
    v.text(d,(65,155),'Odor cue:',16,v.MUTED)
    v.text(d,(175,152),'BLUE' if main['cue']==0 else 'GOLD',18,v.CYAN if main['cue']==0 else v.AMBER,True)
    v.text(d,(288,155),'Choose station A or B. Food is revealed ONLY on arrival.',15,v.MUTED)
    for x in range(94,750,55):d.line((x,184,x,576),fill=(26,37,54),width=1)
    for y in range(185,576,48):d.line((94,y,750,y),fill=(26,37,54),width=1)
    # Both stations are visually available but neither reward label is visible before arrival.
    for k,pos in enumerate(main['stations']):
        sx,sy=xy(*pos)
        clr=v.GREEN if sub>=8 and k==main['rewarded_station'] else v.RED if sub>=8 else v.VIOLET if k==0 else v.AMBER
        d.ellipse((sx-22,sy-22,sx+22,sy+22),outline=clr,width=2)
        d.ellipse((sx-12,sy-12,sx+12,sy+12),fill=(36,47,67),outline=clr,width=2)
        v.text(d,(sx-29,sy-53),f'STATION {"A" if k==0 else "B"}',15,clr,True)
    order=('no_learning','frozen_after_training','rewired_learning','real_wiring_learning')
    recs={}
    for arm in order:
        trial=record[arm][ep_index]
        path=trial['trace']
        tick=min(len(path)-1,max(0,int((sub+1)/FRAMES_PER_EPISODE*len(path))-1))
        recs[arm]=(trial,path,tick,path[tick])
        points=[xy(q['x'],q['y']) for q in path[:tick+1]]
        if len(points)>1:d.line(points,fill=C[arm],width=3 if arm=='real_wiring_learning' else 2,joint='curve')
    for arm in order:
        trial,path,tick,p=recs[arm]
        draw_fly(d,p['x'],p['y'],p['heading'],frame_index,C[arm],large=(arm=='real_wiring_learning'))
    for i,arm in enumerate(order[::-1]):
        xx=63+(i%2)*360;yy=581+(i//2)*27
        d.ellipse((xx,yy+3,xx+11,yy+14),fill=C[arm])
        v.text(d,(xx+19,yy),LABEL[arm],15,C[arm],True)
    v.text(d,(826,111),'FLYWIRE-DERIVED 42-NODE CIRCUIT',17,v.TXT,True)
    v.text(d,(827,136),'95 weighted edges | schematic topology',15,v.MUTED)
    for a,b,w in data['edges']:
        x1,y1=positions[a];x2,y2=positions[b]
        d.line((x1,y1,x2,y2),fill=(31,56,70) if w>0 else (61,41,66),width=1)
    neural=recs['real_wiring_learning'][3]['neural']
    for i,(px,py) in positions.items():
        strength=min(1,abs(neural[i]));radius=3+int(strength*4)
        tint=(int(20+47*strength),int(53+146*strength),int(65+174*strength)) if neural[i]>=0 else (int(25+161*strength),int(30+56*strength),int(45+120*strength))
        d.ellipse((px-radius,py-radius,px+radius,py+radius),fill=tint)
    for k,s in enumerate(('LC4','LPLC2','OTHER','DESC.')):
        v.text(d,(837+k*102,330),s,14,v.MUTED)
    v.text(d,(828,380),'ASSOCIATIVE MEMORY / SOFTWARE Q VALUES',17,v.TXT,True)
    v.text(d,(829,407),'Blue odor (0) and gold odor (1): A vs B',15,v.MUTED)
    q=main['q_before'] if sub<8 else main['q_after']
    for row in range(2):
        by=442+row*73
        v.text(d,(829,by),f'CUE {row}',16,v.CYAN if row==0 else v.AMBER,True)
        for station in range(2):
            yy=by+station*20
            v.text(d,(922,yy-2),'A' if station==0 else 'B',15,v.MUTED,True)
            d.rounded_rectangle((945,yy,1150,yy+12),radius=4,fill=(37,49,66))
            d.rounded_rectangle((945,yy,945+max(1,round(205*q[row][station])),yy+12),radius=4,fill=v.CYAN if station==0 else v.VIOLET)
            v.text(d,(1161,yy-5),f'{q[row][station]:.2f}',14,v.TXT,mono=True)
    v.text(d,(828,591),'Canonical dyn12: 12-dimensional runtime state',15,v.MUTED)
    dyn=recs['real_wiring_learning'][3]['dyn12']
    for i,x in enumerate(dyn):
        px=831+i*33;zero=624;bar=round(min(1,abs(x))*22)
        d.rectangle((px,zero-bar,px+20,zero),fill=v.CYAN if x>=0 else v.VIOLET)
    # Per-arm running outcome, actual recorded episode rewards only.
    v.text(d,(43,650),'LAST 20 EPISODES:',16,v.TXT,True)
    for i,arm in enumerate(('real_wiring_learning','no_learning','frozen_after_training')):
        values=[e['reward'] for e in record[arm][max(0,ep_index-19):ep_index+1]]
        rate=sum(values)/len(values)
        x=241+i*335
        v.text(d,(x,650),f'{LABEL[arm].split(" +")[0]}: {rate*100:.0f}%',15,C[arm],True)
    v.text(d,(43,684),f'CURRENT FOOD: {"FOUND" if sub>=8 and main["reward"] else "EMPTY" if sub>=8 else "UNKNOWN"}  |  SELECTED: {"A" if main["choice"]==0 else "B"}  |  REWARD ONLY AT LANDING',15,v.GREEN if sub>=8 and main['reward'] else v.MUTED,True)
    d.rounded_rectangle((954,14,1240,39),radius=5,fill=(78,39,51))
    v.text(d,(966,19),'SIMULATION, NOT REAL ANIMAL',14,(255,223,230),mono=True)
    return im


def main():
    p=argparse.ArgumentParser();p.add_argument('--preview-only',action='store_true');a=p.parse_args()
    results=json.loads((OUT/'results.json').read_text())
    if results['source_data_sha256']!=sha256(DATA) or results['episode_log_sha256']!=sha256(OUT/'all_runs.jsonl'):
        raise RuntimeError('evidence source hash mismatch')
    data=load_graph();raw=[json.loads(x) for x in (OUT/'all_runs.jsonl').read_text().splitlines()]
    record={r['arm']:r['episodes'] for r in raw if r['seed']==0}
    if set(record)!=set(ARMS):raise RuntimeError('missing experimental arm')
    if not all(len(vv)==160 and all('trace' in e and e['trace'] for e in vv) for vv in record.values()):
        raise RuntimeError('missing executed movement traces')
    positions=anatomy_positions(data)
    for name,ix in (('training_preview.png',56),('heldout_preview.png',950),('reversal_preview.png',1400)):
        frame_at(ix,record,positions,data).save(OUT/name)
    if a.preview_only:
        print('Preview files created');return
    video=OUT/'Cosmic_Fruit_Fly_Learning_Experiment_3m20s.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
          '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264',
          '-preset','veryfast','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(160*FRAMES_PER_EPISODE):
            proc.stdin.write(frame_at(i,record,positions,data).tobytes())
            if (i+1)%320==0:print(f'encoded frame {i+1}/1600',flush=True)
        proc.stdin.close()
        error=proc.stderr.read().decode()
        if proc.wait()!=0:raise RuntimeError(error)
    except BaseException:
        proc.kill();raise
    manifest={'video':video.name,'sha256':sha256(video),'fps':FPS,'frames':160*FRAMES_PER_EPISODE,
        'duration_sec':160*FRAMES_PER_EPISODE/FPS,'render_code_sha256':sha256(Path(__file__)),
        'source_data_sha256':sha256(DATA),'episode_log_sha256':sha256(OUT/'all_runs.jsonl'),
        'classification':'rendered playback of actual executed computational traces (seed=0); not a real animal or real-time recording'}
    (OUT/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
