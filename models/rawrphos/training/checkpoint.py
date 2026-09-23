"""Immutable atomic bundles. Safe tensor load; no unrestricted pickle."""
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import uuid
import torch
from safetensors.torch import save_file,load_file
from rawrphos.architecture.model import RawrphosConfig,RawrphosLM
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer

def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()
def parameter_hash(model):
    h=hashlib.sha256()
    for name,tensor in sorted(model.state_dict().items()):
        h.update(name.encode()); h.update(str(tensor.dtype).encode()); h.update(str(list(tensor.shape)).encode())
        h.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()

def save_checkpoint(path,model,tokenizer,metadata,state):
    # Fail before creating a bundle: finite grads do not guarantee finite weights.
    if not all(bool(torch.isfinite(v).all()) for v in model.state_dict().values()):
        raise FloatingPointError('refusing to checkpoint nonfinite model parameters')
    # Inference-only synthetic fixtures historically save RNG but no optimizer.
    # Check moments when present; real training/resume still requires all states.
    if 'optimizer' in state and not all(bool(torch.isfinite(v).all()) for entry in state['optimizer']['state'].values()
               for v in entry.values() if isinstance(v,torch.Tensor)):
        raise FloatingPointError('refusing to checkpoint nonfinite optimizer state')
    path=Path(path)
    if path.exists(): raise FileExistsError('checkpoint already exists')
    temp=path.parent/(path.name+'.tmp-'+uuid.uuid4().hex); temp.mkdir(parents=True)
    try:
        save_file({k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()},str(temp/'model.safetensors'))
        (temp/'config.json').write_text(json.dumps(model.config.to_dict(),sort_keys=True))
        tokenizer.save(temp/'tokenizer')
        metadata=dict(metadata,model_id='rawrphos-native',family='RAWRPHOS',lineage='native-from-scratch',
            parameter_count=model.parameter_count(),parameter_sha256=parameter_hash(model),tokenizer_sha256=tokenizer.sha256,
            checkpoint_sha256=hash_file(temp/'model.safetensors'))
        (temp/'metadata.json').write_text(json.dumps(metadata,sort_keys=True,indent=2))
        torch.save(state,temp/'training_state.pt')
        files={str(p.relative_to(temp)):hash_file(p) for p in sorted(temp.rglob('*')) if p.is_file()}
        (temp/'manifest.json').write_text(json.dumps({'schema':'rawrphos-checkpoint-v1','files':files},sort_keys=True,indent=2))
        for p in temp.rglob('*'):
            if p.is_file():
                with p.open('rb') as f: os.fsync(f.fileno())
        os.rename(temp,path)
        if os.name=='posix':
            fd=os.open(path.parent,os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        return metadata
    finally:
        if temp.exists(): shutil.rmtree(temp)

def load_checkpoint(path,require_trained=True,expected_checkpoint_sha256=None,load_training_state=True):
    p=Path(path)
    if p.is_symlink(): raise ValueError('checkpoint must not be a symlink')
    manifest=json.loads((p/'manifest.json').read_text())
    required={'model.safetensors','config.json','metadata.json','training_state.pt','tokenizer/tokenizer.json','tokenizer/metadata.json'}
    if manifest.get('schema')!='rawrphos-checkpoint-v1' or set(manifest.get('files',{}))!=required:
        raise ValueError('invalid checkpoint manifest')
    for name,digest in manifest['files'].items():
        target=p/name
        if target.is_symlink() or hash_file(target)!=digest: raise ValueError('checkpoint file hash mismatch: '+name)
    metadata=json.loads((p/'metadata.json').read_text()); c=RawrphosConfig.from_dict(json.loads((p/'config.json').read_text()))
    if metadata.get('model_id')!='rawrphos-native' or metadata.get('lineage')!='native-from-scratch': raise ValueError('model identity mismatch')
    if require_trained and (type(metadata.get('training_steps')) is not int or metadata['training_steps']<1): raise ValueError('untrained checkpoint')
    if metadata['checkpoint_sha256']!=manifest['files']['model.safetensors']: raise ValueError('checkpoint identity hash mismatch')
    if expected_checkpoint_sha256 is not None and metadata['checkpoint_sha256']!=expected_checkpoint_sha256: raise ValueError('unexpected checkpoint hash')
    tokenizer=RawrphosTokenizer.load(p/'tokenizer')
    if tokenizer.sha256!=metadata['tokenizer_sha256'] or tokenizer.vocab_size!=c.vocab_size: raise ValueError('tokenizer/model mismatch')
    model=RawrphosLM(c); model.load_state_dict(load_file(str(p/'model.safetensors')),strict=True)
    if not all(bool(torch.isfinite(v).all()) for v in model.state_dict().values()):
        raise ValueError('checkpoint contains nonfinite model parameters')
    if model.parameter_count()!=metadata['parameter_count'] or parameter_hash(model)!=metadata['parameter_sha256']: raise ValueError('parameter identity mismatch')
    state=torch.load(p/'training_state.pt',map_location='cpu',weights_only=True) if load_training_state else None
    if state is not None:
        if not isinstance(state,dict) or not {'optimizer','rng','data_rng'} <= state.keys():
            raise ValueError('incomplete optimizer/RNG resume state')
        if not all(bool(torch.isfinite(v).all()) for entry in state['optimizer']['state'].values()
                   for v in entry.values() if isinstance(v,torch.Tensor)):
            raise ValueError('checkpoint contains nonfinite optimizer state')
    return {'model':model,'tokenizer':tokenizer,'metadata':metadata,'state':state,'config':c,'manifest':manifest}

def rng_state(): return {'torch':torch.get_rng_state(),'python':random.getstate()}
def restore_rng(value): torch.set_rng_state(value['torch']); random.setstate(value['python'])
