"""Thin native adapter; Beast Box still owns memory, R12, policy and transactions."""
import json
import os
import urllib.request
from rawrphos.inference.engine import Engine

LOCAL_URL='http://127.0.0.1:8767/v1'
KEY_ENV='RAWRPHOS_API_KEY'

class NativeProvider:
    model='rawrphos-native'
    def __init__(self,checkpoint,max_new_tokens=64,threads=4):
        self.engine=Engine(checkpoint,max_new_tokens,threads); self.max_new_tokens=max_new_tokens; self.last_response=None
    def generate(self,prompt):
        self.last_response=self.engine.complete(prompt,max_tokens=self.max_new_tokens,temperature=0)
        return self.last_response

def compatible_profile():
    return {'kind':'compatible','model':'rawrphos-native','base_url':LOCAL_URL,'allow_remote':False,'api_key_env':KEY_ENV}

def host_info():
    from beastbox.providers import _local_opener
    key=os.environ.get(KEY_ENV,'')
    if len(key)<32 or any(c in key for c in '\r\n'): raise ValueError('native authorization unavailable')
    request=urllib.request.Request(LOCAL_URL.removesuffix('/v1')+'/model/info',headers={'Authorization':'Bearer '+key})
    try:
        with _local_opener().open(request,timeout=5) as response: raw=response.read(16385)
        if len(raw)>16384: raise ValueError('metadata too large')
        info=json.loads(raw)
        if info.get('model_id')!='rawrphos-native' or info.get('lineage')!='native-from-scratch' or info.get('training_steps',0)<1 or info.get('ready') is not True: raise ValueError('native model is not ready')
        return info
    except (OSError,ValueError,KeyError,TypeError): raise ValueError('verified native inference unavailable; no fallback') from None
