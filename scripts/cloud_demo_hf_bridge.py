#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from gradio_client import Client


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def extract(result):
    if isinstance(result, str):
        return result
    if isinstance(result, (list, tuple)):
        for item in reversed(result):
            if isinstance(item, str) and item.strip():
                return item
            if isinstance(item, dict):
                for key in ('content', 'text', 'response'):
                    if isinstance(item.get(key), str) and item[key].strip():
                        return item[key]
    if isinstance(result, dict):
        for key in ('content', 'text', 'response'):
            if isinstance(result.get(key), str) and result[key].strip():
                return result[key]
    raise ValueError('cloud Space returned no extractable text')


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--space', default='huggingface-projects/llama-2-7b-chat')
    p.add_argument('--model-id', default='meta-llama/Llama-2-7b-chat-hf')
    p.add_argument('--port', type=int, default=11434)
    p.add_argument('--evidence-dir', type=Path, required=True)
    args=p.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path=args.evidence_dir/'cloud_requests.jsonl'
    client=Client(args.space, verbose=False)
    try:
        api=client.view_api(return_format='dict')
    except Exception as exc:
        api={'view_api_error': f'{type(exc).__name__}: {exc}'}
    (args.evidence_dir/'hf-space-api.json').write_text(json.dumps(api, indent=2, default=str)+'\n', encoding='utf-8')
    lock=threading.Lock(); counter={'n':0}

    def write(row):
        with lock, log_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')

    def generate(prompt: str):
        errors=[]
        for api_name in ('/chat','/generate'):
            started=time.time()
            try:
                job=client.submit(prompt, [], '', 180, 0.6, 0.9, 50, 1.2, api_name=api_name)
                result=job.result(timeout=170)
                return extract(result), api_name, round(time.time()-started, 3)
            except Exception as exc:
                errors.append(f'{api_name}:{type(exc).__name__}:{exc}')
        raise RuntimeError('public Hugging Face Space call failed: '+' | '.join(errors))

    class Handler(BaseHTTPRequestHandler):
        server_version='BeastHFBridge/1.0'
        def log_message(self,*_):
            pass
        def reply(self, code, body):
            data=json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            if self.path=='/health':
                return self.reply(200, {'ok':True,'provider':'Hugging Face public Gradio Space','space':args.space,'model_id':args.model_id,'api_key_used':False})
            if self.path=='/api/tags':
                return self.reply(200, {'models':[{'name':args.model_id}]})
            self.reply(404, {'error':'not found'})
        def do_POST(self):
            if self.path!='/api/generate':
                return self.reply(404, {'error':'not found'})
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>1500000:
                return self.reply(400, {'error':'invalid payload size'})
            body=json.loads(self.rfile.read(n).decode('utf-8')); prompt=body.get('prompt')
            if not isinstance(prompt,str) or not prompt:
                return self.reply(400, {'error':'prompt required'})
            with lock:
                counter['n'] += 1; idx=counter['n']
            row={'request_index':idx,'received_at_unix':time.time(),'beast_requested_model':body.get('model'),'cloud_provider':'Hugging Face public Gradio Space','space':args.space,'cloud_model':args.model_id,'api_key_used':False,'prompt':prompt,'prompt_sha256':sha(prompt)}
            try:
                output, endpoint, elapsed=generate(prompt)
                row.update({'success':True,'api_name':endpoint,'elapsed_seconds':elapsed,'response':output,'response_sha256':sha(output),'response_chars':len(output)})
                write(row); self.reply(200, {'response':output,'model':args.model_id,'done':True})
            except Exception as exc:
                row.update({'success':False,'error':f'{type(exc).__name__}: {exc}'})
                write(row); self.reply(502, {'error':row['error']})

    print(json.dumps({'status':'ready','listen':f'127.0.0.1:{args.port}','space':args.space,'model':args.model_id,'api_key_used':False}), flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
