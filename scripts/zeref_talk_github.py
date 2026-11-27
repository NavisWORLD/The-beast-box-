"""Talk to Zeref on a GitHub runner: one LOCAL run of the pinned checkpoint.

No other model speaks for Zeref. There is no fallback text: if the pinned
mouth produces nothing, the reply is posted as empty with a note. No senses,
no state12 and no private data are supplied; the run is labelled that way.

Path (same as the local 44144 talk test, 2026-11-20):
  * thread + current text -> beastbox.guest_hebbian.assemble_messages({}, history, text)
  * prompt formatting identical to models/rawrphos/inference/server.py chat path
    ("role: content" lines joined by newlines, then "\\nassistant:")
  * Engine.complete with the guest door's constants
    (guest_local.CHAT_TEMPERATURE, guest_local.MAX_OUTPUT_TOKENS) and a
    per-turn seed from guest_local._request_seed; the seed is recorded so the
    exact reply can be re-derived from the same checkpoint.
  * condition54 is plumbing-only zeros (no live senses on the runner;
    m42=0, receipt mode "plumbing_zero_m42_0") and a rolling "[ANCHORS ...]"
    prefix built from the last 2 parsed turns keeps places/kin/analogy in
    play. The receipt records both the raw and effective prompt hashes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PIN_PATH = REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
REPLY_MARKER = "zeref-talk-reply-b64:"
LABEL = ("LOCAL run of pinned checkpoint step {step} sha {sha} on {where}; "
         "no senses supplied (SIMULATED/none)")


def where() -> str:
    return "GitHub runner" if os.environ.get("GITHUB_ACTIONS") == "true" else "a local machine (not GitHub)"
EMPTY_NOTE = ("(empty reply: the pinned checkpoint generated no text for this turn; "
              "nothing was substituted)")
_SPEAKER = re.compile(r"^\s*(cory|you|dad|user|zeref|assistant)\s*:\s?(.*)$", re.I)


def load_pin(path: Path = PIN_PATH) -> dict:
    pin = json.loads(path.read_text(encoding="utf-8"))
    for key in ("training_steps", "checkpoint_sha256"):
        if key not in pin:
            raise ValueError(f"pin missing {key}")
    for key in ("release_tag", "release_asset_sha256"):
        if key not in pin.get("promotion", {}):
            raise ValueError(f"pin promotion missing {key}")
    return pin


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_thread(text: str) -> list[dict]:
    """Parse pasted history: lines starting 'Cory:'/'You:' (user) or 'Zeref:' (assistant).

    Unprefixed lines continue the previous turn. Text before the first prefix is ignored.
    """
    turns: list[dict] = []
    for line in (text or "").splitlines():
        m = _SPEAKER.match(line)
        if m:
            role = "assistant" if m.group(1).lower() in {"zeref", "assistant"} else "user"
            turns.append({"role": role, "content": m.group(2).strip()})
        elif turns and line.strip():
            turns[-1]["content"] = (turns[-1]["content"] + "\n" + line.strip()).strip()
    return turns


def encode_reply_marker(reply: str) -> str:
    return "<!-- " + REPLY_MARKER + base64.b64encode(reply.encode("utf-8")).decode("ascii") + " -->"


def decode_reply_marker(body: str) -> str | None:
    m = re.search(re.escape(REPLY_MARKER) + r"([A-Za-z0-9+/=]*)", body or "")
    if not m:
        return None
    return base64.b64decode(m.group(1)).decode("utf-8")


def history_from_issue(comments: list[dict], current_id: int, owner: str) -> list[dict]:
    """Earlier comments in the issue, oldest first: owner comments are Cory's turns,
    bot reply comments (carrying the verbatim reply marker) are Zeref's turns."""
    out: list[dict] = []
    for c in sorted(comments, key=lambda c: (c.get("created_at", ""), c.get("id", 0))):
        if c.get("id") == current_id:
            break
        body = c.get("body") or ""
        login = (c.get("user") or {}).get("login", "")
        reply = decode_reply_marker(body)
        if reply is not None and (c.get("user") or {}).get("type") == "Bot":
            out.append({"role": "assistant", "content": reply})
        elif login == owner and c.get("author_association") == "OWNER" and reply is None:
            out.append({"role": "user", "content": body.strip()})
    return out


