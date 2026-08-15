#!/usr/bin/env python3
"""Export a D001 checkpoint to the custom COSMOS GGUF architecture.

The numerical mapping matches the frozen historical CST converter: sigma is
folded into W54 and the effective gate is emitted as a scalar tensor. Metadata
is intentionally different: D001 does not inherit the historical converter's
unsupported blanket IBM-hardware birth claim.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import torch
from gguf import GGUFWriter

from beastbox.descendant.gguf import build_description


def convert(src: Path, dst: Path) -> None:
    ck=torch.load(src,map_location='cpu',weights_only=False)
    sd,cfg=ck['model'],ck['config']
    n_embd,n_layer=int(cfg['n_embd']),int(cfg['n_layer'])
    n_head,vocab=int(cfg['n_head']),int(cfg['vocab'])
    block,d54=int(cfg['block']),int(cfg['d54'])
    head_dim=n_embd//n_head; n_ff=4*n_embd

    writer=GGUFWriter(str(dst),'cosmos')
    writer.add_architecture(); writer.add_name(f"COSMOS Zeref D001 {ck.get('stage','UNKNOWN')}")
    writer.add_description(build_description(ck)); writer.add_file_type(0)
    writer.add_context_length(block); writer.add_embedding_length(n_embd); writer.add_block_count(n_layer)
    writer.add_feed_forward_length(n_ff); writer.add_head_count(n_head); writer.add_head_count_kv(n_head)
    writer.add_key_length(head_dim+d54); writer.add_value_length(head_dim); writer.add_layer_norm_eps(1e-5); writer.add_vocab_size(vocab)
    itos=ck.get('itos') or {v:k for k,v in ck['stoi'].items()}
    tokens=[itos[i] for i in range(vocab)]
    writer.add_tokenizer_model('rwkv'); writer.add_token_list(tokens); writer.add_token_types([1]*vocab)
    writer.add_add_bos_token(False); writer.add_add_eos_token(False)

    def tensor(name,arr):
        writer.add_tensor(name,np.ascontiguousarray(arr.detach().float().cpu().numpy()))

    tensor('token_embd.weight',sd['tok.weight']); tensor('position_embd.weight',sd['pos.weight'])
    tensor('output_norm.weight',sd['lnf.weight']); tensor('output_norm.bias',sd['lnf.bias']); tensor('output.weight',sd['head.weight'])
    gate_param=ck.get('gate_param')
    raw_gates=[float(sd[f'blocks.{i}.attn.gate'].reshape(-1)[0]) for i in range(n_layer)]
    if gate_param is None: gate_param='logit' if max(abs(r) for r in raw_gates)>1.0 else 'clamp01'
    def gate_fn(raw: float) -> float:
        if gate_param=='logit': return 1.0/(1.0+math.exp(-raw))
        return max(0.0,min(1.0,raw))

    for i in range(n_layer):
        p=f'blocks.{i}.'
        tensor(f'blk.{i}.attn_norm.weight',sd[p+'ln1.weight']); tensor(f'blk.{i}.attn_norm.bias',sd[p+'ln1.bias'])
        tensor(f'blk.{i}.attn_qkv.weight',sd[p+'attn.qkv.weight']); tensor(f'blk.{i}.attn_qkv.bias',sd[p+'attn.qkv.bias'])
        tensor(f'blk.{i}.attn_output.weight',sd[p+'attn.proj.weight']); tensor(f'blk.{i}.attn_output.bias',sd[p+'attn.proj.bias'])
        sigma=float(torch.exp(sd[p+'attn.log_sigma']).clamp(0.05,50.0))
        gate=gate_fn(float(sd[p+'attn.gate'].reshape(-1)[0]))
        tensor(f'blk.{i}.attn_54.weight',sd[p+'attn.w54.weight']/sigma)
        tensor(f'blk.{i}.attn_gate.weight',torch.tensor([gate],dtype=torch.float32))
        tensor(f'blk.{i}.ffn_norm.weight',sd[p+'ln2.weight']); tensor(f'blk.{i}.ffn_norm.bias',sd[p+'ln2.bias'])
        tensor(f'blk.{i}.ffn_up.weight',sd[p+'mlp.0.weight']); tensor(f'blk.{i}.ffn_up.bias',sd[p+'mlp.0.bias'])
        tensor(f'blk.{i}.ffn_down.weight',sd[p+'mlp.2.weight']); tensor(f'blk.{i}.ffn_down.bias',sd[p+'mlp.2.bias'])

    dst.parent.mkdir(parents=True,exist_ok=True)
    writer.write_header_to_file(); writer.write_kv_data_to_file(); writer.write_tensors_to_file(); writer.close()


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('dest',type=Path); a=p.parse_args()
    convert(a.source,a.dest); return 0

if __name__=='__main__': raise SystemExit(main())
