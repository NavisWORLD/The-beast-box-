"""Autoregressive sampling with a correctness-equivalent uncached control."""
import math
import time

import torch


@torch.inference_mode()
def generate(model,ids,max_new_tokens=64,temperature=0.8,top_k=40,eos_token_id=None,
             generator=None,use_cache=True,deadline=None,cancelled=None,control_vector=None,qstate_metric12=None):
    if ids.ndim!=2 or ids.shape[0]!=1: raise ValueError('generation accepts one nonempty prompt')
    if type(max_new_tokens) is not int or not 1<=max_new_tokens<=1024: raise ValueError('invalid token budget')
    if not math.isfinite(temperature) or temperature<0: raise ValueError('invalid temperature')
    if type(top_k) is not int or not 0<=top_k<=model.config.vocab_size: raise ValueError('invalid top_k')
    if ids.shape[1]+max_new_tokens>model.config.max_seq_len: raise ValueError('prompt and output exceed context')
    model.eval(); cache=None; full=ids
    for _ in range(max_new_tokens):
        if (deadline is not None and time.monotonic()>deadline) or (cancelled is not None and cancelled()):
            raise TimeoutError('generation cancelled or timed out')
        current=full[:,-1:] if use_cache and cache is not None else full
        out=model(current,past_key_values=cache if use_cache else None,use_cache=use_cache,
                  control_vector=control_vector,qstate_metric12=qstate_metric12)
        cache=out['past_key_values']; logits=out['logits'][:,-1,:].float()
        if not bool(torch.isfinite(logits).all()): raise FloatingPointError('nonfinite generation logits')
        if temperature==0: token=logits.argmax(-1,keepdim=True)
        else:
            logits=logits/temperature
            if top_k: logits=logits.masked_fill(logits<logits.topk(top_k).values[:,-1:],float('-inf'))
            token=torch.multinomial(torch.softmax(logits,-1),1,generator=generator)
        full=torch.cat((full,token),-1)
        yield token.item(),full
        if eos_token_id is not None and token.item()==eos_token_id: break
