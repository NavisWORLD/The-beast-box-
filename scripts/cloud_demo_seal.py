#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--source-sha', required=True)
    args=p.parse_args()
    e=args.root/'evidence'; db=args.root/'data/runtime.sqlite3'; log=e/'cloud_requests.jsonl'; video=e/'BEAST_BOX_LLAMA2_CLOUD_LONG_LIVE.mp4'
    rows=[json.loads(x) for x in log.read_text(encoding='utf-8').splitlines() if x.strip()] if log.exists() else []
    receipt={
        'schema':'beast-box-hf-cloud-live-demo-v1',
        'source_repo':'NavisWORLD/The-beast-box-',
        'source_branch':'experiment/beast-cloud-live-demo-001',
        'source_head_sha':args.source_sha,
        'packaged_artifact_run':34035894541,
        'packaged_binary_sha256':(e/'BEASTBOX_BINARY_SHA256.txt').read_text().split()[0],
        'cloud_provider':'Hugging Face public Gradio Space',
        'space':'huggingface-projects/llama-2-7b-chat',
        'model_id':'meta-llama/Llama-2-7b-chat-hf',
        'api_key_used':False,
        'beast_provider_path':'LocalOllamaProvider -> loopback bridge -> public Hugging Face Gradio Space',
        'literal_gui_recording':video.exists() and video.stat().st_size>0,
        'cloud_request_count':len(rows),
        'successful_cloud_requests':sum(bool(x.get('success')) for x in rows),
        'all_cloud_requests_success':bool(rows) and all(bool(x.get('success')) for x in rows),
        'process_restart_requested':True,
        'claim_boundary':'Software continuity and retrieved-context delivery through a real cloud model. No claim of consciousness, superintelligence, weight changes, biological identity, quantum advantage, or new physics.'
    }
    if db.exists():
        con=sqlite3.connect(f'file:{db}?mode=ro&immutable=1',uri=True)
        memories=[{'id':x[0],'kind':x[1],'text':x[2]} for x in con.execute('SELECT id,kind,text FROM memories ORDER BY id')]
        continuity=[]
        for seq,payload,ch in con.execute('SELECT sequence,payload,sha256 FROM continuity ORDER BY sequence'):
            obj=json.loads(payload); continuity.append({'sequence':seq,'system_id':obj.get('system_id'),'turn':obj.get('state',{}).get('turn'),'checkpoint_sha256':ch})
        con.close()
        receipt.update({'memory_record_count':len(memories),'continuity_checkpoint_count':len(continuity),'system_id_stable':len({x['system_id'] for x in continuity})==1 if continuity else False,'system_id':continuity[-1]['system_id'] if continuity else None,'final_turn':continuity[-1]['turn'] if continuity else None,'runtime_sqlite_sha256':file_sha(db)})
        (e/'runtime-memory.json').write_text(json.dumps(memories,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        (e/'continuity.json').write_text(json.dumps(continuity,indent=2)+'\n',encoding='utf-8')
    if log.exists(): receipt['cloud_log_sha256']=file_sha(log)
    if video.exists() and video.stat().st_size: receipt['video_sha256']=file_sha(video)
    (e/'RUN_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
