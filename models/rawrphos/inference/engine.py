"""One loaded native checkpoint, bounded serial generation and measured timing."""
import threading
import time
import math
import hashlib
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
    def tokens(self,prompt,max_tokens=64,temperature=.8,seed=67,use_cache=True,timeout=60,cancelled=None,control_vector=None):
        if not isinstance(prompt,str) or len(prompt.encode('utf-8'))>65536: raise ValueError('invalid or oversized prompt')
        if type(max_tokens) is not int or not 1<=max_tokens<=self.max_new_tokens: raise ValueError('token budget exceeds host limit')
        t0=time.perf_counter(); ids=self.tokenizer.encode(prompt,add_bos=True); tokenize=time.perf_counter()-t0
        if len(ids)+max_tokens>self.model.config.max_seq_len: raise ValueError('prompt plus output exceeds context limit')
        if not self.lock.acquire(blocking=False): raise RuntimeError('native provider is busy')
        try:
            gen=torch.Generator(device=self.device).manual_seed(seed); started=time.perf_counter(); first=None; generated=[]; emitted=''
            for token,full in generate(self.model,torch.tensor([ids],device=self.device),max_new_tokens=max_tokens,
                    temperature=temperature,top_k=min(40,self.tokenizer.vocab_size),eos_token_id=self.tokenizer.eos_id,
                    generator=gen,use_cache=use_cache,deadline=time.monotonic()+timeout,cancelled=cancelled,
                    control_vector=control_vector):
                if first is None: first=time.perf_counter()-started
                generated.append(token); decoded=self.tokenizer.decode(generated); stable=decoded.rstrip('\ufffd')
                delta=stable[len(emitted):]; emitted=stable
                yield delta
            decoded=self.tokenizer.decode(generated)
            if len(decoded)>len(emitted): yield decoded[len(emitted):]
            seconds=time.perf_counter()-started
            self.last_metrics={'tokenization_seconds':tokenize,'prefill_and_first_token_seconds':first,
                'generation_seconds':seconds,'prompt_tokens':len(ids),'generated_tokens':len(generated),
                'decode_tokens_per_second':(len(generated)-1)/max(1e-9,seconds-(first or seconds)) if len(generated)>1 else None,
                'total_tokens_per_second':len(generated)/max(seconds,1e-9),'cache_enabled':use_cache}
            self.last_success=time.time()
        finally: self.lock.release()
    @staticmethod
    def validate_control(value):
        """External numeric controls are data, never model tools or authority."""
        if (not isinstance(value,list) or len(value)!=12 or
            any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1 for x in value)):
            raise ValueError('control_vector must be 12 finite values in [-1,1]')
        return [float(x) for x in value]

    @torch.inference_mode()
    def condition_probe(self,prompt,control_vector,max_tokens=24,seed=67):
        """Matched reference/zero/rotated/real input with ONE immutable model.

        Logit distance establishes numerical influence only, not useful behavior,
        learned benefit, physical sensor attestation or quantum advantage.
        """
        from rawrphos.architecture.generation import generate
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=220:
            raise ValueError('probe prompt must be 1..220 characters')
        if type(max_tokens) is not int or not 1<=max_tokens<=32:
            raise ValueError('probe max_tokens must be 1..32')
        if type(seed) is not int or not 0<=seed<2**63:
            raise ValueError('invalid fixed probe seed')
        controls=self.validate_control(control_vector)
        ids=self.tokenizer.encode(prompt,add_bos=True)
        if len(ids)+max_tokens>min(self.model.config.max_seq_len,384):
            raise ValueError('probe input exceeds tested 384 token window')
        if not self.lock.acquire(blocking=False):
            raise RuntimeError('native provider is busy')
        try:
            input_ids=torch.tensor([ids],device=self.device)
            vectors={'reference':None,'zero_input':[0.0]*12,
                'rotated_input':controls[1:]+controls[:1],'conditioned':controls}
            logits={}
            norm={}; gates={}
            started=time.monotonic()
            for label,values in vectors.items():
                cv=None if values is None else torch.tensor([values],dtype=torch.float32,device=self.device)
                forward=self.model(input_ids,control_vector=cv)
                logits[label]=forward['logits'][:,-1,:].float()
                norm[label]=round(float(cv.norm()) if cv is not None else 0.0,8)
                gates[label]=[round(float(t['gate']),8) for t in forward['telemetry']]
                if time.monotonic()-started>18:raise TimeoutError('matched probe timeout')
            def distance(a,b):
                return round(float(torch.linalg.vector_norm(logits[a]-logits[b])),10)
            def run_one(values):
                cv=None if values is None else torch.tensor([values],dtype=torch.float32,device=self.device)
                g=torch.Generator(device=self.device).manual_seed(seed)
                out=[]
                for token,_ in generate(self.model,input_ids,max_new_tokens=max_tokens,temperature=0,
                    eos_token_id=self.tokenizer.eos_id,generator=g,use_cache=True,
                    deadline=time.monotonic()+18,control_vector=cv):
                    out.append(token)
                return self.tokenizer.decode(out)
            raw=run_one(None)
            conditioned=run_one(controls)
            return {'model_id':'rawrphos-native','training_steps':self.metadata['training_steps'],
                'checkpoint_sha256':self.metadata['checkpoint_sha256'],
                'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                'control_sha256':hashlib.sha256(torch.tensor(controls,dtype=torch.float32).numpy().tobytes()).hexdigest(),
                'controls':{'reference':{'state_norm':norm['reference']},
                            'zero_input':{'state_norm':norm['zero_input']},
                            'rotated_input':{'state_norm':norm['rotated_input']},
                            'conditioned':{'state_norm':norm['conditioned']}},
                'gate_by_layer':gates['conditioned'],
                'logit_l2':{'zero_vs_reference':distance('zero_input','reference'),
                    'conditioned_vs_reference':distance('conditioned','reference'),
                    'conditioned_vs_rotated':distance('conditioned','rotated_input')},
                'response_reference':raw,'response_conditioned':conditioned,
                'equal_fixed_seed':raw==conditioned,
                'performance_gain_proven':False,'model_weights_changed':False,
                'controls_are_retrained_models':False,'duration_ms':round((time.monotonic()-started)*1000,3)}
        finally:self.lock.release()

    def complete(self,prompt,**kwargs): return ''.join(self.tokens(prompt,**kwargs))
