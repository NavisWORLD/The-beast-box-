"""Optional demo adapter: load the user's existing pinned native weights on CPU.

This is a demonstration driver, not a dependency of the portable bridge.
No checkpoint download, network inference, training, tools or authority.
"""
import hashlib,json,sys
from pathlib import Path
repo,checkpoint,weight_hash,context_json=sys.argv[1:]
sys.path.insert(0,str(Path(repo)/'models'))
from rawrphos.inference.engine import Engine
context=json.loads(context_json)
memories=' | '.join(m['summary'] for m in context['memories']) or 'No approved memories yet.'
prompt=f"User: You are {context['name']}, a {context['family']} companion ({context['creature_id']}). Public memories: {memories} User says: {context['user']} Reply briefly.\nAssistant:"
engine=Engine(checkpoint,max_new_tokens=48,threads=2,expected_sha256=weight_hash)
output=engine.complete(prompt,max_tokens=48,temperature=0,seed=67)
print(json.dumps({'model':'RAWRPHOS-native','training_steps':engine.metadata['training_steps'],
 'weight_sha256':weight_hash,'prompt':prompt,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
 'output':output,'metrics':engine.last_metrics,'network_inference':False,'paid_api_calls':0}))
