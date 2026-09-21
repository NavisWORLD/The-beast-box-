"""Render an evidence-bound ~5.6 minute video of executed sandbox traces.

LIVE means LIVE-IN-SIMULATION at the archived step only. This is NOT a live
hardware camera, biological movement, or live screen recording. The forest
backdrop is decorative; a separate 96x64 sensor raster drives the controller.
"""
from __future__ import annotations
import argparse, json, math, subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from sandbox_ecology import POSITIONS, PALETTE, retinal_image, interpret_retina
from sandbox_sensors import BOUNDS, OBSTACLES
from fly_movement import HERE, DATA, load_graph, sha256
from run_build_grow import ARMS, GOALS

OUT=HERE/'build_grow_demo'
ASSET=HERE/'assets'/'forest_world_clean.png'
FPS=5
FRAMES_PER_TICK=2
W,H=1280,720
NAVY=(6,16,32);PANEL=(11,28,48);CYAN=(51,225,243);YELLOW=(255,207,69)
GREEN=(68,239,144);PINK=(249,122,197);PURPLE=(180,138,246);WHITE=(238,248,251)
MUTED=(142,168,189);RED=(250,96,108)
F='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
B='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
FONTS={n:ImageFont.truetype(B,n) for n in (10,11,12,13,14,15,16,18,20,21,22)}


def text(d,xy,msg,size=13,color=WHITE):
    d.text(xy,str(msg),fill=color,font=FONTS[size])


def panel(d,rect):
    d.rounded_rectangle(rect,radius=4,fill=NAVY,outline=(73,183,210),width=2)
    x,y,x2,y2=rect
    d.line((x+5,y+4,x2-5,y+4),fill=CYAN,width=1)


def coords(x,y):
    return (round(24+(x-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0])*892),
            round(17+(BOUNDS[3]-y)/(BOUNDS[3]-BOUNDS[2])*534))


def fly(d,px,py,heading,frame,offspring=False,scale=1.0):
    c=math.cos(-heading);s=math.sin(-heading)
    def q(a,b):return (round(px+(c*a-s*b)*scale),round(py+(s*a+c*b)*scale))
    wing=5*math.sin(frame*1.32)
    for side in (-1,1):
        d.polygon([q(-3,side*2),q(-10-wing,side*11),q(2,side*8)],fill=(159,240,246),outline=(17,48,77))
        for leg in (-7,0,6):d.line((q(leg,side*4),q(leg+3,side*10)),fill=(11,30,50),width=2)
    body=(170,99,244) if offspring else (27,117,153)
    for ox,r,color in ((-7,6,body),(0,7,(15,72,105)),(8,6,(253,157,61))):
        cx,cy=q(ox,0);d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=color,outline=NAVY,width=2)
    cx,cy=q(11,-3);d.ellipse((cx-2,cy-2,cx+2,cy+2),fill=RED)


