"""Render executed real-connectivity-subset movement traces; not a camera recording."""
from __future__ import annotations
import argparse
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fly_movement import DATA, load_graph, sha256

HERE=Path(__file__).resolve().parent
W,H,FPS=1280,720,12
BG=(8,12,27); PANEL=(15,24,42); LINE=(37,56,80); TXT=(238,247,255)
MUTED=(163,182,205); CYAN=(69,226,251); VIOLET=(188,137,252)
AMBER=(252,185,90); WHITE=(201,213,225); GREEN=(95,238,174); RED=(253,103,128)
COL={'published_subset':CYAN,'weight_matched_rewire':VIOLET,'25pct_lesion':AMBER,'no_propagation':WHITE}
NAMES={'published_subset':'ORIGINAL WIRING','weight_matched_rewire':'REWIRED','25pct_lesion':'25% LESION','no_propagation':'NO PROPAGATION'}
FR='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FM='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT={('regular',s):ImageFont.truetype(FR,s) for s in [14,15,16,17,18,20,22,26,30]}
FONT.update({('bold',s):ImageFont.truetype(FB,s) for s in [15,16,17,18,19,20,22,28,32,37]})
FONT.update({('mono',s):ImageFont.truetype(FM,s) for s in [14,16,18]})

def text(d,xy,msg,size=18,color=TXT,bold=False,mono=False):
    f=FONT[('mono' if mono else 'bold' if bold else 'regular',size)]
    d.text(xy,str(msg),fill=color,font=f)

def rect(d,xy,fill=PANEL,r=16,outline=LINE):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=2)

def mapxy(x,y): return (int(96+(x+4.2)/8.4*663),int(604-(y+2.45)/4.9*425))

def fpoly(d,pts,fill,outline=None,width=2):
    d.polygon(pts,fill=fill)
    if outline:d.line(pts+[pts[0]],fill=outline,width=width,joint='curve')

def fly(d,x,y,theta,phase,color,primary=True):
    cx,cy=mapxy(x,y)
    scale=1.0 if primary else .47
    c,s=math.cos(-theta),math.sin(-theta)
    def tr(u,v):return (round(cx+scale*(c*u-s*v)),round(cy+scale*(s*u+c*v)))
    def ellipse_center(u,v,rx,ry,fill,outline=None):
        X,Y=tr(u,v)
        d.ellipse((X-rx*scale,Y-ry*scale,X+rx*scale,Y+ry*scale), fill=fill,outline=outline,width=2 if primary else 1)
    for side in (-1,1):
        flutter=math.sin(phase*.9+side)*13
        wing=[tr(-6,side*7),tr(-38-flutter,side*34),tr(-8,side*18)]
        fpoly(d,wing,fill=(42,93,122) if primary else (27,58,77),outline=color,width=2 if primary else 1)
    if primary:
        for j in range(3):
            for side in (-1,1):
                px=-10+j*7
                gait=math.sin(phase*.62+j*math.pi+side*math.pi)*6
                d.line([tr(px,side*7),tr(px-9,side*(19+gait)),tr(px-1,side*(23+gait))],fill=color,width=2)
    ellipse_center(-12,0,18,11,(39,71,94),color)
    ellipse_center(2,0,14,10,(52,90,110),color)
    ellipse_center(20,0,10,10,(50,70,77),color)
    if primary:
        for side in [-1,1]:
            ellipse_center(23,side*5,4,4,AMBER)
            d.line([tr(27,side*4),tr(36,side*8)],fill=WHITE,width=2)
    d.line([tr(-3,0),tr(17,0)],fill=color,width=2)

def nodecoords(data):
    # Positions are a schematic by role, NOT reconstructed neuron coordinates.
    role_cols={'lc4':0,'lplc2':1,'other':2,'gf':3,'escw':3,'dnp09':3,'dna01':3,'dna02':3,'mdn':3}
    slots={i:[] for i in range(4)}
    for i,r in enumerate(data['roles']):slots[role_cols[r]].append(i)
    pos={}
    for col,arr in slots.items():
        for row,i in enumerate(arr):
            pos[i]=(856+col*106, 216+round((row+.5)/(len(arr))*207))
    return pos

