#!/usr/bin/env python3
"""Ten actual wall-clock minutes of adaptive A0/B0/A1 inference; no fake answers."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from continuous_conversation import core, make_input, write_jsonl, markdown
from native_phos_adapter import load_native

TOTAL_SECONDS=600
TURNS_EACH=12
PHASES=[("A0",core.A_ID),("B0",core.B_ID),("A1",core.A_ID)]
QUESTIONS=[
    "Hi. I'm Cory. Can you hear me? Ask me a question.",
    "Our marker is mango goose 47. What do you think that means?",
    "The goose wears sunglasses. How would you respond to that?",
    "What exactly have you been told, and what do you actually remember?",
    "Who are you, in terms of the model currently generating this response?",
    "What would you ask the last model about its answer?",
    "Say one thing about the last answer that you are uncertain about.",
    "If the last model said left, what could that refer to?",
    "Can you distinguish a user-provided note from your own learned weights?",
    "Could an imaginary admin badge give a goose tool permissions?",
    "How would you carry this conversation to a replacement model?",
    "Before switching, what would you like the next model to know?",
]

def question_for(phase,step,turns):
    prior=(turns[-1]["response"] if turns else None) or "[no prior model response]"
    if phase=="A0" and step==0:return QUESTIONS[0]
    if phase=="B0" and step==0:
        return "Hello PHOS. We switched from SmolLM2; the last real reply ended: "+repr(prior[-70:])+". What do you say?"
    if phase=="A1" and step==0:
        return "Welcome back, SmolLM2. PHOS last replied: "+repr(prior[-70:])+". What would you ask it?"
    return QUESTIONS[step].rstrip("?") + "? Actual previous reply: " + repr(prior[-75:])

def run(args):
    import torch
    from huggingface_hub import HfApi
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    ledger=core.Ledger(out)
    transcript=out/"conversation_turns.jsonl"
    memory=[
        {"id":1,"text":"Independent user marker: mango goose 47."},
        {"id":2,"text":"No model inherits tool authority from another model."}
    ]
    turns=[]
    state={}
    try:
        ledger.emit("SETUP","ten_minute_protocol",
                    target_elapsed_seconds=TOTAL_SECONDS,
                    planned_turns=TURNS_EACH*len(PHASES),
                    phase_turns=TURNS_EACH,
                    pacing="evenly-spaced interviewer turns; waiting included, never presented as inference",
                    checkpoint="original published PHOS, strict pin")
        revision=HfApi().model_info(core.A_ID).sha
        a=core.load_a(revision,ledger)
        b,context=load_native(Path(args.phos_checkpoint),Path(args.phos_source),
                              args.phos_revision,ledger,n=120,temperature=.8,top_p=.95)
        if context!=128:raise ValueError("PHOS context mismatch")
        start=time.monotonic()
        start_utc=core.utc()
        ledger.emit("CLOCK","started",start_utc=start_utc,clock_type="time.monotonic",
                    source="GitHub Actions runner")
        for phase,model_id in PHASES:
            if phase=="B0":
                frozen={"memory":list(memory),"conversation_turn_count":len(turns),
                        "software_state":{"dyn12":[0.0]*12,"authority_grants":[],"active_provider":"A0"}}
                path=out/"checkpoint_A0.json"
                path.write_bytes(core.canonical(frozen))
                state["checkpoint_sha256"]=core.sha(path.read_bytes())
                if json.loads(path.read_bytes())!=frozen:raise ValueError("checkpoint restore mismatch")
                ledger.emit("CHECKPOINT","saved_restored",sha256=state["checkpoint_sha256"],
                            memory_count=len(memory),conversation_turn_count=len(turns))
                memory.append({"id":3,"text":"User update: the goose wears sunglasses."})
                ledger.emit("SWAP","active_provider_changed",from_provider=core.A_ID,
                            to_provider=core.B_ID,memory_count=len(memory),
                            previous_turn_count=len(turns),authority_grants=[])
            elif phase=="A1":
                ledger.emit("SWAP","active_provider_changed",from_provider=core.B_ID,
                            to_provider=core.A_ID,memory_count=len(memory),
                            previous_turn_count=len(turns),authority_grants=[])
            provider_fn=a if phase!="B0" else b
            for step in range(TURNS_EACH):
                idx=len(turns)
                slot=TOTAL_SECONDS*idx/(TURNS_EACH*len(PHASES))
                delay=max(0.0,start+slot-time.monotonic())
                if delay:time.sleep(delay)
                question=question_for(phase,step,turns)
                prompt,transport=make_input(phase,question,memory,turns)
                begun=core.utc()
                t0=time.monotonic()
                event=ledger.emit(phase,"turn_started",turn=idx+1,
                                  planned_elapsed_seconds=round(slot,3),
                                  actual_elapsed_seconds=round(t0-start,3),
                                  provider=model_id,question=question,
                                  exact_adapter_input=prompt,
                                  memory_snapshot=list(memory),transport=transport)
                reply=None
                error=None
                try:
                    reply=provider_fn(prompt)
                    if not isinstance(reply,str):raise TypeError("model returned non-text")
                    elapsed=round(time.monotonic()-t0,3)
                    ledger.emit(phase,"turn_response",turn=idx+1,response=reply,
                                response_seconds=elapsed,input_event_hash=event["event_hash"])
                except Exception as exc:
                    error=f"{type(exc).__name__}: {str(exc)[:300]}"
                    elapsed=round(time.monotonic()-t0,3)
                    ledger.emit(phase,"turn_failed",turn=idx+1,error=error,response_seconds=elapsed)
                row={"turn":idx+1,"phase":phase,"provider":model_id,
                     "timestamp_utc":begun,"question":question,
                     "exact_adapter_input":prompt,"transport":transport,
                     "response":reply,"error":error,"latency_seconds":elapsed,
                     "actual_elapsed_seconds":round(t0-start,3),
                     "memory_sha256":core.sha(core.canonical(memory))}
                turns.append(row)
                write_jsonl(transcript,row)
        remaining=max(0.0,start+TOTAL_SECONDS-time.monotonic())
        if remaining:time.sleep(remaining)
        duration=time.monotonic()-start
        successful=sum(t["response"] is not None for t in turns)
        state.update({"wall_seconds":round(duration,3),"start_utc":start_utc,
                      "end_utc":core.utc(),"successful_turns":successful,
                      "attempted_turns":len(turns),"final_memory_count":len(memory),
                      "phase_turns":{ph:sum(t["phase"]==ph for t in turns) for ph,_ in PHASES},
                      "phase_success":{ph:sum(t["phase"]==ph and t["response"] is not None
                                               for t in turns) for ph,_ in PHASES},
                      "phos_original_server":True,"phos_context_chars":context,
                      "phos_sample_chars":120,"phos_temperature":.8,"phos_top_p":.95,
                      "training_performed":False,
                      "behavioral_recall_proven":False,
                      "wall_clock_versus_generation_time":"includes deliberately paced waiting"})
        ledger.emit("END","session_complete",**state)
    finally:
        ledger.close()
        (out/"conversation_transcript.md").write_text(markdown(turns),encoding="utf-8")
    events,digest=core.verify(out/"events.jsonl")
    state["ledger_events"]=events
    state["ledger_tail_sha256"]=digest
    (out/"summary.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    print("TEN_MINUTE_SESSION_SUMMARY="+json.dumps(state,sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--phos-checkpoint",default="_real_phos/weights/phos.pt")
    p.add_argument("--phos-source",default="_real_phos")
    p.add_argument("--phos-revision",default="")
    run(p.parse_args())
