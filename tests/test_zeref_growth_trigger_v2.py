import json,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
import zeref_growth_trigger as t
def test_plateau_grows_without_cap_and_is_repeatable(tmp_path):
    lin=t.empty()
    for i in range(4):lin["rounds"].append({"run":str(i),"best_chat_nll":2.95+i*.001,"approved":False})
    d=t.decide(lin,40,"a"*64,None,2.88,avail=10**12)
    assert d["grow"] and d["add_layers"]==2 and d["target_layers"]==42 and d["max_layers"] is None
    d2=t.decide(lin,40,"a"*64,None,2.88,avail=10**12)  # same window: no double-fire, target kept
    assert d2["target_layers"]==42 and d2["add_layers"]==2 and d2["reasons"]==[]
def test_ram_limit_defers_not_stops():
    lin=t.empty();lin["target_layers"]=20
    d=t.decide(lin,6,"a"*64,None,2.88,avail=t.layer_bytes(256)*2*3)
    assert d["add_layers"]==3 and d["limit_hit"]["limit"]=="ram" and lin["target_layers"]==20
def test_rigetti_simulated_events_fire_and_grow_world(tmp_path):
    p=tmp_path/"e.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [
      {"kind":"diary","tick":5,"growth":"rigetti-qvm-simulated","simulated":True,"grew":True},
      {"kind":"diary","tick":6,"growth":"deterministic-fallback","simulated":False,"grew":False}]))
    lin=t.empty();d=t.decide(lin,6,"a"*64,str(p),2.88,avail=10**12)
    assert d["reasons"]==["rigetti_simulated_growth"] and d["add_layers"]==2 and lin["world_growth"]==1
    assert t.decide(lin,6,"a"*64,str(p),2.88,avail=10**12)["reasons"]==[]  # tick already consumed
def test_record_reads_report():
    lin=t.record(t.empty(),{"accepted_as_next_training_parent":False,"training_logs":[{"best_in_cycle_chat_nll":2.9}]},"7")
    assert lin["rounds"][-1]=={"run":"7","best_chat_nll":2.9,"approved":False,"limits_hit":[],"candidate":None}
