"""Pure trusted-task router and observation guard for experimental Zeref research.

Routing is *not* selected by visitor prompt contents, memory, identity inference,
or quantum features. Only an authorized application task tag may select a model.
"""
from __future__ import annotations

ROLE_BRANCH={"pocket":"game","native":"game","dialogue":"language"}
ACTIONS=("UP","DOWN","LEFT","RIGHT","WAIT")
MOVES=ACTIONS[:4]

def route(task):
    if type(task) is not str or task not in ROLE_BRANCH:
        raise ValueError("Explicit trusted task type required")
    return ROLE_BRANCH[task]

def _parse(text):
    raw=(text if isinstance(text,str) else "").strip()
    return raw[len("ACTION: "):] if raw.startswith("ACTION: ") and raw[len("ACTION: "):] in ACTIONS else None

def guarded_choice(text,observation):
    """Observation-only guard, NOT evidence of neural blocked-move learning."""
    key=_parse(text)
    neighbors=observation.get("neighbors",{})
    if key=="WAIT":return "WAIT","model_wait"
    if key in neighbors and neighbors[key].get("kind")=="open":
        return key,"model_safe"
    open_moves=[k for k in MOVES if neighbors.get(k,{}).get("kind")=="open"]
    if not open_moves:return "WAIT","no_open_neighbor"
    frontier=observation.get("frontier")
    if frontier in open_moves:return frontier,"guard_frontier"
    return min(open_moves,key=lambda k:(neighbors[k].get("visits",999),k)),"guard_unvisited_first"
