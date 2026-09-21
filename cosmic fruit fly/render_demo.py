"""Render an MP4 of *executed software trace events*, NOT a screen recording.

Requires Pillow and ffmpeg. Do not omit the always-visible synthetic/replay labels.
Re-execute record_demo.py before rendering to regenerate verified replay JSON.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'demo_recording'
DATA = json.loads((OUT / 'replay.json').read_text(encoding='utf8'))
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
F = {(f, s): ImageFont.truetype(f, s) for f, s in [(FONT_REG, 18), (FONT_REG, 21), (FONT_REG, 25), (FONT_REG, 32), (FONT_BOLD, 17), (FONT_BOLD, 21), (FONT_BOLD, 28), (FONT_BOLD, 39), (FONT_BOLD, 53), (FONT_MONO, 14), (FONT_MONO, 17)]}

WIDTH, HEIGHT, FPS = 1280, 720, 12
BG = (8, 12, 27)
PANEL = (15, 23, 45)
EDGE = (37, 55, 88)
WHITE = (233, 244, 255)
MUTED = (156, 174, 200)
CYAN = (66, 220, 249)
VIOLET = (178, 132, 252)
GREEN = (103, 237, 170)
RED = (249, 119, 144)
YELLOW = (255, 205, 117)


def text(draw, xy, msg, color=WHITE, sz=21, bold=False):
    font = F[(FONT_BOLD if bold else FONT_REG, sz)] if (FONT_BOLD if bold else FONT_REG, sz) in F else F[(FONT_BOLD, 21)]
    draw.text(xy, str(msg), fill=color, font=font)


def box(draw, area, color=PANEL, outline=EDGE, radius=18):
    draw.rounded_rectangle(area, radius=radius, fill=color, outline=outline, width=2)


def base(t, title, subtitle):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, WIDTH, 8), fill=CYAN)
    text(d, (48, 26), 'CORY DAVIS  //  BEAST BOX  //  COSMIC FRUIT FLY', CYAN, 21, True)
    text(d, (48, 67), title, WHITE, 39, True)
    text(d, (50, 122), subtitle, MUTED, 18)
    box(d, (862, 19, 1229, 49), (58, 25, 55), (129, 54, 93), 9)
    text(d, (874, 23), 'SYNTHETIC DATA  /  NOT A FLY', (255, 198, 213), 17, True)
    d.line((48, 665, 1232, 665), fill=EDGE, width=2)
    text(d, (49, 676), 'RENDERED REPLAY OF EXECUTED TRACES  |  NOT SCREEN OR CAMERA CAPTURE', MUTED, 14)
    d.rectangle((48, 709, 48 + int(1185 * min(1,t / 88)), 712), fill=CYAN)
    return img, d


def fmt_pct(x):
    return f'{100*x:.1f}%'


def timeline_events(arm):
    ticks = DATA['arms'][arm]['events']
    return [e for e in ticks if e['episode'] in (79, 80, 81, 119)]


def graph_edges(arm):
    raw = DATA['graph']['edge_list']
    if arm == 'topology_control':
        # Same permutation algorithm as the experiment, verified on source input.
        import random
        targets = [b for a, b, w in raw]
        random.Random(90001).shuffle(targets)
        return [(a, targets[j], w) for j, (a, b, w) in enumerate(raw)]
    return raw if arm != 'baseline' else []


NODES = [(355 + 160*math.cos(2*math.pi*k/24 - math.pi/2), 391 + 155*math.sin(2*math.pi*k/24 - math.pi/2)) for k in range(24)]


def graph_panel(d, ev, arm, t):
    box(d, (47, 167, 685, 639))
    text(d, (71, 181), 'NEURAL GRAPH  /  24 COMPUTATIONAL UNITS', WHITE, 17, True)
    edges = graph_edges(arm)
    lesioned = set(ev['lesion_indices'])
    for a, b, weight in edges:
        if a == b: continue
        pos1, pos2 = NODES[a], NODES[b]
        inactive = a in lesioned or b in lesioned
        color = (56, 40, 65) if inactive else (39, 91, 101) if weight >= 0 else (89, 49, 95)
        d.line((*pos1,*pos2), fill=color, width=1)
    neural = ev['neural']
    for i, (x, y) in enumerate(NODES):
        active = max(0.0, min(1.0, abs(neural[i]) * 1.65))
        if i in lesioned:
            color, outline, radius = (33, 36, 55), RED, 9
        else:
            color = tuple(int(20 + c*active) for c in (42, 182, 214)) if neural[i] >= 0 else tuple(int(20 + c*active) for c in (119, 90, 203))
            outline = CYAN if neural[i] >= 0 else VIOLET
            radius = 8 + int(6*active)
        d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color, outline=outline, width=2)
    text(d, (70, 590), f'weighted synapse operations / tick: {ev["edge_ops"]:>3}', MUTED, 17)
    if arm == 'lesion':
        text(d, (70, 614), f'LESION: {len(lesioned)} / 24 disabled  |  red rings = disabled units', RED, 17, True)
    elif arm == 'topology_control':
        text(d, (70, 614), 'Targets permuted; edge weights and counts preserved', VIOLET, 17)
    elif arm == 'baseline':
        text(d, (70, 614), 'No network propagation; matched reference arm', MUTED, 17)
    else:
        text(d, (70, 614), 'Color intensity = executed activation magnitude', CYAN, 17)


def right_panel(d, ev, arm):
    box(d, (701, 167, 1233, 407))
    text(d, (722, 182), 'CANONICAL CST / dyn12 STATE', WHITE, 17, True)
    zero_y = 323
    d.line((738, zero_y, 1204, zero_y), fill=EDGE, width=1)
    for i, val in enumerate(ev['state']):
        x = 741 + i*38
        height = min(88, int(abs(val)*79))
        cy = CYAN if val >= 0 else VIOLET
        d.rounded_rectangle((x, zero_y-height if val >= 0 else zero_y,
                             x+25, zero_y if val >= 0 else zero_y+height), radius=3, fill=cy)
        text(d, (x + 2, 367), str(i+1), MUTED, 14)
    box(d, (701, 422, 1233, 639))
    text(d, (723, 437), 'INPUT  >  STATE  >  MEMORY  >  ACTION', WHITE, 17, True)
    text(d, (723, 474), f'Episode {ev["episode"]:03}  /  {ev["phase"].upper()}  |  Neural tick {ev["tick"]+1:02}', CYAN, 21, True)
    text(d, (723, 508), f'Cue {ev["cue_original"]:+.0f}   Context {ev["context_original"]:+.0f}   Signal {ev["stimulus"]:+.3f}', MUTED, 17)
    text(d, (723, 537), f'Memory: {"OFF" if arm == "memory_off" else "ENABLED"}   |  Plasticity L1: {ev["plasticity_l1_at_tick"]:.4f}', VIOLET if arm == 'memory_off' else GREEN, 17)
    if ev['tick'] < (4 if ev['phase'] == 'train' else 7):
        text(d, (723, 575), 'Action / reward: pending next policy step ...', YELLOW, 18)
    else:
        color = GREEN if ev['reward'] else RED
        text(d, (723, 575), f'Action {ev["action"]}  /  Target {ev["target"]}  /  Reward {ev["reward"]}', color, 21, True)
    text(d, (724, 612), 'External tool authority: NONE', MUTED, 17)


def scene_intro(t):
    img, d = base(t, 'THE FLY EXPERIMENT  //  WHAT ACTUALLY RAN', 'Verified data replay  •  source hash matched  •  synthetic engineering fixture only')
    box(d,(49,188,1230,605))
    text(d,(92,219),'24',CYAN,53,True); text(d,(98,288),'simulated units',WHITE,21)
    text(d,(446,219),'96',VIOLET,53,True); text(d,(449,288),'weighted edges',WHITE,21)
    text(d,(845,219),'72',GREEN,53,True); text(d,(847,288),'replayed runs',WHITE,21)
    d.line((98,343,1180,343),fill=EDGE,width=2)
    text(d,(99,374),'9 experimental arms   ×   8 seeds   ×   120 episodes = 8,640 trials',WHITE,28,True)
    text(d,(100,437),'REAL code execution and archived results.  NO biological advantage established.',MUTED,21)
    text(d,(100,485),'Renderer uses the actual logged activation/state values. No invented neuron traces.',CYAN,21)
    text(d,(100,536),'Dataset provenance: locally generated synthetic connectivity; not FlyWire.',YELLOW,21)
    return img


def scene_loop(t):
    img,d=base(t,'THE ACTUAL CONTROL LOOP','Matched simulated task  •  deterministic controller  •  no privileged tools')
    stages=[('01','SENSOR','Cue + context'),('02','NETWORK','Tick / feedback'),('03','CST dyn12','12 state values'),('04','MEMORY','Bounded lookup'),('05','ACTION','0 or 1'),('06','REWARD','Correct or error')]
    for j,(num,name,detail) in enumerate(stages):
        x=62+(j%3)*402;y=183+(j//3)*225
        active=int(t*2)%6==j
        box(d,(x,y,x+372,y+177), (17,38,55) if active else PANEL, CYAN if active else EDGE)
        text(d,(x+18,y+16),num,CYAN if active else MUTED,21,True)
        text(d,(x+19,y+61),name,WHITE,28,True)
        text(d,(x+20,y+119),detail, MUTED,18)
    return img


def scene_arm(t, start, end, arm, title, subtitle):
    img,d=base(t,title,subtitle)
    evs=timeline_events(arm)
    fraction=max(0,min(0.999999,(t-start)/(end-start)))
    idx=min(len(evs)-1,int(fraction*len(evs)))
    ev=evs[idx]
    graph_panel(d,ev,arm,t)
    right_panel(d,ev,arm)
    return img


def scene_summary(t):
    img,d=base(t,'WHAT THE MATCHED CONTROLS MEASURED','8 seeds per arm  •  40 test episodes per seed  •  accuracy is NOT biological intelligence')
    box(d,(48,165,1233,635))
    pairs=[('Baseline','baseline'),('Synthetic network','connectome'),('Rewired topology','topology_control'),('25% lesion','lesion'),('Plasticity disabled','plasticity_off'),('Network, memory off','memory_off'),('Baseline, memory off','baseline_memory_off'),('Rewired, memory off','topology_memory_off'),('Lesion, memory off','lesion_memory_off')]
    progress=min(1,max(0,(t-67)/4))
    for j,(label,key) in enumerate(pairs):
        y=185+j*47
        value=DATA['summary'][key]['test_accuracy_mean']
        text(d,(73,y),label,WHITE,18)
        d.rounded_rectangle((376,y+4,1038,y+22),radius=5,fill=EDGE)
        if progress>0:
            d.rounded_rectangle((376,y+4,376+int(662*value*progress),y+22),radius=5, fill=CYAN if value>0.9 else VIOLET)
        text(d,(1059,y-1),fmt_pct(value),CYAN if value>0.9 else VIOLET,18,True)
    return img


def scene_outro(t):
    img,d=base(t,'THE RESULT  //  NO NETWORK ADVANTAGE DEMONSTRATED','Evidence preserved; nonbiological benchmark only. No claims of fly intelligence, sentience or consciousness.')
    box(d,(48,186,1232,615))
    text(d,(88,215),'What we actually observed',CYAN,28,True)
    text(d,(91,275),'Memory-enabled conditions: 100% test accuracy on repeated keys.',WHITE,21)
    text(d,(91,319),'Removing memory: approx. 46–48% mean accuracy across matched controls.',WHITE,21)
    text(d,(91,364),'Topology rewiring and neuron lesions did not change memory-saturated accuracy.',WHITE,21)
    d.line((90,415,1180,415),fill=EDGE,width=2)
    text(d,(91,443),'NOT YET TESTED: authenticated full fruit fly connectome, true biological dynamics,',YELLOW,21)
    text(d,(91,475),'new-task generalization, full COSMOS integration, real model swap or external devices.',YELLOW,21)
    text(d,(91,544),'MODEL != SYSTEM     |     MODEL != MEMORY     |     MODEL != AUTHORITY',VIOLET,21,True)
    return img


def make():
    path=OUT/'cosmic_fruit_fly_executed_trace_replay.mp4'
    command=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24', '-video_size',f'{WIDTH}x{HEIGHT}',
             '-framerate',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','22',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    ff=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    assert ff.stdin is not None
    segments=[(0,6,'intro'),(6,12,'loop'),(12,28,'connectome'),(28,41,'topology_control'),
              (41,54,'lesion'),(54,67,'memory_off'),(67,80,'summary'),(80,88,'outro')]
    frames=0
    try:
        for start,end,kind in segments:
            for k in range(int((end-start)*FPS)):
                t=start+k/FPS
                if kind=='intro': frame=scene_intro(t)
                elif kind=='loop': frame=scene_loop(t)
                elif kind=='connectome': frame=scene_arm(t,start,end,kind,'RUN 01  //  SYNTHETIC CONNECTIVITY','Unmodified source replay  •  seed 0  •  graph propagates computational signals')
                elif kind=='topology_control': frame=scene_arm(t,start,end,kind,'RUN 02  //  REWIRED CONTROL','Identical edge count and weight multiset; target wiring randomized')
                elif kind=='lesion': frame=scene_arm(t,start,end,kind,'RUN 03  //  SIMULATED LESION','25% of computational nodes disabled; no claim about real injury or physiology')
                elif kind=='memory_off': frame=scene_arm(t,start,end,kind,'RUN 04  //  MEMORY ABLATION','Bounded lookup disabled; policy can make wrong choices despite network activity')
                elif kind=='summary': frame=scene_summary(t)
                else: frame=scene_outro(t)
                if frames==int(16*FPS): frame.save(OUT/'demo_preview.png')
                ff.stdin.write(frame.tobytes())
                frames+=1
        ff.stdin.close()
        err=ff.stderr.read().decode(errors='replace')
        ret=ff.wait()
        if ret: raise RuntimeError('ffmpeg failed '+err[-2000:])
    except Exception:
        ff.kill()
        raise
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/'video_manifest.json').write_text(json.dumps({'file':path.name,'sha256':digest,
       'frames':frames,'fps':FPS,'duration_seconds':frames/FPS,'video_type':'rendered replay of executed traces, not screen/camera recording',
       'replay_json_sha256':hashlib.sha256((OUT/'replay.json').read_bytes()).hexdigest()},indent=2)+'\n')
    print(json.dumps({'video':str(path),'frames':frames,'seconds':frames/FPS,'bytes':path.stat().st_size,'sha256':digest},indent=2))


if __name__=='__main__': make()
