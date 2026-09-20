"""Timestamp-faithful REPLAY of actual public ledger events (not a screen recording)."""
import argparse
import json
from pathlib import Path
from recorder import verify_ledger
from dashboard import HTML


def create_replay(run: Path):
    events = verify_ledger(run / 'events.jsonl')
    if not events:
        raise ValueError('empty ledger')
    html = HTML.replace('Actual recorded events only.', 'REPLAY of recorded events, not live capture.')
    # Bundle only public, hash-verified events. Remove network polling and endpoints.
    html = html.replace("refresh();setInterval(refresh,1500);", "events=JSON.parse(document.getElementById('bundled').textContent);current=Math.max(0,Math.min(events.length-1,Number(new URLSearchParams(location.search).get('event') ?? events.length-1)));render();")
    # The fetch function is defined but never called in standalone replay.
    data = json.dumps(events, ensure_ascii=False).replace('<', '\\u003c')
    html = html.replace('<script>\nlet events=', f'<script type="application/json" id="bundled">{data}</script><script>\nlet events=')
    (run / 'experiment_replay.html').write_text(html, encoding='utf-8')
    return run / 'experiment_replay.html'


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('run', type=Path)
    args = p.parse_args()
    print(create_replay(args.run))
