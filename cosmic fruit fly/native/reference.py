"""Pure Python numerical parity reference; no animal-physiology claims."""
from __future__ import annotations
import json,math,sys
from pathlib import Path

def compute(path:Path):
    tokens=iter(map(float,path.read_text().split()))
    steps=int(next(tokens));offset=int(next(tokens));
    if steps<0 or steps>10000:raise ValueError("invalid step count")
    w=[[next(tokens) for _ in range(42)] for _ in range(42)]
    stimulus=[next(tokens) for _ in range(42)]
    state=[next(tokens) for _ in range(42)]
    dyn=[next(tokens) for _ in range(12)]
    for tick in range(steps):
        state=[math.tanh(.61*state[i]+2.15*sum(w[i][j]*state[j] for j in range(42))+stimulus[i]) for i in range(42)]
        drive=[sum(state[i::12])/len(state[i::12]) for i in range(12)]
        dyn=[math.tanh(.86*dyn[i]+.14*drive[i]+.015*math.sin((offset+tick+1)*(i+1)*0.17320508075688773)) for i in range(12)]
    return {"state":state,"dyn12":dyn}

if __name__=='__main__':print(json.dumps(compute(Path(sys.argv[1])),separators=(',',':')))