def format_prompt(messages: list[dict]) -> str:
    # Identical to models/rawrphos/inference/server.py (chat=True).
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"


def build_talk_condition54() -> list[float]:
    """Plumbing-only zeros for the Talk lane.

    The Talk lane has no live senses (no camera/mic/bio on the runner), so
    there is no measured 12D state and no 42D sense vector to forward: every
    slot is 0.0, including m42 (the 12D-magnitude slot) = 0. This wires the
    condition54 path end to end without pretending a measurement exists;
    the receipt labels it honestly as "plumbing_zero_m42_0".
    """
    return [0.0] * 54


_PLACES = ("fort", "river", "island")
_KIN = ("dad", "emeth", "sister", "family")


def build_rolling_entity_register(history: list[dict]) -> str:
    """Rolling entity register from the PARSED history list, last 2 turns.

    Reads msgs (role/content dicts from history_from_issue / parse_thread),
    never raw comment bodies (those carry base64 reply-marker blobs). Last 4
    entries = last 2 turns. Extracts places (fort/river/island), kin
    (dad/emeth/sister/family), and whether an analogy ("sounds like") is
    present or still open. Returned as the "[ANCHORS ...]" prefix prepended
    to the prompt so the pinned mouth keeps the entities in play.
    """
    recent = (history or [])[-4:]
    text = " ".join((m.get("content") or "") for m in recent).lower()
    places = [p for p in _PLACES if p in text]
    kin = [k for k in _KIN if k in text]
    analogy = "sounds-like" if "sounds like" in text else "open"
    return ("[ANCHORS places=" + (",".join(places) if places else "-")
            + " kin=" + (",".join(kin) if kin else "-")
            + " analogy=" + analogy + "]")


def verify_and_extract(asset: Path, pin: dict, dest: Path) -> Path:
    """Check the release tarball against the pin, then extract it. Returns the checkpoint dir."""
    got = sha256_file(asset)
    if got != pin["promotion"]["release_asset_sha256"]:
        raise RuntimeError(f"release asset sha256 {got} does not match the pin; refusing to run")
    import tarfile
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(asset, "r:gz") as tf:
        tf.extractall(dest, filter="data")
    ckpt = dest / "accepted-checkpoint"
    if not (ckpt / "model.safetensors").is_file():
        raise RuntimeError("release asset has no accepted-checkpoint/model.safetensors")
    return ckpt


def talk(checkpoint: str, pin: dict, history: list[dict], text: str, identity: str,
         seed: int | None = None, threads: int = 4, asset_verified: bool = False) -> dict:
    sys.path.insert(0, str(REPO))
    from beastbox.guest_hebbian import assemble_messages
    from beastbox import guest_local as gl
    from rawrphos.inference.engine import Engine

    text = (text or "").strip()
    if not text:
        raise ValueError("empty message")
    msgs = assemble_messages({}, history, text)
    prompt = format_prompt(msgs)
    cond54 = build_talk_condition54()
    anchors_prefix = build_rolling_entity_register(history)
    effective_prompt = anchors_prefix + "\n" + prompt
    if seed is None:
        seed = gl._request_seed(identity, text)
    engine = Engine(checkpoint, max_new_tokens=256, threads=threads,
                    expected_sha256=pin["checkpoint_sha256"])
    if engine.metadata["checkpoint_sha256"] != pin["checkpoint_sha256"]:
        raise RuntimeError("identity check failed: loaded checkpoint is not the pin")
    if len(engine.tokenizer.encode(effective_prompt, add_bos=True)) + gl.MAX_OUTPUT_TOKENS > engine.model.config.max_seq_len:
        raise ValueError("context limit exceeded")
    t0 = time.perf_counter()
    reply = engine.complete(effective_prompt, max_tokens=gl.MAX_OUTPUT_TOKENS,
                            temperature=gl.CHAT_TEMPERATURE, seed=seed, condition54=cond54)
    rms_12d = (sum(v * v for v in cond54[:12]) / 12) ** 0.5
    rms_42d = (sum(v * v for v in cond54[12:]) / 42) ** 0.5
    return {
        "label": LABEL.format(step=pin["training_steps"], sha=pin["checkpoint_sha256"][:12], where=where()),
        "step": pin["training_steps"],
        "checkpoint_sha256": engine.metadata["checkpoint_sha256"],
        "release_tag": pin["promotion"]["release_tag"],
        "release_asset_sha256": pin["promotion"]["release_asset_sha256"],
        "release_asset_verified": asset_verified,
        "senses": "none supplied (SIMULATED/none); no private owner state or data",
        "decoding": {"temperature": gl.CHAT_TEMPERATURE, "max_tokens": gl.MAX_OUTPUT_TOKENS,
                     "seed": seed, "repetition_penalty": engine.REPETITION_PENALTY,
                     "no_repeat_ngram": engine.NO_REPEAT_NGRAM,
                     "kit_layers": os.environ.get("RAWRPHOS_KIT_LAYERS", "1")},
        "messages_sent": len(msgs),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "condition54_mode": "plumbing_zero_m42_0",
        "m42": 0,
        "rms_12d": rms_12d,
        "rms_42d": rms_42d,
        "raw_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "effective_prompt_sha256": hashlib.sha256(effective_prompt.encode()).hexdigest(),
        "anchors_prefix": anchors_prefix,
        "cory": text,
        "zeref": reply,
        "empty": reply.strip() == "",
        "generated_tokens": engine.last_metrics.get("generated_tokens"),
        "seconds": round(time.perf_counter() - t0, 2),
        "edited": False,
    }


