"""Authenticated local inference. No network provider or canned fallback."""
import argparse
import hmac
import json
import math
import os
import time
import uuid
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,StreamingResponse
from rawrphos.inference.engine import Engine

def create_app(checkpoint,api_key,max_new_tokens=256,threads=4,expected_sha256=None):
    if not isinstance(api_key,str) or len(api_key)<32 or any(c in api_key for c in '\r\n'): raise ValueError('strong host API key required')
    engine=Engine(checkpoint,max_new_tokens,threads,expected_sha256); app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    app.state.engine=engine; app.state.api_key=api_key
    @app.middleware('http')
    async def auth(request,call_next):
        if request.url.path!='/health':
            provided=request.headers.get('authorization','')
            if not hmac.compare_digest(provided,'Bearer '+app.state.api_key): return JSONResponse({'error':'authorization required'},status_code=401)
        if request.method=='POST':
            length=request.headers.get('content-length','')
            if not length.isdigit() or int(length)>65536: return JSONResponse({'error':'bounded Content-Length required'},status_code=413)
        return await call_next(request)
    @app.get('/health')
    def health(): return {'status':'alive'}
    @app.get('/ready')
    def ready(): return {'ready':True,'model_id':'rawrphos-native','checkpoint_sha256':engine.metadata['checkpoint_sha256']}
    @app.get('/model/info')
    def info(): return engine.info()
    @app.get('/v1/models')
    def models(): return {'object':'list','data':[{'id':'rawrphos-native','object':'model','owned_by':'Cory Davis / COSMOS'}]}

    async def completion(request,chat=False):
        try:
            body=await request.json()
            if not isinstance(body,dict) or set(body)-{'model','prompt','messages','max_tokens','temperature','stream','seed'}: raise ValueError('unsupported request fields')
            if body.get('model')!='rawrphos-native': raise ValueError('unknown model')
            temperature=body.get('temperature',.8); count=body.get('max_tokens',64); seed=body.get('seed',67)
            if isinstance(temperature,bool) or not isinstance(temperature,(int,float)) or not math.isfinite(temperature) or temperature<0: raise ValueError('invalid temperature')
            if type(count) is not int or not 1<=count<=engine.max_new_tokens: raise ValueError('invalid token budget')
            if type(seed) is not int or not 0<=seed<2**63 or type(body.get('stream',False)) is not bool: raise ValueError('invalid seed or stream')
            if chat:
                messages=body.get('messages')
                if not isinstance(messages,list) or not 1<=len(messages)<=32: raise ValueError('invalid messages')
                if any(not isinstance(m,dict) or set(m)!={'role','content'} or m['role'] not in {'system','user','assistant'} or not isinstance(m['content'],str) for m in messages): raise ValueError('text messages required')
                prompt='\n'.join(f"{m['role']}: {m['content']}" for m in messages)+'\nassistant:'
            else: prompt=body.get('prompt')
            if not isinstance(prompt,str) or len(prompt.encode())>65536: raise ValueError('invalid prompt')
            if len(engine.tokenizer.encode(prompt,add_bos=True))+count>engine.model.config.max_seq_len: raise ValueError('context limit exceeded')
        except (ValueError,TypeError,KeyError,UnicodeError):
            return JSONResponse({'error':'invalid request, model ID, or context/token limit'},status_code=400)
        identifier='rawrphos-'+uuid.uuid4().hex
        if body.get('stream',False):
            def events():
                try:
                    for delta in engine.tokens(prompt,max_tokens=count,temperature=temperature,seed=seed):
                        choice={'index':0,'delta':{'content':delta}} if chat else {'index':0,'text':delta}
                        yield 'data: '+json.dumps({'id':identifier,'model':'rawrphos-native','choices':[choice]})+'\n\n'
                    yield 'data: [DONE]\n\n'
                except (ValueError,RuntimeError,TimeoutError,FloatingPointError):
                    yield 'data: '+json.dumps({'error':'native inference failed; no fallback'})+'\n\n'
            return StreamingResponse(events(),media_type='text/event-stream')
        try:
            # CPU generation runs off the asynchronous request loop.
            from starlette.concurrency import run_in_threadpool
            text=await run_in_threadpool(engine.complete,prompt,max_tokens=count,temperature=temperature,seed=seed)
            choice={'index':0,'message':{'role':'assistant','content':text}} if chat else {'index':0,'text':text}
            choice['finish_reason']='length' if engine.last_metrics['generated_tokens']==count else 'stop'
            usage={'prompt_tokens':engine.last_metrics['prompt_tokens'],'completion_tokens':engine.last_metrics['generated_tokens']}
            usage['total_tokens']=sum(usage.values())
            return {'id':identifier,'object':'chat.completion' if chat else 'text_completion','created':int(time.time()),
                'model':'rawrphos-native','choices':[choice],'usage':usage,'checkpoint_sha256':engine.metadata['checkpoint_sha256']}
        except (ValueError,RuntimeError,TimeoutError,FloatingPointError):
            return JSONResponse({'error':'native inference unavailable; no fallback'},status_code=503)
    @app.post('/v1/condition-probe')
    async def condition_probe(request:Request):
        try:
            body=await request.json()
            if (not isinstance(body,dict) or set(body)!={'model','prompt','control_vector','max_tokens','seed'}
                or body.get('model')!='rawrphos-native'):
                raise ValueError('invalid probe shape')
            vector=Engine.validate_control(body.get('control_vector'))
            prompt=body['prompt'];count=body['max_tokens'];seed=body['seed']
            if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=220 or type(count) is not int or not 1<=count<=32 or type(seed) is not int or not 0<=seed<2**63:
                raise ValueError('invalid probe values')
        except (ValueError,TypeError,KeyError,UnicodeError):
            return JSONResponse({'error':'invalid bounded native conditioning probe'},status_code=400)
        try:
            from starlette.concurrency import run_in_threadpool
            result=await run_in_threadpool(engine.condition_probe,prompt,vector,count,seed)
            return result
        except RuntimeError:
            return JSONResponse({'error':'native probe busy'},status_code=429)
        except (ValueError,TimeoutError,FloatingPointError):
            return JSONResponse({'error':'native conditioning probe unavailable; no fallback'},status_code=503)

    @app.post('/v1/condition-probe-v2')
    async def condition_probe_v2(request:Request):
        try:
            body=await request.json()
            if (not isinstance(body,dict) or set(body)!={'model','prompt','arms','max_tokens','seed'}
                or body.get('model')!='rawrphos-native'):
                raise ValueError('invalid v2 probe shape')
            prompt=body['prompt'];arms=body['arms'];count=body['max_tokens'];seed=body['seed']
            if (not isinstance(prompt,str) or not 1<=len(prompt.strip())<=220
                or type(count) is not int or not 1<=count<=32
                or type(seed) is not int or not 0<=seed<2**63
                or not isinstance(arms,dict) or not 2<=len(arms)<=10):
                raise ValueError('invalid v2 probe values')
        except (ValueError,TypeError,KeyError,UnicodeError):
            return JSONResponse({'error':'invalid bounded native conditioning v2 probe'},status_code=400)
        try:
            from starlette.concurrency import run_in_threadpool
            result=await run_in_threadpool(engine.condition_probe_v2,prompt,arms,count,seed)
            return result
        except RuntimeError:
            return JSONResponse({'error':'native probe busy'},status_code=429)
        except (ValueError,TimeoutError,FloatingPointError):
            return JSONResponse({'error':'native conditioning v2 probe unavailable; no fallback'},status_code=503)

    @app.post('/v1/completions')
    async def text_completion(request:Request): return await completion(request)
    @app.post('/v1/chat/completions')
    async def chat_completion(request:Request): return await completion(request,True)
    return app

def main():
    p=argparse.ArgumentParser(); p.add_argument('--checkpoint',required=True); p.add_argument('--port',type=int,default=8767)
    p.add_argument('--threads',type=int,default=4); p.add_argument('--expected-sha256'); args=p.parse_args()
    import uvicorn
    app=create_app(args.checkpoint,os.environ.get('RAWRPHOS_API_KEY',''),threads=args.threads,expected_sha256=args.expected_sha256)
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)
if __name__=='__main__': main()
