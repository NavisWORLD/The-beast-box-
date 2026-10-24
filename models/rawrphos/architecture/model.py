"""Native PHOS-derived causal language model; no imported checkpoint parameters.

Architecture provenance: QC67 b414724, cosmos_state_ladder.py, PHOS/dyn12.
Differences: tied embeddings, explicit configuration, stable masked softmax,
prefix-correct KV/state caching, safe controls, no automatic weight adaptation.
"""
from dataclasses import asdict, dataclass
import math

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class RawrphosConfig:
    vocab_size: int = 4096
    d_model: int = 192
    n_heads: int = 4
    n_layers: int = 4
    max_seq_len: int = 2048
    state_dim: int = 12
    attention_mode: str = 'dyn12'
    gate_init: float = 0.1
    sigma_init: float = 0.2
    state_dt: float = 0.1
    dropout: float = 0.0
    # 2026-10-22 additive: optional in-context Hebbian fast weights (off = exact old model).
    hebbian: bool = False
    hebbian_dim: int = 32
    hebbian_decay: float = 0.9
    hebbian_rate: float = 0.1
    # 2026-10-22 additive: original-kit state ladder rung (phera-ra/QC67_cosmo@b414724,
    # architecture/cosmos_state_ladder.py Trinity). 'dyn12' = exact old model.
    state_mode: str = 'dyn12'
    # 2026-10-23 additive: optional routed 54D conditioning (12D + 42D slots) with a learnable
    # per-slot gain that starts at ZERO (identical logits at upgrade). Off = exact old model.
    cond54: bool = False

    def __post_init__(self):
        if type(self.hebbian) is not bool or type(self.hebbian_dim) is not int or self.hebbian_dim<1:
            raise ValueError('invalid hebbian configuration')
        if not 0<self.hebbian_decay<1 or not 0<self.hebbian_rate<=1:
            raise ValueError('invalid hebbian decay/rate')
        for name in ['vocab_size','d_model','n_heads','n_layers','max_seq_len','state_dim']:
            if type(getattr(self,name)) is not int or getattr(self,name)<1:
                raise ValueError(f'invalid {name}')
        if self.d_model % self.n_heads or (self.d_model//self.n_heads)%2:
            raise ValueError('heads must divide width and have an even rotary dimension')
        if self.state_mode not in {'dyn12','tri'}: raise ValueError('state_mode must be dyn12 or tri')
        if type(self.cond54) is not bool or (self.cond54 and self.state_mode!='tri'): raise ValueError('cond54 needs state_mode tri')
        if self.state_dim != 12: raise ValueError('this architecture implements dyn12 only')
        if self.attention_mode not in {'dyn12','standard','zero_gate','frozen_state','shuffled_state'}:
            raise ValueError('unsupported attention mode')
        if not 0 < self.gate_init < 1 or not math.isfinite(self.sigma_init) or self.sigma_init <= 0:
            raise ValueError('invalid gate or bandwidth')
        if not 0 <= self.dropout < 1 or not 0 < self.state_dt <= 1:
            raise ValueError('invalid dropout or state time step')

    def to_dict(self):
        d=asdict(self)
        if not self.hebbian:  # keep config.json byte-identical for non-Hebbian checkpoints
            for k in ('hebbian','hebbian_dim','hebbian_decay','hebbian_rate'): d.pop(k)
        if self.state_mode=='dyn12': d.pop('state_mode')
        if not self.cond54: d.pop('cond54')  # byte-identical config.json for non-conditioned checkpoints
        return d
    @classmethod
    def from_dict(cls, value): return cls(**value)


class RMSNorm(nn.Module):
    def __init__(self, width):
        super().__init__(); self.weight=nn.Parameter(torch.ones(width))
    def forward(self,x):
        xf=x.float()
        return (xf*torch.rsqrt(xf.square().mean(-1,keepdim=True)+1e-6)).to(x.dtype)*self.weight


def rotary(x, positions):
    freq=10000.0**(-torch.arange(0,x.shape[-1],2,device=x.device,dtype=torch.float32)/x.shape[-1])
    angles=positions.float()[:,None]*freq[None,:]
    cos,sin=angles.cos().to(x.dtype)[None,None],angles.sin().to(x.dtype)[None,None]
    a,b=x[...,0::2],x[...,1::2]
    return torch.stack((a*cos-b*sin,a*sin+b*cos),-1).flatten(-2)


class Dyn12(nn.Module):
    def __init__(self,dt):
        super().__init__(); self.dt=dt
        self.k=nn.Parameter(torch.linspace(.05,.20,12))
        self.gamma=nn.Parameter(torch.linspace(.02,.10,12))
    def forward(self,state,omega):
        return torch.tanh(state+self.dt*(self.k*omega.unsqueeze(-1)-self.gamma*state))


class Trinity(nn.Module):
    """Faithful port of the original kit's Trinity (cosmos_state_ladder.py:393-434):
    12D and 42D as one coupled system; state is x54=concat(x12,x42).
        dx12/dt = k*Omega - g12*x12 + 0.1*M(42->12) x42
        dx42/dt = tanh(drive(h))*(1+tanh(M(12->42)x12))*(1+lam*Omega) - g42*x42 + 0.1*C(x42)
    Only change: dt comes from config.state_dt (the kit hardcodes 0.1, served default 0.1)."""
    def __init__(self,d_model,dt):
        super().__init__(); self.dt=dt
        self.k=nn.Parameter(torch.linspace(.05,.20,12))
        self.g12=nn.Parameter(torch.linspace(.02,.10,12))
        self.g42=nn.Parameter(torch.full((42,),.05))
        self.drive=nn.Linear(d_model,42)
        self.C=nn.Linear(42,42,bias=False)
        self.m42_12=nn.Linear(42,12,bias=False)
        self.m12_42=nn.Linear(12,42,bias=False)
        self.lam=nn.Parameter(torch.tensor(.5))
    def forward(self,state,h,omega):
        x12,x42=state[...,:12],state[...,12:]; om=omega[...,None]
        gain=1.0+torch.tanh(self.m12_42(x12))
        d12=self.k*om-self.g12*x12+0.1*self.m42_12(x42)
        d42=torch.tanh(self.drive(h))*gain*(1.0+self.lam*om)-self.g42*x42+0.1*self.C(x42)
        return torch.tanh(torch.cat([x12+self.dt*d12,x42+self.dt*d42],-1))


class StateAttention(nn.Module):
    def __init__(self,c):
        super().__init__(); self.config=c
        self.qkv=nn.Linear(c.d_model,3*c.d_model)
        self.proj=nn.Linear(c.d_model,c.d_model)
        self.gate_logit=nn.Parameter(torch.tensor(math.log(c.gate_init/(1-c.gate_init))))
        self.log_sigma=nn.Parameter(torch.tensor(math.log(c.sigma_init)))

    def forward(self,x,state,mask,past=None,return_attention=False):
        c=self.config; b,t,d=x.shape; start=0 if past is None else past['key'].shape[-2]
        q,k,v=self.qkv(x).chunk(3,-1)
        q,k,v=[y.view(b,t,c.n_heads,d//c.n_heads).transpose(1,2) for y in (q,k,v)]
        pos=torch.arange(start,start+t,device=x.device)
        q,k=rotary(q,pos),rotary(k,pos)
        keys=state
        if past is not None:
            k=torch.cat((past['key'],k),-2); v=torch.cat((past['value'],v),-2)
            keys=torch.cat((past['state'],state),1)
        key_pos=torch.arange(k.shape[-2],device=x.device)
        allowed=(key_pos[None,:]<=pos[:,None])[None,None] & mask[:,None,None,:]
        if not bool(allowed.any(-1).all()): raise ValueError('attention row has no valid causal key')
        scores=(q.float()@k.float().transpose(-2,-1))/math.sqrt(d//c.n_heads)
        standard=torch.softmax(scores.masked_fill(~allowed,float('-inf')),-1)
        g=torch.sigmoid(self.gate_logit)
        sigma=self.log_sigma.exp().clamp(1e-4,1e3)
        mode=c.attention_mode
        if mode in {'standard','zero_gate'}:
            mixed=standard; g=g*0
        else:
            qs,ks=state.float(),keys.float()
            if mode=='shuffled_state':
                if not bool(mask.all()): raise ValueError('shuffled-state control requires unpadded input')
                # Each query independently rotates only its own causal prefix.
                # Rotating dimensions alone would preserve all distances and be inert.
                perm=(key_pos[None,:]+(pos[:,None]+1)//2)%(pos[:,None]+1)
                shuffled=ks[:,perm,:]
                distance=(qs[:,:,None,:]-shuffled).square().sum(-1)
            else:
                distance=(qs.square().sum(-1,keepdim=True)+ks.square().sum(-1)[:,None,:]
                          -2*(qs@ks.transpose(-2,-1))).clamp_min(0)
            affinity=torch.softmax((-distance/(2*sigma.square())).masked_fill(~allowed[:,0],float('-inf')),-1)
            mixed=(1-g)*standard+g*affinity[:,None]
        mean=mixed.mean(1)
        entropy=-(mean*mean.clamp_min(1e-30).log()).sum(-1)
        count=allowed[:,0].sum(-1)
        omega=torch.where(count>1,entropy/count.float().log().clamp_min(1e-6),torch.zeros_like(entropy))
        y=F.dropout(mixed,p=c.dropout,training=self.training).to(v.dtype)@v
        y=self.proj(y.transpose(1,2).contiguous().view(b,t,d))
        telemetry={'gate':g.detach(),'sigma':sigma.detach(),'state_norm':state.detach().norm(dim=-1).mean(),
                   'omega_mean':omega.detach().mean()}
        if return_attention: telemetry['attention']=mixed.detach()
        return y,omega,{'key':k,'value':v,'state':keys,'key_mask':mask},telemetry


class HebbianFastWeights(nn.Module):
    """Per-sequence fast-weight memory (ported from closed_loop.py):
    F_t = decay*F_{t-1} + rate * v_t k_t^T, Frobenius-bounded to <=1; read_t = F_{t-1} q_t (causal).
    F is an activation carried in the KV cache: it starts at zero for every new prompt/session and
    is never written back to parameters. The output projection is zero-initialised and scaled by a
    learned gate starting at sigmoid(-4)~0.018, so an upgraded checkpoint starts at identical logits."""
    def __init__(self,c):
        super().__init__(); n=c.hebbian_dim; self.decay=c.hebbian_decay; self.rate=c.hebbian_rate
        self.norm=RMSNorm(c.d_model)
        self.q=nn.Linear(c.d_model,n,bias=False); self.k=nn.Linear(c.d_model,n,bias=False); self.v=nn.Linear(c.d_model,n,bias=False)
        self.out=nn.Linear(n,c.d_model,bias=False)
        self.gate_logit=nn.Parameter(torch.tensor(-4.0))
    def reset_out(self): nn.init.zeros_(self.out.weight)
    def forward(self,x,fast=None):
        b,t,_=x.shape; n=self.q.out_features
        h=self.norm(x); q=torch.tanh(self.q(h)); k=torch.tanh(self.k(h)); v=torch.tanh(self.v(h))
        F_=torch.zeros(b,n,n,device=x.device,dtype=q.dtype) if fast is None else fast
        reads=[]
        for i in range(t):
            reads.append(torch.einsum('bij,bj->bi',F_,q[:,i]))
            F_=self.decay*F_+self.rate*torch.einsum('bi,bj->bij',v[:,i],k[:,i])
            F_=F_/F_.flatten(1).norm(dim=-1).clamp(min=1.0)[:,None,None]
        y=torch.sigmoid(self.gate_logit)*self.out(torch.stack(reads,1))
        return x+y,F_,{'hebbian_gate':torch.sigmoid(self.gate_logit).detach(),'fast_weight_norm':F_.detach().flatten(1).norm(dim=-1).mean()}


class Block(nn.Module):
    def __init__(self,c,final=False):
        super().__init__(); self.n1=RMSNorm(c.d_model); self.n2=RMSNorm(c.d_model)
        self.attn=StateAttention(c)
        hidden=int(c.d_model*((1+5**.5)/2))
        self.ffn=nn.Sequential(nn.Linear(c.d_model,hidden),nn.GELU(),nn.Linear(hidden,c.d_model))
        self.transition=None if final else (Trinity(c.d_model,c.state_dt) if c.state_mode=='tri' else Dyn12(c.state_dt))
    def forward(self,x,state,mask,past=None,return_attention=False):
        h=self.n1(x); y,omega,cache,tel=self.attn(h,state,mask,past,return_attention)
        x=x+y
        if self.transition is not None and self.attn.config.attention_mode!='frozen_state':
            state=self.transition(state,h,omega) if isinstance(self.transition,Trinity) else self.transition(state,omega)
        x=x+self.ffn(self.n2(x))
        return x,state,cache,tel


class RawrphosLM(nn.Module):
    def __init__(self,config):
        super().__init__(); self.config=config
        self.token=nn.Embedding(config.vocab_size,config.d_model)
        self.state_init=nn.Linear(config.d_model,12)
        self.blocks=nn.ModuleList(Block(config,final=i==config.n_layers-1) for i in range(config.n_layers))
        self.norm=RMSNorm(config.d_model)
        self.apply(self._init)
        # Registered LAST so non-Hebbian parameter order (and optimizer indices) are unchanged.
        if config.hebbian:
            self.hebbian=HebbianFastWeights(config); self.hebbian.reset_out()
        if config.state_mode=='tri':
            self.state_init42=nn.Linear(config.d_model,42)
        if config.cond54:
            self.cond_gain=nn.Parameter(torch.zeros(54))  # registered last: older optimizer indices unchanged
    @staticmethod
    def _init(m):
        if isinstance(m,(nn.Linear,nn.Embedding)):
            nn.init.normal_(m.weight,std=.02)
            if getattr(m,'bias',None) is not None: nn.init.zeros_(m.bias)
    @property
    def state_width(self): return 54 if self.config.state_mode=='tri' else 12
    def parameter_count(self): return sum(p.numel() for p in self.parameters())
    def hebbian_parameters(self):
        out=list(self.hebbian.parameters()) if self.config.hebbian else []
        if self.config.state_mode=='tri':  # new Trinity params only; k/g12 continue Dyn12's k/gamma
            out+=list(self.state_init42.parameters())+[p for b in self.blocks if isinstance(b.transition,Trinity)
                for n,p in b.transition.named_parameters() if n not in ('k','g12')]
        if self.config.cond54: out+=[self.cond_gain]
        return out
    def base_parameters(self):
        ids={id(p) for p in self.hebbian_parameters()}
        return [p for p in self.parameters() if id(p) not in ids]

    def forward(self,input_ids,targets=None,attention_mask=None,past_key_values=None,use_cache=False,
                control_vector=None,return_attention=False,condition54=None):
        c=self.config
        if input_ids.ndim!=2 or input_ids.dtype!=torch.long or input_ids.shape[1]<1:
            raise ValueError('input_ids must be a nonempty rank-2 int64 tensor')
        if bool(((input_ids<0)|(input_ids>=c.vocab_size)).any()): raise ValueError('token outside vocabulary')
        b,t=input_ids.shape; start=0
        if past_key_values is not None:
            if len(past_key_values)!=c.n_layers: raise ValueError('cache layer count mismatch')
            start=past_key_values[0]['key'].shape[-2]
            for cache in past_key_values:
                shape=(b,c.n_heads,start,c.d_model//c.n_heads)
                if cache['key'].shape!=shape or cache['value'].shape!=shape or cache['state'].shape!=(b,start,self.state_width):
                    raise ValueError('cache shape mismatch')
        if start+t>c.max_seq_len: raise ValueError('context limit exceeded')
        if attention_mask is None:
            attention_mask=torch.ones((b,start+t),device=input_ids.device,dtype=torch.bool)
        else:
            if attention_mask.shape!=(b,start+t) or not bool(((attention_mask==0)|(attention_mask==1)).all()):
                raise ValueError('attention_mask must be binary and cover complete cache plus input')
            attention_mask=attention_mask.bool()
        if past_key_values is not None and any(not torch.equal(x['key_mask'],attention_mask[:,:start]) for x in past_key_values):
            raise ValueError('cached mask cannot change')
        x=self.token(input_ids); state_logits=self.state_init(x)
        if c.state_mode=='tri': state_logits=torch.cat([state_logits,self.state_init42(x)],-1)
        state=torch.tanh(state_logits)
        if control_vector is not None:
            if control_vector.shape!=(b,12) or not bool(torch.isfinite(control_vector).all()) or bool((control_vector.abs()>1).any()):
                raise ValueError('external state must be finite [batch,12] in [-1,1]')
            # tri: the 12 control scalars drive x12 only; x42 gets zero external input.
            if c.state_mode=='tri': control_vector=torch.cat([control_vector,control_vector.new_zeros(b,42)],-1)
            state=torch.tanh(state_logits+control_vector.to(state)[:,None,:])
        if condition54 is not None:
            if not c.cond54: raise ValueError('this model does not declare cond54')
            if condition54.shape!=(b,54) or not bool(torch.isfinite(condition54).all()) or bool((condition54.abs()>1).any()):
                raise ValueError('condition54 must be finite [batch,54] in [-1,1]')
            # routed slots (masked slots are exactly 0.0 upstream) scaled by the learned per-slot gain
            ext=control_vector.to(state)[:,None,:] if control_vector is not None else 0.
            state=torch.tanh(state_logits+ext+(self.cond_gain.to(state)*condition54.to(state))[:,None,:])
        if c.attention_mode=='frozen_state': state=state.detach()
        caches=[]; telemetry=[]
        for i,block in enumerate(self.blocks):
            x,state,cache,tel=block(x,state,attention_mask,None if past_key_values is None else past_key_values[i],return_attention)
            if use_cache: caches.append(cache)
            telemetry.append(tel)
        if c.hebbian:
            fast=None if past_key_values is None else past_key_values[-1].get('hebbian_fast')
            if past_key_values is not None and fast is None: raise ValueError('hebbian cache missing fast weights')
            x,fast,htel=self.hebbian(x,fast)
            if use_cache: caches[-1]=dict(caches[-1],hebbian_fast=fast)
            telemetry.append(htel)
        logits=F.linear(self.norm(x),self.token.weight)
        loss=None
        if targets is not None:
            if targets.shape!=input_ids.shape: raise ValueError('targets must already be shifted and match input shape')
            if not bool((targets!=-100).any()): raise ValueError('no supervised tokens')
            loss=F.cross_entropy(logits.float().reshape(-1,c.vocab_size),targets.reshape(-1),ignore_index=-100)
        return {'logits':logits,'loss':loss,'past_key_values':caches if use_cache else None,'telemetry':telemetry}


def upgrade_to_hebbian(model,dim=32):
    """Return a Hebbian-enabled copy of a non-Hebbian model. Every existing tensor is copied
    exactly; only hebbian.* is new (zero output => identical logits at upgrade time)."""
    if model.config.hebbian: return model
    cfg=RawrphosConfig.from_dict(dict(asdict(model.config),hebbian=True,hebbian_dim=dim))
    new=RawrphosLM(cfg)
    missing,unexpected=new.load_state_dict(model.state_dict(),strict=False)
    if unexpected or any(not k.startswith('hebbian.') for k in missing):
        raise ValueError('hebbian upgrade may only add hebbian.* parameters')
    return new


def upgrade_to_trinity(model):
    """Return a state_mode='tri' copy of a dyn12 model with IDENTICAL outputs at upgrade:
    Trinity.k/g12 copy Dyn12.k/gamma; state_init42 and Trinity.drive are zeroed so x42 stays 0
    (then d42=0, M(42->12)x42=0, distances unchanged) until training moves drive."""
    if model.config.state_mode=='tri': return model
    new=RawrphosLM(RawrphosConfig.from_dict(dict(asdict(model.config),state_mode='tri')))
    sd=model.state_dict(); tgt=new.state_dict()
    for k,v in sd.items():
        k2=k.replace('transition.gamma','transition.g12')
        if k2 not in tgt: raise ValueError(f'unexpected key {k}')
        tgt[k2]=v.clone()
    for k in tgt:
        if k.startswith('state_init42.') or '.transition.drive.' in k: tgt[k]=torch.zeros_like(tgt[k])
    new.load_state_dict(tgt); return new


def upgrade_to_cond54(model):
    """Return a cond54 copy of a tri model with IDENTICAL outputs at upgrade: only cond_gain is new
    and it starts at zero, so routed conditioning has no effect until training moves it."""
    if model.config.cond54: return model
    if model.config.state_mode!='tri': raise ValueError('cond54 upgrade needs a tri model')
    new=RawrphosLM(RawrphosConfig.from_dict(dict(asdict(model.config),cond54=True)))
    missing,unexpected=new.load_state_dict(model.state_dict(),strict=False)
    if unexpected or missing!=['cond_gain']: raise ValueError('cond54 upgrade may only add cond_gain')
    return new


def grow_depth(model,add=2):
    """Function-preserving (Net2Net-style) depth growth for repeatable capacity expansion.
    Every existing tensor is copied exactly; `add` new blocks are appended whose attention
    output projection and MLP output layer are zero, so each new block is an identity residual
    and logits are IDENTICAL at growth time. The old final block gains a state transition
    (copied from block 0); its state only feeds the zero-output new blocks. Returns
    (grown_model, new_parameter_ids) so trainers can give new params fresh optimizer moments."""
    if type(add) is not int or add<1: raise ValueError('grow_depth adds >=1 blocks (no size cap; physical limits are checked by the trigger)')
    c=model.config; n=c.n_layers
    new=RawrphosLM(RawrphosConfig.from_dict(dict(asdict(c),n_layers=n+add)))
    sd=model.state_dict(); tgt=new.state_dict()
    for k,v in sd.items():
        if k not in tgt or tgt[k].shape!=v.shape: raise ValueError(f'growth may only add parameters ({k})')
        tgt[k]=v.clone()
    for k in tgt:
        if k.startswith(f'blocks.{n-1}.transition.'): tgt[k]=sd[k.replace(f'blocks.{n-1}.','blocks.0.',1)].clone()
        if any(k.startswith(f'blocks.{i}.') for i in range(n,n+add)) and ('.attn.proj.' in k or '.ffn.2.' in k):
            tgt[k]=torch.zeros_like(tgt[k])
    new.load_state_dict(tgt)
    fresh={id(p) for name,p in new.named_parameters()
           if name.startswith(f'blocks.{n-1}.transition.') or any(name.startswith(f'blocks.{i}.') for i in range(n,n+add))}
    return new,fresh
