"""Finish an interrupted FFmpeg segment without inventing or skipping frames."""
import json, subprocess
from pathlib import Path
from PIL import Image
from fly_movement import HERE,load_graph
from render_build_grow import ASSET,OUT,W,H,FPS,FRAMES_PER_TICK,graph_layout,world_and_ui
runs=[json.loads(line) for line in (OUT/'runs.jsonl').read_text().splitlines()]
run=next(r for r in runs if r['arm']=='real_wiring' and r['seed']==3)
world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
data=load_graph();layout=graph_layout(data)
video=OUT/'Cosmic_Fruit_Fly_Build_Grow_part2.mp4'
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast','-crf','26','-r','25','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
# Recorded first segment is exactly 1511 source frames = 1266 from first three seeds and 245 from seed3.
first_three=sum(len(r['trace'])*FRAMES_PER_TICK for r in runs if r['arm']=='real_wiring' and r['seed']<3)
assert first_three == 1266,first_three
start=1511-first_three
assert start == 245, start
n=0
try:
    for index in range(start,len(run['trace'])*FRAMES_PER_TICK):
        tick_i,sub=divmod(index,FRAMES_PER_TICK)
        step=run['trace'][tick_i]
        nxt=run['trace'][tick_i+1] if tick_i+1<len(run['trace']) and run['trace'][tick_i+1]['stage']==step['stage'] else None
        frame=world_and_ui(step,run,world,data,layout,first_three+index,sub/FRAMES_PER_TICK,nxt)
        p.stdin.write(frame.tobytes());n+=1
    p.stdin.close();stderr=p.stderr.read().decode();rc=p.wait()
    if rc:raise RuntimeError(stderr)
except BaseException:
    p.kill();raise
print('TAIL_COMPLETED',n,'duration',n/FPS, 'first_three',first_three)
