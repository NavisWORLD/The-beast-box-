"""Evidence-first Zelda-like *original pixel-art inspired* virtual fly replay.

The decorative forest is an edited concept-art backdrop; physics obstacles,
vision, odor and touch come from sandbox_sensors.py, NOT the image pixels.
Sensor camera inset is re-rasterized per recorded pose then checked against the
saved executed sensor trace. It is a virtual camera, NOT physical camera footage.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from sandbox_sensors import camera, interpret_camera, OBSTACLES, BOUNDS
from fly_movement import DATA, HERE, sha256
from run_sensor_quest import COUNTS

OUT=HERE/'sensor_quest_demo'
ASSET=HERE/'assets'/'forest_world_clean.png'
FPS=10
FRAMES_PER_EP=26
W,H=1280,720
NAVY=(8,19,36); PANEL=(12,29,49); CYAN=(47,220,241); AMBER=(255,202,67)
GREEN=(76,239,151); PURPLE=(193,125,250); WHITE=(239,248,255); MUTED=(146,172,191)
RED=(250,109,113)
FONTS='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
FONT={n:ImageFont.truetype(BOLD,n) for n in (11,12,13,14,15,16,18,20,22)}


def text(d,xy,message,size=14,color=WHITE):d.text(xy,message,font=FONT[size],fill=color)


def panel(d,rect):
    d.rounded_rectangle(rect,radius=5,fill=NAVY,outline=(82,190,212),width=2)
    x,y,x2,y2=rect
    d.line((x+3,y+3,x2-3,y+3),fill=CYAN,width=1)


def coords(x,y):
    return (round(24+(x-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0])*887),
            round(19+(BOUNDS[3]-y)/(BOUNDS[3]-BOUNDS[2])*533))


def fly_sprite(d,px,py,heading,frame):
    # Original pixel sprite, cosmetic flapping/feet independent of inferred physiology.
    angle=-heading;c=math.cos(angle);s=math.sin(angle)
    def pt(a,b):return (round(px+c*a-s*b),round(py+s*a+c*b))
    wing=5*math.sin(frame*1.7)
    for side in (-1,1):
        d.polygon([pt(-3,side*3),pt(-13-wing,side*12),pt(2,side*8)],fill=(156,246,249),outline=(15,56,84))
        for leg in (-8,0,7):d.line([pt(leg,side*4),pt(leg+3,side*11)],fill=(12,37,51),width=2)
    for x,r,color in ((-8,7,(28,121,153)),(0,7,(18,76,113)),(9,6,(244,158,61))):
        cx,cy=pt(x,0);d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=color,outline=(9,35,52),width=2)
    cx,cy=pt(12,-3);d.ellipse((cx-2,cy-2,cx+2,cy+2),fill=RED)
    d.ellipse((px-16,py+14,px+17,py+17),fill=(31,65,52))


def draw_camera(base,pos,heading,stations,logged):
    pixels=camera(pos,heading,stations)
    detected=interpret_camera(pixels)
    # Strict self-audit against archived genuine compute; fail if renderer invents a sensor.
    if detected!=logged:
        raise ValueError('camera replay diverged from executed logged vision')
    return Image.fromarray(pixels,'RGB').resize((288,153),Image.Resampling.NEAREST)


def render_frame(i,record,world):
    ei=min(sum(COUNTS)-1,i//FRAMES_PER_EP);sub=i%FRAMES_PER_EP
    ep=record[ei];trace=ep['trace']
    tick=min(len(trace)-1,round((sub+.5)/FRAMES_PER_EP*(len(trace)-1)))
    step=trace[tick];pos=(step['x'],step['y']);heading=step['heading']
    rgb=Image.new('RGB',(W,H),NAVY)
    rgb.paste(world,(20,16))
    d=ImageDraw.Draw(rgb)
    # Physical obstacles are overlay outlines, not inferred from the decorative landscape.
    for ox,oy,r in OBSTACLES:
        px,py=coords(ox,oy);rad=round(r*105)
        d.ellipse((px-rad,py-rad,px+rad,py+rad),outline=(240,228,160),width=2)
        d.ellipse((px-rad+5,py-rad+5,px+rad-5,py+rad-5),outline=(31,70,72),width=1)
    for k,station in enumerate(ep['stations']):
        px,py=coords(*station);clr=CYAN if k==0 else AMBER
        d.ellipse((px-19,py-19,px+19,py+19),fill=(20,39,50),outline=clr,width=3)
        d.ellipse((px-9,py-9,px+9,py+9),fill=clr,outline=WHITE,width=1)
        text(d,(px-38,py-42),f'STATION {"A" if k==0 else "B"}',11,WHITE)
        if sub>=FRAMES_PER_EP-3 and k==ep['choice']:
            color=GREEN if ep['reward'] else RED
            d.ellipse((px-25,py-25,px+25,py+25),outline=color,width=4)
    path=[coords(p['x'],p['y']) for p in trace[:tick+1]]
    if len(path)>1:d.line(path,fill=AMBER,width=3,joint='curve')
    px,py=coords(*pos)
    # Vision cone is purely visual; true simulated camera uses FOV and obstacles.
    reach=37;fov=math.radians(114)/2
    d.polygon([(px,py),(px+round(reach*math.cos(heading-fov)),py-round(reach*math.sin(heading-fov))),
               (px+round(reach*math.cos(heading+fov)),py-round(reach*math.sin(heading+fov)))],
              outline=CYAN,width=2)
    fly_sprite(d,px,py,heading,i)
    # Original screenshot-like UI, all dynamic readouts from step and episode.
    panel(d,(24,19,549,88));text(d,(38,28),'* COSMIC FRUIT FLY    +',20,CYAN)
    text(d,(39,60),f'EP {ei+1:03d}/{sum(COUNTS):03d}  {ep["phase"].upper()}  SENSORS ONLINE',13,WHITE)
    panel(d,(24,97,285,169));text(d,(38,105),'OBJECTIVE',16,CYAN)
    text(d,(39,134),'Find Food  [A / B]',16,AMBER)
    panel(d,(927,14,1267,173));text(d,(941,22),'MINIMAP  /  ARENA',16,CYAN)
    mini=world.resize((306,113),Image.Resampling.NEAREST)
    rgb.paste(mini,(942,48));d=ImageDraw.Draw(rgb)
    for k,st in enumerate(ep['stations']):
        xp,yp=coords(*st);mx=round(942+(xp-20)/900*306);my=round(48+(yp-16)/540*113)
        d.ellipse((mx-4,my-4,mx+4,my+4),fill=CYAN if k==0 else AMBER,outline=WHITE)
    mx=round(942+(px-20)/900*306);my=round(48+(py-16)/540*113)
    d.ellipse((mx-5,my-5,mx+5,my+5),fill=RED,outline=WHITE,width=1)
    panel(d,(927,180,1267,390));text(d,(941,190),'FLY CAMERA / VIRTUAL',16,CYAN)
    view=draw_camera(rgb,step['sensor_pose'][:2],step['sensor_pose'][2],ep['stations'],step['vision'])
    rgb.paste(view,(952,220));d=ImageDraw.Draw(rgb)
    seen=[v['seen'] for v in step['vision']]
    text(d,(943,373),f'A:{int(seen[0])}  B:{int(seen[1])}  REPLAY',13,GREEN if any(seen) else MUTED)
    panel(d,(927,399,1267,574));text(d,(941,408),'SENSORS / COMPUTED',16,CYAN)
    def meter(y,label,value,col,extra=''):
        text(d,(942,y),label,13,WHITE)
        x0=1062
        d.rectangle((x0,y+2,x0+111,y+12),fill=(43,65,79))
        d.rectangle((x0,y+2,x0+round(111*max(0,min(1,value))),y+12),fill=col)
        text(d,(1183,y),extra or f'{value:.2f}',12,col)
    meter(438,'VISION',float(step['vision'][ep['choice']]['confidence']),CYAN)
    meter(461,'ODOR',float(step['odor'][ep['choice']][0]),AMBER)
    meter(484,'TOUCH',float(step['touch']),RED,str(int(step['touch'])))
    text(d,(943,506),f'HEADING: {round(math.degrees(heading)):+04} deg',13,WHITE)
    text(d,(943,528),f'MEMORY: Q(odor {ep["cue"]})',13,PURPLE)
    text(d,(943,547),f'A={ep["q_before"][ep["cue"]][0]:.2f}   B={ep["q_before"][ep["cue"]][1]:.2f}',13,PURPLE)
    panel(d,(15,582,1267,706))
    text(d,(29,592),f'WIRING: {"REAL SUBSET"}',16,CYAN)
    text(d,(282,592),f'EPISODE: {ei+1}/{sum(COUNTS)}',16,WHITE)
    text(d,(549,592),'dyn12 ACTIVITY',16,CYAN)
    for j,value in enumerate(step['dyn12']):
        h=round(abs(value)*36);x=557+j*23
        d.rectangle((x,660-h,x+16,660),fill=CYAN if value>=0 else PURPLE)
    text(d,(850,591),f'POS: ({pos[0]:+.2f},{pos[1]:+.2f})',13,WHITE)
    text(d,(850,615),f'TICK {tick+1:03d}/{len(trace):03d}  SPEED {step["speed"]:.2f}',13,WHITE)
    text(d,(850,640),'REWARD: '+('FOUND' if ep['reward'] else 'EMPTY' if ep['arrived'] else 'TIMEOUT') if sub>=FRAMES_PER_EP-3 else 'REWARD: UNKNOWN',13,
         GREEN if sub>=FRAMES_PER_EP-3 and ep['reward'] else MUTED)
    text(d,(29,675),'REAL ANATOMICAL SUBSET + ASSUMED DYNAMICS  |  SOFTWARE LEARNING  |  RENDERED TRACE',12,MUTED)
    return rgb


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');a=ap.parse_args()
    results=json.loads((OUT/'results.json').read_text())
    if results['episode_log_hash']!=sha256(OUT/'runs.jsonl') or results['source_hash']!=sha256(DATA) or results['code_hash']!=sha256(HERE/'run_sensor_quest.py') or results['sensor_code_hash']!=sha256(HERE/'sandbox_sensors.py'):
        raise RuntimeError('source or recorded evidence hashes mismatch')
    raw=[json.loads(x) for x in (OUT/'seed-0.jsonl').read_text().splitlines()]
    record=next(r['episodes'] for r in raw if r['arm']=='real_wiring_learning')
    if len(record)!=sum(COUNTS) or not all(e['trace'] for e in record):raise RuntimeError('missing executed traces')
    world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    for name,ep in [('train',16),('heldout',47),('reversal',67)]:
        render_frame(ep*FRAMES_PER_EP+FRAMES_PER_EP//2,record,world).save(OUT/f'quest_{name}_preview.png')
    if a.preview:print('PREVIEWS_OK');return
    video=OUT/'Cosmic_Fruit_Fly_Sensor_Quest_3m18s.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
        '-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast','-crf','25',
        '-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    total=len(record)*FRAMES_PER_EP
    try:
        for i in range(total):
            proc.stdin.write(render_frame(i,record,world).tobytes())
            if (i+1)%260==0:print(f'RENDERED {i+1}/{total}',flush=True)
        proc.stdin.close();err=proc.stderr.read().decode()
        if proc.wait()!=0:raise RuntimeError(err)
    except BaseException:
        proc.kill();raise
    manifest={'video':video.name,'sha256':sha256(video),'fps':FPS,'frames':total,
        'duration_seconds':total/FPS,'source_sha256':sha256(DATA),
        'episode_log_sha256':sha256(OUT/'runs.jsonl'), 'world_asset_sha256':sha256(ASSET),
        'renderer_sha256':sha256(Path(__file__)),
        'classification':'rendered playback of executed seed 0 sensor/movement/neural trace; virtual camera re-rasterized and verified; edited forest art is ILLUSTRATIVE backdrop, not physical sensor pixels'}
    (OUT/'video_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