def render_frame(index,frames,runs,data,positions):
    tick=min(len(runs['published_subset'])-1, int(index*len(runs['published_subset'])/frames))
    p={k:v[tick] for k,v in runs.items()}
    primary=p['published_subset']
    img=Image.new('RGB',(W,H),BG)
    d=ImageDraw.Draw(img)
    d.rectangle((0,0,W,8),fill=CYAN)
    text(d,(42,20),'CORY DAVIS   //   BEAST BOX   //   COSMIC FRUIT FLY',20,CYAN,True)
    text(d,(42,52),'THE FLY MOVES',37,TXT,True)
    text(d,(440,65),'REAL FLYWIRE WIRING  +  MODELED BEHAVIOR',17,AMBER,True)
    rect(d,(40,117,804,651))
    rect(d,(822,117,1240,453))
    rect(d,(822,465,1240,651))
    text(d,(62,131),'2D VIRTUAL ARENA  /  4 MATCHED CONTROLLERS',18,TXT,True)
    text(d,(63,157),'Animated flies = executed positions. Target = green beacon.',15,MUTED)
    # subtle movement floor grid
    for xx in range(96,763,56):d.line((xx,184,xx,610),fill=(26,36,54),width=1)
    for yy in range(184,611,54):d.line((96,yy,764,yy),fill=(26,36,54),width=1)
    # target / obstacle
    cx,cy=mapxy(3.3,1.15)
    for rad in (18,34,50):d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),outline=(40,93,79),width=2)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=GREEN)
    text(d,(cx-34,cy-72),'BEACON',15,GREEN,True)
    ox,oy=mapxy(0,.6)
    d.ellipse((ox-45,oy-45,ox+45,oy+45),fill=(73,43,61),outline=RED,width=2)
    d.line((ox-19,oy-19,ox+19,oy+19),fill=RED,width=3)
    d.line((ox+19,oy-19,ox-19,oy+19),fill=RED,width=3)
    text(d,(ox-34,oy+49),'OBJECT',15,RED,True)
    order=('no_propagation','25pct_lesion','weight_matched_rewire','published_subset')
    for cond in order:
        trail=runs[cond][max(0,tick-150):tick+1:3]
        pts=[mapxy(t['x'],t['y']) for t in trail]
        if len(pts)>1:d.line(pts,fill=COL[cond],width=3 if cond=='published_subset' else 1,joint='curve')
    for cond in order:
        q=p[cond]
        fly(d,q['x'],q['y'],q['heading'],tick,COL[cond],primary=(cond=='published_subset'))
    for i,cond in enumerate(('published_subset','weight_matched_rewire','25pct_lesion','no_propagation')):
        bx=64+(i%2)*331; by=576+(i//2)*26
        d.ellipse((bx,by+3,bx+11,by+14),fill=COL[cond])
        text(d,(bx+19,by),NAMES[cond],15,COL[cond],True)
    text(d,(844,132),'REAL 42-NODE CONNECTION SUBGRAPH',17,TXT,True)
    text(d,(844,156),'95 weighted directed edges  |  schematic',15,MUTED)
    # Edge diagram
    for a,b,w in data['edges']:
        x1,y1=positions[a]; x2,y2=positions[b]
        d.line((x1,y1,x2,y2),fill=(30,61,78) if w>0 else (66,43,76),width=1)
    les=set()
    for i,(x,y) in positions.items():
        v=primary['neural'][i]
        act=min(1,abs(v))
        base=tuple(int(18+f*act) for f in (63,189,222)) if v>=0 else tuple(int(18+f*act) for f in (175,74,202))
        r=3+int(act*5)
        d.ellipse((x-r,y-r,x+r,y+r),fill=base,outline=CYAN if abs(v)>.55 else None)
    for i,(role,x) in enumerate([('LC4',850),('LPLC2',956),('OTHER',1062),('DN',1168)]):
        text(d,(x,429),role,14,MUTED)
    text(d,(845,474),'CANONICAL BEAST BOX / dyn12',17,TXT,True)
    zero=554
    d.line((846,zero,1219,zero),fill=LINE,width=1)
    for j,v in enumerate(primary['dyn12']):
        x=847+j*31; size=max(1,int(abs(v)*61))
        d.rounded_rectangle((x,zero-size if v>0 else zero,x+19,zero if v>0 else zero+size),radius=2,fill=CYAN if v>0 else VIOLET)
        text(d,(x+4,622),str(j+1),14,MUTED)
    text(d,(844,579),'DN output via assumed decoder -> speed / turn',15,MUTED)
    d.line((41,667,1240,667),fill=LINE,width=2)
    text(d,(42,676),f'TICK {tick:03d}/{len(runs["published_subset"])-1:03d}   |   TARGET DISTANCE {primary["distance_to_target"]:.2f}   |   SPEED {primary["speed"]:.2f}   |   TURN {primary["turn"]:+.2f}',16,TXT,mono=True)
    # persistent small classification
    d.rounded_rectangle((925,21,1238,49),radius=7,fill=(69,37,53),outline=(123,69,78),width=1)
    text(d,(939,27),'SIMULATION, NOT ANIMAL FOOTAGE',14,(255,211,219),bold=False,mono=True)
    return img


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--evidence',type=Path,default=HERE/'real_fly_demo')
    ap.add_argument('--frames',type=int,default=420)
    args=ap.parse_args()
    if args.frames<24:ap.error('min 24 frames')
    data=load_graph()
    ev=args.evidence
    manifest=json.loads((ev/'results.json').read_text())
    if manifest['data_sha256']!=sha256(DATA):raise RuntimeError('data hash mismatch')
    traces=[json.loads(line) for line in (ev/'movement_traces.jsonl').read_text().splitlines()]
    runs={r['condition']:r['trace'] for r in traces if r['seed']==0}
    if len(runs)!=4:raise RuntimeError('missing condition in recorded trace')
    pos=nodecoords(data)
    video=ev/'Cosmic_Fruit_Fly_Real_Wiring_Moving_Demo.mp4'
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','veryfast',
             '-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(args.frames):
            frame=render_frame(i,args.frames,runs,data,pos)
            if i==args.frames//3:frame.save(ev/'moving_fly_preview.png')
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        error=proc.stderr.read().decode()
        if proc.wait()!=0:raise RuntimeError(error)
    except BaseException:
        proc.kill();raise
    result={'video':video.name,'sha256':sha256(video),'frames':args.frames,'fps':FPS,
            'seconds':args.frames/FPS,'source_data_sha256':sha256(DATA),
            'movement_trace_sha256':sha256(ev/'movement_traces.jsonl'),
            'classification':'rendered playback of executed virtual-fly movements with real connectivity subset and assumed dynamics'}
    (ev/'video_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
