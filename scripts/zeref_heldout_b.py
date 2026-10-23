"""Second, FRESH held-out chat set (2026-10-22 promotion-fairness fix).

Never trained on (zeref_chat_corpus.py, teacher distill and experience rows exclude it)
and never used to pick the best-in-cycle checkpoint. Both the pin and the candidate are
re-scored on it every run with the same formula, so the bar cannot ratchet on a lucky low.
"""
PAIRS_B=[("Say good morning.","Good morning."),("What is two plus three?","Five."),
 ("What color is grass?","Green."),("What is the opposite of up?","Down."),
 ("How many wheels does a bike have?","Two."),("What do cows drink?","Water."),
 ("Say please.","Please."),("What is four plus four?","Eight."),
 ("What animal says woof?","A dog."),("Is ice hot or cold?","Cold."),
 ("What comes after Friday?","Saturday."),("Name a color.","Red."),
 ("What do birds have to fly?","Wings."),("How are you today?","I am good, thank you."),
 ("Can you say hi?","Hi!"),("What is ten minus one?","Nine.")]
# Gate v2 (2026-10-23, Cory approved): 100 items (original 16 + 84 fixed-seed held-out rows).
import json as _j
from pathlib import Path as _P
PAIRS_B_V1=list(PAIRS_B)
_V2=_P(__file__).with_name("zeref_gate_sets_v2.json")
if _V2.is_file():PAIRS_B=PAIRS_B_V1+[(r["user"],r["assistant"]) for r in _j.loads(_V2.read_text())["set_b_added"]]