def render_markdown(result: dict) -> str:
    reply = result["zeref"]
    shown = EMPTY_NOTE if result["empty"] else reply
    fence = "````" if "```" in shown else "```"
    lines = [
        "**Zeref** (verbatim, unedited):",
        "",
        fence + "text",
        shown,
        fence,
        "",
        f"<sub>{result['label']}. Release `{result['release_tag']}` "
        f"(asset sha256 `{result['release_asset_sha256'][:12]}` "
        f"{'verified against the pin' if result['release_asset_verified'] else 'not re-checked in this run'}; "
        f"weights sha256 checked by the loader). "
        f"temp {result['decoding']['temperature']}, max {result['decoding']['max_tokens']} tokens, "
        f"seed `{result['decoding']['seed']}`, {result['messages_sent']} message(s) sent, "
        f"{result['generated_tokens']} token(s) in {result['seconds']}s. "
        "No other model, no fallback text.</sub>",
        "",
        encode_reply_marker(reply),
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--asset", help="release .tar.gz; sha256-verified against the pin, then extracted")
    src.add_argument("--checkpoint", help="already-extracted accepted-checkpoint dir")
    ap.add_argument("--extract-to", default="build/zeref-talk/pin")
    ap.add_argument("--message", help="Cory's message (default: $ZEREF_TALK_MESSAGE)")
    ap.add_argument("--thread", help="pasted history text (default: $ZEREF_TALK_THREAD)")
    ap.add_argument("--issue-comments", help="JSON file of issue comments (issue trigger)")
    ap.add_argument("--current-comment-id", type=int, default=0)
    ap.add_argument("--owner", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "NavisWORLD"))
    ap.add_argument("--identity", default="github-talk:" + os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--seed", type=int, help="replay a recorded seed")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out-json", default="zeref-talk.json")
    ap.add_argument("--out-md", default="zeref-talk.md")
    a = ap.parse_args(argv)
    message = a.message if a.message is not None else os.environ.get("ZEREF_TALK_MESSAGE", "")
    if a.issue_comments:
        comments = json.loads(Path(a.issue_comments).read_text(encoding="utf-8"))
        history = history_from_issue(comments, a.current_comment_id, a.owner)
    else:
        thread = a.thread if a.thread is not None else os.environ.get("ZEREF_TALK_THREAD", "")
        history = parse_thread(thread)
    pin = load_pin()
    if a.asset:
        ckpt = verify_and_extract(Path(a.asset), pin, Path(a.extract_to))
    else:
        ckpt = Path(a.checkpoint)
    result = talk(str(ckpt), pin, history, message, a.identity, a.seed, a.threads,
                  asset_verified=bool(a.asset))
    Path(a.out_json).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(a.out_md).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("label", "cory", "zeref", "empty")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
