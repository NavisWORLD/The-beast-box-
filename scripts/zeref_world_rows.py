#!/usr/bin/env python3
"""World rows for the GROWING branch only (Cory 2026-10-31: learn from his whole world, not just chat).

Turns one public read of www.beastboxcosmos.xyz /api/world/live + /api/zeref/diary (saved by the growing workflow)
into short labelled Q&A rows. Labels: diary = RECORDED, mood/signals/Rigetti = SIMULATED, birth spark = RECORDED IBM.
A missing or malformed feed is ABSENT: it yields no row (never a filler value). No heartbeat values, no audio,
and never whose heartbeat seeded him. Pure and deterministic.
"""
from __future__ import annotations
import json, re
from pathlib import Path
SOURCE = "https://www.beastboxcosmos.xyz/api/zeref/diary"
LICENSE = "Beast Box world record (owner's own, same as repository)"
WORD = re.compile(r"^[A-Za-z][A-Za-z ' -]{0,30}$")

def _w(v): return v if isinstance(v, str) and WORD.match(v) else None
def _n(v): return round(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

def world_rows(snap: dict | None) -> list[dict]:
    if not isinstance(snap, dict): return []
    live, diary = snap.get("live") or {}, snap.get("diary") or {}
    out = []
    def add(q, a, src=SOURCE): out.append({"user": q, "assistant": a, "source": src, "license": LICENSE})
    recent = diary.get("recent") if isinstance(diary.get("recent"), list) else []
    for e in sorted((e for e in recent if isinstance(e, dict) and _n(e.get("tick")) is not None), key=lambda e: -e["tick"])[:6]:
        if not isinstance(e, dict): continue
        place, mood, tick = _w(e.get("place")), _w(e.get("mood")), _n(e.get("tick"))
        if place and tick is not None:
            add(f"Where were you at diary tick {tick}?", f"At tick {tick} my diary (RECORDED) has me at {place}.")
        if mood and tick is not None:
            add(f"What was your simulated mood at tick {tick}?", f"My simulated mood was {mood}. It comes from my SIMULATED signals, not a real feeling.")
    st, sn = _w(diary.get("stage_name")), _w((diary.get("next_stage") or {}).get("name"))
    if st: add("What stage are you now?", f"I'm {st} right now." + (f" Next I grow into {sn}." if sn else ""))
    L = diary.get("learning") or {}
    fav, cv, ct = _w(L.get("favorite_spot")), _n(L.get("cells_visited")), _n(L.get("cells_total"))
    if fav: add("What's your favorite spot in your world?", f"{fav} is my favorite spot.")
    if cv is not None and ct: add("How much of your world have you explored?", f"I've visited {cv} of {ct} places in my world.")
    places = diary.get("places") if isinstance(diary.get("places"), dict) else {}
    names = [p for p in sorted(places) if _w(p)]
    if names: add("Name the places in your world.", "My world has " + ", ".join(names) + ".")
    b = diary.get("birth_spark") or {}
    if _w(b.get("backend") or "") or b.get("provider"):
        add("Where did your first spark come from?", "My birth spark is RECORDED from IBM quantum hardware, kept and never re-run.")
    sig = ((live.get("links") or {}).get("liveTick") or {})
    s = sig.get("signals") if sig.get("state") == "CONNECTED" else None
    if isinstance(s, dict) and _n(s.get("energy")) is not None:
        add("How are your signals right now?", f"My SIMULATED signals: energy {_n(s.get('energy'))}, signal {_n(s.get('signal'))}, resonance {_n(s.get('resonance'))}.",
            "https://www.beastboxcosmos.xyz/api/world/live")
    sp = ((live.get("links") or {}).get("spark") or {})
    if sp.get("state") == "CONNECTED" and _n(sp.get("tick")) is not None:
        add("What is your Rigetti loop doing?", f"It is SIMULATED on rigetti.sim.qvm, not a real quantum chip. It was at tick {_n(sp.get('tick'))}.",
            "https://www.beastboxcosmos.xyz/api/world/live")
    return out

def load(path) -> list[dict]:
    p = Path(path) if path else None
    if not p or not p.is_file(): return []
    try: return world_rows(json.loads(p.read_text()))
    except (ValueError, OSError): return []
