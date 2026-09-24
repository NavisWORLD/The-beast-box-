"""CPU-only architecture/resource probe for an UNTRAINED RAWRPHOS 10M candidate.

Does not load, change, replace, or rebrand the existing native 3.91M model.
Synthetic tokens and optimizer updates here are solely a hardware test.
"""
import argparse
import json
import math
import resource
import time

import torch

from rawrphos.architecture.model import RawrphosConfig, RawrphosLM

MODEL_ID = "rawrphos-native-10m-research"
EXPECTED_PARAMETERS = 10138540


def probe(threads=2, seq_len=64, batch_size=2):
    if type(threads) is not int or not 1 <= threads <= 4:
        raise ValueError("CPU-only probe requires 1..4 threads")
    if type(seq_len) is not int or not 1 <= seq_len <= 128:
        raise ValueError("synthetic sequence must be 1..128")
    if type(batch_size) is not int or not 1 <= batch_size <= 2:
        raise ValueError("synthetic batch must be 1..2")
    torch.set_num_threads(threads)
    torch.manual_seed(67)
    config = RawrphosConfig(vocab_size=4096,d_model=384,n_heads=6,n_layers=8,
                            max_seq_len=2048,state_dim=12,attention_mode="dyn12")
    started=time.perf_counter()
    model=RawrphosLM(config).cpu().train()
    count=model.parameter_count()
    assert count == EXPECTED_PARAMETERS, "architecture unexpectedly changed"
    optimizer=torch.optim.AdamW(model.parameters(),lr=0.00008)
    x=torch.randint(0,config.vocab_size,(batch_size,seq_len),dtype=torch.long)
    target=torch.randint(0,config.vocab_size,(batch_size,seq_len),dtype=torch.long)
    optimizer.zero_grad(set_to_none=True)
    result=model(x,targets=target)
    assert bool(torch.isfinite(result["loss"])), "nonfinite synthetic loss"
    result["loss"].backward()
    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
    optimizer.step()
    assert math.isfinite(float(norm))
    assert all(bool(torch.isfinite(param).all()) for param in model.parameters())
    return {
        "schema":"rawrphos-untrained-architecture-probe-v1",
        "model_id":MODEL_ID,"configuration":config.to_dict(),
        "parameters":count,"synthetic_optimizer_steps":1,
        "trained_language_checkpoint":False,"weights_published":False,
        "transplanted_from_3_91m":False,
        "synthetic_batch_size":batch_size,"synthetic_seq_len":seq_len,
        "cpu_threads":threads,
        "wall_seconds":time.perf_counter()-started,
        "peak_process_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations":["Synthetic random-token CPU fixture; not measured real-corpus training throughput.",
                       "Not a trained model and not a quality benchmark.",
                       "A larger model changes tensor shapes; old optimizer and weights cannot be silently resumed.",
                       "Future training needs separate owner authorization, provenance and GPU/CPU cost limits."],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--threads",type=int,default=2)
    parser.add_argument("--seq-len",type=int,default=64)
    parser.add_argument("--batch-size",type=int,default=2)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    report=probe(args.threads,args.seq_len,args.batch_size)
    import pathlib
    dest=pathlib.Path(args.output)
    if dest.exists(): raise FileExistsError("refuse to overwrite resource probe")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
