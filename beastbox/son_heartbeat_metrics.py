from __future__ import annotations
import math

def normalize_counts(counts: dict[str,int], shots: int=4096) -> dict[str,float]:
    total=sum(int(v) for v in counts.values())
    if total != shots: raise ValueError(f'expected {shots} shots, got {total}')
    return {format(i,'05b'):int(counts.get(format(i,'05b'),0))/shots for i in range(32)}

def _keys(p,q): return sorted(set(p)|set(q))
def tvd(p: dict[str,float],q: dict[str,float]) -> float: return 0.5*sum(abs(float(p.get(k,0))-float(q.get(k,0))) for k in _keys(p,q))
def _kl(p,m):
    s=0.0
    for k,v in p.items():
        v=float(v); mv=float(m.get(k,0))
        if v>0: s += v*math.log2(v/mv)
    return s
def jsd_bits(p: dict[str,float],q: dict[str,float]) -> float:
    keys=_keys(p,q); m={k:0.5*(float(p.get(k,0))+float(q.get(k,0))) for k in keys}
    pp={k:float(p.get(k,0)) for k in keys}; qq={k:float(q.get(k,0)) for k in keys}
    return 0.5*_kl(pp,m)+0.5*_kl(qq,m)
def pairwise_matrix(distributions: dict[str,dict[str,float]]) -> dict:
    names=list(distributions)
    return {
      'tvd':{a:{b:tvd(distributions[a],distributions[b]) for b in names} for a in names},
      'jsd_bits':{a:{b:jsd_bits(distributions[a],distributions[b]) for b in names} for a in names},
    }

def simulate_gate_program(program: dict) -> dict[str,float]:
    import cmath
    import numpy as np
    state=np.zeros(32,dtype=np.complex128); state[0]=1.0
    def one_qubit(mat,q):
        nonlocal state
        out=state.copy(); bit=1<<q
        for base in range(32):
            if base & bit: continue
            j=base|bit; a=state[base]; b=state[j]
            out[base]=mat[0,0]*a+mat[0,1]*b
            out[j]=mat[1,0]*a+mat[1,1]*b
        state=out
    for op in program.get('operations',[]):
        gate=op['gate']
        if gate in {'rx','ry','rz'}:
            t=float(op['angle']); c=math.cos(t/2); s=math.sin(t/2)
            if gate=='rx': mat=np.array([[c,-1j*s],[-1j*s,c]],complex)
            elif gate=='ry': mat=np.array([[c,-s],[s,c]],complex)
            else: mat=np.array([[cmath.exp(-0.5j*t),0],[0,cmath.exp(0.5j*t)]],complex)
            one_qubit(mat,int(op['qubit']))
        elif gate=='cx':
            ctrl=1<<int(op['control']); targ=1<<int(op['target']); out=state.copy()
            for i in range(32):
                if i & ctrl:
                    j=i^targ
                    out[j]=state[i]
            state=out
        else: raise ValueError(gate)
    probs=np.abs(state)**2
    probs=probs/probs.sum()
    return {format(i,'05b'):float(probs[i]) for i in range(32)}
