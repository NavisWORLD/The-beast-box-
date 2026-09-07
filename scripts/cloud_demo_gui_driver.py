#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, time
from pathlib import Path


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--prompts', type=Path, required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--screens', type=Path, required=True)
    p.add_argument('--display', default=':99.0')
    args=p.parse_args()
    prompts=json.loads(args.prompts.read_text(encoding='utf-8'))
    args.screens.mkdir(parents=True, exist_ok=True)

    def wid():
        ids=subprocess.check_output(['xdotool','search','--name','Beast Box'],text=True).strip().splitlines()
        if not ids: raise RuntimeError('Beast Box window missing')
        return ids[0]
    def count():
        return sum(1 for x in args.log.read_text(encoding='utf-8').splitlines() if x.strip()) if args.log.exists() else 0
    def shot(n):
        subprocess.run(['ffmpeg','-y','-f','x11grab','-video_size','1280x720','-i',args.display,'-frames:v','1',str(args.screens/f'{n:02d}-turn.png')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)

    for offset,prompt in enumerate(prompts):
        n=args.start+offset; w=wid()
        subprocess.run(['xdotool','windowactivate','--sync',w],check=True)
        subprocess.run(['xdotool','mousemove','--window',w,'450','560','click','1'],check=True)
        clip=subprocess.Popen(['xclip','-selection','clipboard'],stdin=subprocess.PIPE,text=True); clip.communicate(prompt)
        if clip.returncode: raise RuntimeError('xclip failed')
        subprocess.run(['xdotool','key','--clearmodifiers','ctrl+a'],check=True)
        subprocess.run(['xdotool','key','--clearmodifiers','ctrl+v'],check=True)
        before=count()
        subprocess.run(['xdotool','mousemove','--window',w,'52','620','click','1'],check=True)
        deadline=time.time()+190
        while time.time()<deadline:
            if count()>before:
                row=json.loads([x for x in args.log.read_text(encoding='utf-8').splitlines() if x.strip()][-1])
                if not row.get('success'): raise RuntimeError(row.get('error','cloud inference failed'))
                time.sleep(3); shot(n); time.sleep(5); break
            time.sleep(.5)
        else:
            raise TimeoutError('cloud response timeout')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
