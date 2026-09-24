"""One loaded native checkpoint, bounded serial generation and measured timing."""
import threading
import time
import torch
from rawrphos.training.checkpoint import load_checkpoint
from rawrphos.inference.snapshot import load_inference_snapshot
from pathlib import Path
from rawrphos.architecture.generation import generate

class Engine:
    def __init__(self,checkpoint,max_new_tokens=256,threads=4,expected_sha256=None,device='cpu'):
        if type(max_new_tokens) is not int or not 1<=max_new_tokens<=1024: raise ValueError('invalid host token budget')
        if device not in {'cpu', 'cuda'}: raise ValueError('unsupported inference device')
        torch.set_num_threads(threads); started=time.perf_counter()
        if (Path(checkpoint) / "inference-manifest.json").is_file():
            if expected_sha256 is None:
                raise ValueError("published inference snapshots require a pinned weight SHA")
            loaded = load_inference_snapshot(checkpoint, expected_checkpoint_sha256=expected_sha256)
        else:
            loaded = load_checkpoint(checkpoint,expected_checkpoint_sha256=expected_sha256,load_training_state=False)
        self.model=loaded['model'].eval().to(device); self.device=device
        self.tokenizer=loaded['tokenizer']; self.metadata=loaded['metadata']
        self.load_seconds=time.perf_counter()-started; self.max_new_tokens=max_new_tokens
        self.lock=threading.Lock(); self.last_success=None; self.last_metrics={}
    def info(self):
        m=self.metadata
        return {'model_id':'rawrphos-native','display_name':'RAWRPHØS','family':'RAWRPHOS',
            'architecture':self.model.config.to_dict(),'parameter_count':self.model.parameter_count(),
            'checkpoint_sha256':m['checkpoint_sha256'],'tokenizer_sha256':m['tokenizer_sha256'],
            'context_limit':self.model.config.max_seq_len,'training_seq_len':m.get('training_seq_len'),
            'context_extrapolation_validated':False,'training_steps':m['training_steps'],
            'lineage':'native-from-scratch','serving_backend':'pytorch-cpu','quantization':None,
            'release_status':m.get('release_status','trained-candidate'),'ready':True,
            'load_seconds':self.load_seconds,'last_successful_inference':self.last_success,
            'weight_bytes':sum(p.numel()*p.element_size() for p in self.model.parameters())}
    def tokens(self,prompt,max_tokens=64,temperature=.8,seed=67,use_cache=True,timeout=60,cancelled=None):
        if not isinstance(prompt,str) or len(prompt.encode('utf-8'))>65536: raise ValueError('invalid or oversized prompt')
        if type(max_tokens) is not int or not 1<=max_tokens<=self.max_new_tokens: raise ValueError('token budget exceeds host limit')
        t0=time.perf_counter(); ids=self.tokenizer.encode(prompt,add_bos=True); tokenize=time.perf_counter()-t0
        if len(ids)+max_tokens>self.model.config.max_seq_len: raise ValueError('prompt plus output exceeds context limit')
        if not self.lock.acquire(blocking=False): raise RuntimeError('native provider is busy')
        try:
            gen=torch.Generator(device=self.device).manual_seed(seed); started=time.perf_counter(); first=None; generated=[]; emitted=''
            for token,full in generate(self.model,torch.tensor([ids],device=self.device),max_new_tokens=max_tokens,
                    temperature=temperature,top_k=min(40,self.tokenizer.vocab_size),eos_token_id=self.tokenizer.eos_id,
                    generator=gen,use_cache=use_cache,deadline=time.monotonic()+timeout,cancelled=cancelled):
                if first is None: first=time.perf_counter()-started
                generated.append(token); decoded=self.tokenizer.decode(generated); stable=decoded.rstrip('\ufffd')
                delta=stable[len(emitted):]; emitted=stable
                yield delta
            decoded=self.tokenizer.decode(generated)
            if len(decoded)>len(emitted): yield decoded[len(emitted):]
            seconds=time.perf_counter()-started
            self.last_metrics={'tokenization_seconds':tokenize,'prefill_and_first_token_seconds':first,
                'generation_seconds':seconds,'prompt_tokens':len(ids),'generated_tokens':len(generated),
                'eos_emitted':bool(generated and generated[-1]==self.tokenizer.eos_id),
                'finish_reason':'stop' if generated and generated[-1]==self.tokenizer.eos_id else 'length',
                'decode_tokens_per_second':(len(generated)-1)/max(1e-9,seconds-(first or seconds)) if len(generated)>1 else None,
                'total_tokens_per_second':len(generated)/max(seconds,1e-9),'cache_enabled':use_cache}
            self.last_success=time.time()
        finally: self.lock.release()
    def complete(self,prompt,**kwargs): return ''.join(self.tokens(prompt,**kwargs))
