"""Autoregressive sampling with a correctness-equivalent uncached control."""
import math
import time
import torch


@torch.inference_mode()
def generate(model,ids,max_new_tokens=64,temperature=0.8,top_k=40,eos_token_id=None,
             generator=None,use_cache=True,deadline=None,cancelled=None,control_vector=None,
             repetition_penalty=1.0,no_repeat_ngram=0,condition54=None):
    if ids.ndim!=2 or ids.shape[0]!=1: raise ValueError('generation accepts one nonempty prompt')
    if type(max_new_tokens) is not int or not 1<=max_new_tokens<=1024: raise ValueError('invalid token budget')
    if not math.isfinite(temperature) or temperature<0: raise ValueError('invalid temperature')
    if type(top_k) is not int or not 0<=top_k<=model.config.vocab_size: raise ValueError('invalid top_k')
    if ids.shape[1]+max_new_tokens>model.config.max_seq_len: raise ValueError('prompt and output exceed context')
    if not math.isfinite(repetition_penalty) or repetition_penalty<1: raise ValueError('invalid repetition_penalty')
    if type(no_repeat_ngram) is not int or no_repeat_ngram<0: raise ValueError('invalid no_repeat_ngram')
    model.eval(); cache=None; full=ids; start=ids.shape[1]
    for _ in range(max_new_tokens):
        if (deadline is not None and time.monotonic()>deadline) or (cancelled is not None and cancelled()):
            raise TimeoutError('generation cancelled or timed out')
        current=full[:,-1:] if use_cache and cache is not None else full
        out=model(current,past_key_values=cache if use_cache else None,use_cache=use_cache,
                  control_vector=control_vector,**({'condition54':condition54} if condition54 is not None else {}))
        cache=out['past_key_values']; logits=out['logits'][:,-1,:].float()
        if not bool(torch.isfinite(logits).all()): raise FloatingPointError('nonfinite generation logits')
        # Optional anti-repetition over GENERATED tokens only (defaults = old behavior).
        gen=full[0,start:].tolist()
        if repetition_penalty>1 and gen:
            seen=torch.tensor(sorted(set(gen)),device=logits.device)
            v=logits[0,seen]; logits[0,seen]=torch.where(v>0,v/repetition_penalty,v*repetition_penalty)
        n=no_repeat_ngram
        if n and len(gen)>=n:
            prefix=tuple(gen[-(n-1):]) if n>1 else ()
            banned={gen[i+n-1] for i in range(len(gen)-n+1) if tuple(gen[i:i+n-1])==prefix}
            if banned: logits[0,list(banned)]=float('-inf')
        if temperature==0: token=logits.argmax(-1,keepdim=True)
        else:
            logits=logits/temperature
            if top_k: logits=logits.masked_fill(logits<logits.topk(top_k).values[:,-1:],float('-inf'))
            token=torch.multinomial(torch.softmax(logits,-1),1,generator=generator)
        full=torch.cat((full,token),-1)
        yield token.item(),full
        if eos_token_id is not None and token.item()==eos_token_id: break
