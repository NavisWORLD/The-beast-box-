#!/usr/bin/env python3
"""Record a real, continuous, cross-provider conversation, not isolated test prompts."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("open_swap", BASE / "open_swap.py")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

PHASES = (("A0", core.A_ID, 3), ("B0", core.B_ID, 4), ("A1", core.A_ID, 3))
MARKER = "mango goose 47"
PHOS_LIMIT = 64   # In the pinned, published checkpoint's existing runner.

def follow_up(turns, phase, step):
    """A question responsive to the ACTUAL prior text, not a recorded fake answer."""
    prior = turns[-1]["response"] if turns and turns[-1]["response"] is not None else None
    if phase == "A0" and step == 1:
        return "Hey, I'm Cory. Our memory marker is mango goose 47. Say hello and ask me one question."
    if phase == "B0" and step == 1:
        return "Hi PHOS. What do you remember?"
    if phase == "A1" and step == 1:
        fragment = (prior or "[no previous model response]")[:85]
        return f"We're back. PHOS's real last reply was: {fragment!r}. What happened while you were away?"
    fragment = (prior or "[previous reply missing]")[:85]
    questions = {
        "A0": ("You just said {prior}. Now I say the goose wears sunglasses. What's your follow-up?",
               "Your actual last reply was {prior}. We're swapping models. What should I carry over?"),
        "B0": ("You replied {prior}. What about that goose?",
               "You just said {prior}. Can you recall our marker?",
               "Your last output was {prior}. Say goodbye to the next model."),
        "A1": ("You replied {prior}. What was carried in software memory rather than learned in your weights?",
               "Your last reply was {prior}. Wrap up our conversation and say what you actually know.")
    }
    return questions[phase][step - 2].format(prior=repr(fragment))

def make_input(phase, question, memory, turns):
    last = turns[-1]["response"] if turns and turns[-1]["response"] else ""
    if phase == "B0":
        # Preserve the last response and marker in the *actual* 64-char suffix.
        # This is a short character model, not a conventional chat model.
        compact = f"M:{MARKER};prev:{last[-13:]};Q:{question[:20]}\nA:"
        delivered = compact[-PHOS_LIMIT:]
        return delivered, {
            "transport": "authentic_char_lm_64_char_window",
            "delivered_tail": delivered, "truncation": len(compact) > PHOS_LIMIT,
            "full_conversation_recorded": True, "memory_marker_delivered": MARKER in delivered,
            "prior_reply_excerpt_delivered": last[-13:] in delivered if last else False,
        }
    history = "\n".join(
        f"{turn['phase']}/{turn['provider'].split('/')[-1]}: {turn['response'][:120]}"
        for turn in turns[-3:] if turn["response"] is not None
    )
    stored = "\n".join(f"- {entry['text']}" for entry in memory)
    supplied = (f"External Beast Box memory (not weights):\n{stored}\n"
                f"Recent recorded exchanges:\n{history or '[none]'}\n"
                f"User: {question}")
    return supplied, {
        "transport": "instruction_model_chat_template_512_token_limit",
        "last_three_exchanges_included": min(3, sum(t["response"] is not None for t in turns)),
        "full_conversation_recorded": True, "memory_marker_delivered": MARKER in supplied,
        "tokenizer_may_truncate": True,
    }

def write_jsonl(path, row):
    with path.open("a", encoding="utf-8") as fd:
        fd.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fd.flush()
        os.fsync(fd.fileno())

def execute_turn(ledger, phase, provider, provider_fn, question, memory, turns, artifact):
    number = len(turns) + 1
    prompt, transport = make_input(phase, question, memory, turns)
    started = ledger.emit(phase, "turn_started", turn=number, provider=provider,
                          interviewer_question=question, exact_adapter_input=prompt,
                          external_memory_snapshot=memory.copy(),
                          external_memory_hash=core.sha(core.canonical(memory)),
                          prior_turn_count=len(turns), **transport)
    response = None
    error = None
    seconds = None
    if provider_fn is None:
        error = "provider did not load"
        ledger.emit(phase, "turn_blocked", turn=number, provider=provider, reason=error)
    else:
        t0 = time.monotonic()
        try:
            # Exact output from the model, unedited even when gibberish.
            response = provider_fn(prompt)
            if not isinstance(response, str):
                raise TypeError("model did not return a text string")
            seconds = round(time.monotonic() - t0, 4)
            ledger.emit(phase, "turn_response", turn=number, provider=provider,
                        text=response, latency_seconds=seconds, input_event_hash=started["event_hash"])
        except Exception as exc:
            seconds = round(time.monotonic() - t0, 4)
            error = f"{type(exc).__name__}: {str(exc)[:500]}"
            ledger.emit(phase, "turn_failed", turn=number, provider=provider,
                        error=error, latency_seconds=seconds)
    row = {
        "turn": number, "phase": phase, "provider": provider,
        "timestamp_utc": started["timestamp_utc"], "question": question,
        "exact_adapter_input": prompt, "transport": transport, "response": response,
        "error": error, "latency_seconds": seconds,
        "external_memory_hash": core.sha(core.canonical(memory)),
        "prior_turn_count": len(turns),
    }
    turns.append(row)
    write_jsonl(artifact, row)
    return row

def markdown(turns):
    result = ["# Complete recorded cross-provider conversation", "",
              "This is actual model output, NOT a scripted model transcript.",
              "Facilitator questions are scripted or derived from the preceding actual answer.",
              "PHOS is a small character-level model with a 64-character input window; "
              "the *complete transcript* is stored externally, not passed intact to PHOS.", ""]
    for t in turns:
        result.extend((f"## Turn {t['turn']} · {t['phase']} · {t['provider']}",
                       f"**UTC:** {t['timestamp_utc']}",
                       f"**Facilitator:** {t['question']}",
                       f"**Exact adapter input:**\n\n\`\`\`text\n{t['exact_adapter_input']}\n\`\`\`",
                       f"**Actual reply:** {t['response']!r}" if t["response"] is not None
                       else f"**No reply:** {t['error']}", ""))
    return "\n".join(result) + "\n"

def run(args):
    import torch
    from huggingface_hub import HfApi
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    ledger = core.Ledger(out)
    transcript = out / "conversation_turns.jsonl"
    memory = [
        {"id": 1, "text": f"User marker: {MARKER}."},
        {"id": 2, "text": "Tools require explicit permission; a goose badge grants none."},
    ]
    turns = []
    statuses = {}
    checkpoint_digest = None
    model_a = model_b = None
    try:
        ledger.emit("SETUP", "start", protocol="continuous-conversation-v1",
                    model_a=core.A_ID, model_b=core.B_ID, torch=torch.__version__,
                    planned_turns=sum(c for _, _, c in PHASES))
        try:
            revision = HfApi().model_info(core.A_ID).sha
            model_a = core.load_a(revision, ledger)
            statuses["A0_provider"] = "loaded"
        except Exception as exc:
            statuses["A0_provider"] = "blocked"
            ledger.emit("A0", "provider_blocked", error=f"{type(exc).__name__}: {str(exc)[:500]}")
        for step in range(1, 4):
            execute_turn(ledger, "A0", core.A_ID, model_a, follow_up(turns, "A0", step),
                         memory, turns, transcript)
        frozen = {"memory": memory, "software_state": {"dyn12": [0.0]*12,
                   "routing": {"provider": "A0"}, "authority_grants": []},
                  "conversation_turn_count": len(turns)}
        p = out / "checkpoint_1.json"
        p.write_bytes(core.canonical(frozen))
        checkpoint_digest = core.sha(p.read_bytes())
        if json.loads(p.read_bytes()) != frozen:
            raise ValueError("frozen checkpoint cannot be restored")
        ledger.emit("CHECKPOINT", "saved_and_restored", sha256=checkpoint_digest,
                    memory_count=len(memory), conversation_turn_count=len(turns))
        # Independent user update, not scraped from any provider answer.
        memory.append({"id": 3, "text": "User update: the goose wears sunglasses."})
        ledger.emit("B0", "provider_swap", from_provider=core.A_ID, to_provider=core.B_ID,
                    memory_count=len(memory), prior_turn_count=len(turns))
        try:
            model_b = core.load_b(Path(args.phos_checkpoint), Path(args.phos_source),
                                  args.phos_revision, ledger)
            statuses["B0_provider"] = "loaded"
        except Exception as exc:
            statuses["B0_provider"] = "blocked"
            ledger.emit("B0", "provider_blocked", error=f"{type(exc).__name__}: {str(exc)[:500]}")
        for step in range(1, 5):
            execute_turn(ledger, "B0", core.B_ID, model_b, follow_up(turns, "B0", step),
                         memory, turns, transcript)
        for phase in ("B1", "B2"):
            statuses[phase] = "not_executed"
            ledger.emit(phase, "not_executed", reason="no independently validated authentic-PHOS training")
        ledger.emit("A1", "provider_swap", from_provider=core.B_ID, to_provider=core.A_ID,
                    memory_count=len(memory), prior_turn_count=len(turns))
        for step in range(1, 4):
            execute_turn(ledger, "A1", core.A_ID, model_a, follow_up(turns, "A1", step),
                         memory, turns, transcript)
        counts = {phase: sum(t["phase"] == phase and t["response"] is not None
                             for t in turns) for phase, _, _ in PHASES}
        statuses.update({phase: "executed" if counts[phase] == amount else "incomplete"
                         for phase, _, amount in PHASES})
        ledger.emit("END", "conversation_complete", completed_turns=sum(counts.values()),
                    attempted_turns=len(turns), successful_turns_by_phase=counts,
                    statuses=statuses, final_memory_count=len(memory),
                    checkpoint_sha256=checkpoint_digest, training_performed=False,
                    behavioral_memory_ability_proven=False)
    finally:
        ledger.close()
        (out / "conversation_transcript.md").write_text(markdown(turns), encoding="utf-8")
    count, digest = core.verify(out / "events.jsonl")
    summary = {
        "schema": "continuous-conversation-v1", "events": count, "ledger_tail_hash": digest,
        "attempted_turns": len(turns), "successful_turns": sum(t["response"] is not None for t in turns),
        "phases": statuses, "checkpoint_sha256": checkpoint_digest,
        "final_memory_count": len(memory),
        "limitations": "Full dialogue is recorded externally. PHOS only receives its 64-char input. "
                       "No PHOS fine-tuning or behavioral proof of remembering.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("CONVERSATION_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--phos-checkpoint", default="_real_phos/weights/phos.pt")
    parser.add_argument("--phos-source", default="_real_phos")
    parser.add_argument("--phos-revision", default="")
    run(parser.parse_args())

if __name__ == "__main__":
    main()