def graph_layout(data):
    groups={'VISUAL':['lplc2','lc4'], 'INTER':['other'], 'DESC':['dng11','dnp09','dna01','mdn','escw','gf','dna02']}
    positions={}
    for column,roles in enumerate(groups.values()):
        ids=[i for i,r in enumerate(data['roles']) if r in roles]
        for j,i in enumerate(ids):
            xx=38+column*186+(j%3)*22
            yy=619+(j//3)*9 if column!=2 else 622+(j//3)*11
            positions[i]=(xx,yy)
    assert len(positions)==42, len(positions)
    return positions


def brain_panel(d, data, step, layout):
    panel(d,(15,570,615,705))
    text(d,(27,580),'VISIBLE 42  /  CONNECTOME GRAPH',15,CYAN)
    text(d,(29,602),'VISUAL',10,(84,224,241));text(d,(218,602),'INTER',10,PURPLE)
    text(d,(404,602),'DESCENDING',10,YELLOW)
    neural=step['neural']
    for src,dst,w in data['edges']:
        a,b=layout[src],layout[dst]
        power=max(abs(neural[src]),abs(neural[dst]))
        hue=(37+round(50*power),66+round(100*power),86+round(80*power))
        d.line((a,b),fill=hue,width=1)
    for i,(px,py) in layout.items():
        role=data['roles'][i]
        strength=abs(neural[i]);rad=2+round(strength*3)
        color=CYAN if role in ('lplc2','lc4') else PURPLE if role=='other' else YELLOW
        if strength>.42:d.ellipse((px-rad-2,py-rad-2,px+rad+2,py+rad+2),outline=WHITE)
        d.ellipse((px-rad,py-rad,px+rad,py+rad),fill=color if strength>.12 else (62,74,97))
    text(d,(28,691),'REAL-DERIVED EDGES  /  SIMULATED ACTIVITY',10,MUTED)


def world_and_ui(step, run, world, data, layout, frame, alpha=0.0, after=None):
    img=Image.new('RGB',(W,H),NAVY);img.paste(world,(20,16))
    d=ImageDraw.Draw(img)
    goal=step['goal'];position=(step['x'],step['y']);heading=step['heading']
    if after is not None:
        position=(step['x']*(1-alpha)+after['x']*alpha,step['y']*(1-alpha)+after['y']*alpha)
        if abs(after['heading']-heading)<math.pi:heading=heading*(1-alpha)+after['heading']*alpha
    for ox,oy,r in OBSTACLES:
        px,py=coords(ox,oy);radius=round(r*100)
        d.ellipse((px-radius,py-radius,px+radius,py+radius),outline=(246,232,172),width=2)
    for name,xy in POSITIONS.items():
        px,py=coords(*xy);color=PALETTE[name];exists=name in step['shown']
        if not exists and name not in ('nest','patch'):continue
        radius=11 if name==goal else 6
        d.ellipse((px-radius,py-radius,px+radius,py+radius),fill=color if exists else (48,64,72),outline=WHITE if name==goal else PANEL,width=2)
        if name==goal:text(d,(px-24,py-29),name.upper(),11,WHITE)
    if step['world']['nest_built']:
        px,py=coords(*POSITIONS['nest']);d.rectangle((px-18,py+10,px+19,py+23),fill=(141,81,48),outline=YELLOW,width=2)
        text(d,(px-22,py+25),'NEST',10,YELLOW)
    if step['world']['grown']:
        px,py=coords(*POSITIONS['patch']);d.ellipse((px-17,py-30,px+17,py-5),fill=GREEN,outline=YELLOW)
    is_child=step['stage']==len(GOALS)-1
    if is_child:
        px,py=coords(*POSITIONS['nest']);fly(d,px,py,0,frame,scale=.65)
    px,py=coords(*position)
    fov=math.radians(114)/2
    reach=46
    d.polygon([(px,py),(px+round(reach*math.cos(heading-fov)),py-round(reach*math.sin(heading-fov))),
                (px+round(reach*math.cos(heading+fov)),py-round(reach*math.sin(heading+fov)))],outline=CYAN,width=2)
    fly(d,px,py,heading,frame,offspring=is_child,scale=.75 if is_child else 1.)
    # Every dynamic figure is read from an executed trace or verified reraster.
    panel(d,(23,17,548,89));text(d,(37,26),'* COSMIC FRUIT FLY   +',20,CYAN)
    text(d,(39,58),f'SEED {run["seed"]+1}/4 | STEP {step["tick"]+1:03d}/{run["steps"]} | EXECUTION REPLAY',12,WHITE)
    panel(d,(23,98,425,165));text(d,(37,106),'OBJECTIVE  //  SANDBOX QUEST',15,CYAN)
    text(d,(37,134),f'{step["stage"]+1:02d}/{len(GOALS)}   {GOALS[step["stage"]][1].upper():<15} {goal.upper()}',14,YELLOW)
    panel(d,(925,15,1267,172));text(d,(940,23),'MINIMAP / VIRTUAL ARENA',15,CYAN)
    img.paste(world.resize((313,111),Image.Resampling.NEAREST),(938,52));d=ImageDraw.Draw(img)
    for name,xy in POSITIONS.items():
        x,y=coords(*xy);mx=round(938+(x-20)/900*313);my=round(52+(y-16)/540*111)
        d.ellipse((mx-3,my-3,mx+3,my+3),fill=PALETTE[name])
    mx=round(938+(px-20)/900*313);my=round(52+(py-16)/540*111)
    d.ellipse((mx-4,my-4,mx+4,my+4),fill=PINK if is_child else CYAN,outline=WHITE)
    panel(d,(925,181,1267,390));text(d,(940,188),'FLY CAMERA / SIMULATED',15,CYAN)
    shown={key:POSITIONS[key] for key in step['shown']}
    pixels=retinal_image(step['sensor_pose'][:2],step['sensor_pose'][2],shown)
    if interpret_retina(pixels)!=step['vision']:
        raise RuntimeError(f'sensor replay mismatch at tick {step["tick"]}')
    view=Image.fromarray(pixels,'RGB').resize((288,153),Image.Resampling.NEAREST)
    img.paste(view,(950,216));d=ImageDraw.Draw(img)
    text(d,(941,372),'VISION: '+('GOAL DETECTED' if step['vision'][goal]['seen'] else 'SEARCHING'),12,GREEN if step['vision'][goal]['seen'] else YELLOW)
    panel(d,(925,397,1267,562));text(d,(940,405),'SENSORS + ACTION POLICY',15,CYAN)
    def meter(y,label,val,color):
        text(d,(941,y),label,12,WHITE)
        d.rectangle((1030,y+2,1160,y+13),fill=(39,56,72))
        d.rectangle((1030,y+2,1030+round(130*max(0.,min(1.,val))),y+13),fill=color)
        text(d,(1171,y),f'{val:.2f}',11,color)
    meter(431,'VISION',step['vision'][goal]['confidence'],CYAN)
    meter(453,'ODOR',step['odor'][0],YELLOW)
    meter(475,'TOUCH',float(step['touch']),PINK)
    text(d,(942,500),f'ACTION: {step["action"].upper():<14}',12,GREEN)
    text(d,(942,521),f'INVENTORY: {",".join(step["world"]["inventory"]) or "EMPTY"}',12,WHITE)
    flags=step['world'];text(d,(942,543),f'NEST:{int(flags["nest_built"])}  GROWN:{int(flags["grown"])}  CHILD:{int(flags["offspring"] is not None)}',11,PURPLE)
    brain_panel(d,data,step,layout)
    panel(d,(622,570,1267,705));text(d,(634,581),'dyn12 ACTIVITY  +  WORLD EVENTS',15,CYAN)
    for i,v in enumerate(step['dyn12']):
        size=round(abs(v)*35);xx=638+i*19
        d.rectangle((xx,646-size,xx+13,646),fill=CYAN if v>=0 else PURPLE)
    event=step['event'] or ('CHILD NAVIGATING' if is_child else 'GOAL: '+goal.upper())
    if event.startswith('FAILED'):color=RED
    elif event.startswith('DENIED'):color=RED
    else:color=GREEN if step['event'] else YELLOW
    text(d,(889,615),event[:29],11,color)
    text(d,(889,638),f'ENERGY:{flags["energy"]}  TICK:{step["tick"]:03d}',11,WHITE)
    text(d,(636,661),'42 REAL-DERIVED NODES | SOFTWARE TASK POLICY | NO EXTERNAL AUTHORITY',10,MUTED)
    text(d,(636,684),'VISUAL REPLAY OF MEASURED SIMULATION STEPS; NO ANIMAL FOOTAGE',10,MUTED)
    return img


def main():
    p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true')
    p.add_argument('--output',type=Path,default=OUT)
    a=p.parse_args();out=a.output
    results=json.loads((out/'results.json').read_text())
    if sha256(out/'runs.jsonl')!=results['run_ledger_sha256'] or sha256(DATA)!=results['source_data_sha256'] or sha256(HERE/'run_build_grow.py')!=results['code_sha256'] or sha256(HERE/'sandbox_ecology.py')!=results['sensor_code_sha256']:
        raise RuntimeError('evidence input changed: hash mismatch')
    raw=[json.loads(line) for line in (out/'runs.jsonl').read_text().splitlines()]
    runs=sorted([r for r in raw if r['arm']=='real_wiring'],key=lambda r:r['seed'])
    if len(runs)!=4 or any(not r['trace'] for r in runs):raise ValueError('four real-wiring executed traces required')
    data=load_graph();layout=graph_layout(data)
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    for label,rr in [('gather',0),('build',0),('grow',0),('offspring',0)]:
        stage={'gather':0,'build':4,'grow':7,'offspring':10}[label]
        step=next(t for t in runs[rr]['trace'] if t['stage']==stage)
        world_and_ui(step,runs[rr],world,data,layout,step['tick']*FRAMES_PER_TICK).save(out/f'preview_{label}.png')
    if a.preview:
        print('PREVIEWS_OK');return
    video=out/'Cosmic_Fruit_Fly_Build_Grow_Visible42_5m38s.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast','-crf','26','-r','25','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    n=0
    try:
        for run in runs:
            trace=run['trace']
            for i,tick in enumerate(trace):
                successor=trace[i+1] if i+1<len(trace) and trace[i+1]['stage']==tick['stage'] else None
                for sub in range(FRAMES_PER_TICK):
                    frame=world_and_ui(tick,run,world,data,layout,n,sub/FRAMES_PER_TICK,successor)
                    proc.stdin.write(frame.tobytes());n+=1
                if (i+1)%100==0:print(f'RENDER seed {run["seed"]}: {i+1}/{len(trace)} | frames={n}',flush=True)
        proc.stdin.close();err=proc.stderr.read().decode()
        if proc.wait()!=0: raise RuntimeError(err)
    except BaseException:
        proc.kill();raise
    manifest={'file':video.name,'sha256':sha256(video),'capture_fps':FPS,'encoded_fps':25,'source_frames':n,'duration_seconds':n/FPS,
       'source_data_sha256':sha256(DATA),'run_ledger_sha256':sha256(out/'runs.jsonl'),
       'renderer_sha256':sha256(Path(__file__)),'backdrop_sha256':sha256(ASSET),
       'classification':'rendered simulation replay of four executed software-agent lifecycles; camera re-rasterized and cross-checked; authored goal sequence; no physical/animal footage'}
    (out/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
