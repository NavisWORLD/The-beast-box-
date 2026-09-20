"""Numerical reference for a 42-node modeled relay and 12-scalar state."""
import json,math,sys
from pathlib import Path
def compute(p):
    v=iter(map(float,Path(p).read_text().split()))
    steps=int(next(v));offset=int(next(v))
    if steps<0 or steps>10000:raise ValueError("steps")
    w=[[next(v) for _ in range(42)] for _ in range(42)]
    drive=[next(v) for _ in range(42)]
    state=[next(v) for _ in range(42)]
    dyn=[next(v) for _ in range(12)]
    for t in range(steps):
        state=[math.tanh(.61*state[i]+2.15*sum(w[i][j]*state[j] for j in range(42))+drive[i]) for i in range(42)]
        avg=[sum(state[i::12])/len(state[i::12]) for i in range(12)]
        dyn=[math.tanh(.86*dyn[i]+.14*avg[i]+.015*math.sin((offset+t+1)*(i+1)*.17320508075688773)) for i in range(12)]
    return {"state":state,"dyn12":dyn}
if __name__=="__main__":print(json.dumps(compute(sys.argv[1])))
