"""Render a plainly labeled, step-paced video from verified event records.

This video is a replay, NEVER a screen capture or a live recording. All displayed
experimental measurements come directly from events.jsonl.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap
from PIL import Image, ImageDraw, ImageFont
from recorder import verify_ledger

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def frame(event, events):
    img = Image.new('RGB', (1280, 720), (8, 15, 32))
    draw = ImageDraw.Draw(img)
    white, blue, amber, green = '#f0f4ff', '#7ddbea', '#ffd295', '#8cebad'
    draw.text((55, 30), 'CORY DAVIS // BEAST BOX // i dare you', font=font(28), fill=blue)
    draw.text((55, 78), 'LEDGER REPLAY — NOT LIVE SCREEN CAPTURE', font=font(22), fill=amber)
    draw.line((55, 119, 1225, 119), fill='#42607f', width=2)
    draw.text((55, 142), f"EVENT {event['seq']:02} / {len(events):02}     {event['timestamp']}", font=font(23), fill=white)
    draw.text((55, 184), f"PHASE: {event['phase']}      EVENT: {event['event_type']}", font=font(21), fill=blue)
    previous = events[:event['seq']]
    blocks = [e for e in previous if e['event_type'] == 'phase_blocked']
    states = [e for e in previous if e['event_type'] == 'independent_state_written']
    steps = [e for e in previous if e['event_type'] == 'training_step']
    draw.rounded_rectangle((55, 242, 585, 424), radius=16, outline='#345977', width=2)
    draw.text((78, 259), 'ACTIVE MODEL / PROVIDER', font=font(18), fill=blue)
    draw.text((78, 300), 'No verified transition' if not any(e['event_type']=='provider_swapped' for e in previous)
              else 'Verified transition recorded', font=font(19), fill=white)
    draw.text((78, 347), f'Blocked phases: {len(blocks)}', font=font(19), fill=amber)
    draw.rounded_rectangle((605, 242, 1225, 424), radius=16, outline='#345977', width=2)
    draw.text((628, 259), 'PERSISTENT SOFTWARE STATE', font=font(18), fill=blue)
    if states:
        state = states[-1]['payload']
        draw.text((628, 300), f"Memory records: {state['memory_count']}", font=font(19), fill=green)
        draw.text((628, 345), f"State counter: {state['state_counter']}", font=font(19), fill=green)
    else:
        draw.text((628, 300), 'Not yet written', font=font(19), fill=white)
    draw.text((55, 451), 'ACTUAL EVENT PAYLOAD', font=font(18), fill=blue)
    payload = json.dumps(event['payload'], sort_keys=True, ensure_ascii=False)
    for idx, line in enumerate(textwrap.wrap(payload, 108, break_long_words=True)[:5]):
        draw.text((55, 484+31*idx), line, font=font(15), fill=white)
    draw.line((55, 650, 1225, 650), fill='#42607f', width=2)
    draw.text((55, 666), f"PHOS training metrics: {len(steps)} verified steps. Playback is event-paced, not wall-clock.",
              font=font(15), fill=amber)
    return img


def render(run):
    events = verify_ledger(run / 'events.jsonl')
    if not events:
        raise ValueError('no recorded events')
    with tempfile.TemporaryDirectory(prefix='ledger_replay_') as work:
        p = Path(work)
        for i, event in enumerate(events):
            frame(event, events).save(p / f'{i:04d}.png')
        output = run / 'experiment_replay.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '0.66',
                        '-i', str(p / '%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart', str(output)], check=True)
    return output


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('run', type=Path)
    args=ap.parse_args()
    print(render(args.run))
