#!/usr/bin/env python3
"""Real Ollama conversation measurement. No fixture or inference fallback."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

from beastbox import __version__
from beastbox.durable import DurableRuntime
from beastbox.providers import LocalOllamaProvider, _assert_loopback, _local_opener
from beastbox.portable_state import export_snapshot, import_snapshot


def api(url, path, body=None):
    _assert_loopback(url)
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with _local_opener().open(req, timeout=180) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("backend metadata too large")
    return json.loads(raw)


def child():
    request = json.load(sys.stdin)
    runtime = DurableRuntime(request["state"], LocalOllamaProvider(model=request["model"], base_url=request["url"]))
    try:
        before = runtime.inspect()
        result = runtime.respond(request["text"])
        return {
            "pid": os.getpid(),
            "before": before,
            "after": runtime.inspect(),
            "result": result,
            "authority": sorted(runtime.policy.allowed),
            "package_version": __version__,
        }
    finally:
        runtime.close()


def measure(args):
    if args.output.exists():
        raise ValueError("demo requires a new output directory; preserve earlier runs")
    args.output.mkdir(parents=True)
    turns = []
    report = {
        "schema": "beastbox-story-demo-v1",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "fixture": False,
        "historical_experiment_002": False,
        "turns": turns,
        "memory_delivery": "NOT_RUN",
        "interpretation": "NOT_RUN",
        "passed": False,
    }
    try:
        tags = api(args.url, "/api/tags")["models"]
        models = {name: next(x for x in tags if x["name"] == name) for name in (args.model_a, args.model_b)}
        if models[args.model_a]["digest"] == models[args.model_b]["digest"]:
            raise ValueError("two distinct real model manifests are required")
        report["models_before"] = models
        report["server_version"] = api(args.url, "/api/version")
        report["show_metadata"] = {m: api(args.url, "/api/show", {"model": m}) for m in models}
        schedule = [
            (args.model_a, "Remember that the code word for this test is SUNFLOWER."),
            (args.model_a, "What is the code word for this test? Reply with the exact word."),
            (args.model_b, "I changed models. What code word did the previous model receive?"),
            (args.model_b, "Also remember that the launch color is AMBER."),
            (args.model_a, "What are the code word and launch color? Reply with both exact values."),
        ]
        state = args.output / "machine-a"
        for index, (model, text) in enumerate(schedule):
            # Explicitly unload before inference, so model backend state is recreated.
            api(args.url, "/api/generate", {"model": model, "keep_alive": 0})
            if index == 4:
                exported = export_snapshot(state, args.output / "portable")
                state = args.output / "machine-b"
                report["portable"] = import_snapshot(args.output / "portable", state, exported["manifest_sha256"])
            request = {"state": str(state.resolve()), "model": model, "text": text, "url": args.url}
            proc = subprocess.run(
                [sys.executable, "-I", str(Path(__file__).resolve()), "--child"],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=240,
            )
            if proc.returncode:
                raise RuntimeError(f"inference child {index + 1} failed: {proc.stderr[-1000:]}")
            turn = json.loads(proc.stdout)
            turn["user_input"] = text
            turn["backend_unloaded_before_inference"] = True
            if turns and turn["before"] != turns[-1]["after"]:
                raise RuntimeError("restart or provider swap changed the substrate")
            if turn["authority"] or not turn["after"]["valid"]:
                raise RuntimeError("authority or integrity failure")
            turns.append(turn)
            (args.output / f"turn-{index + 1}.json").write_text(json.dumps(turn, indent=2) + "\n")
        prompts = [t["result"]["model"]["prompt"] for t in turns]
        delivered = all("SUNFLOWER" in prompts[i] for i in (1, 2, 4)) and "AMBER" in prompts[4]
        # These exact token checks measure only fact emission, not natural conversation quality.
        outputs = [t["result"]["response"] for t in turns]
        interpreted = all("SUNFLOWER" in outputs[i].upper() for i in (1, 2, 4)) and "AMBER" in outputs[4].upper()
        report["memory_delivery"] = "PASS" if delivered else "FAIL"
        report["interpretation"] = "EXACT_FACTS_EMITTED" if interpreted else "EXACT_FACTS_NOT_ALL_EMITTED"
        after = {x["name"]: x for x in api(args.url, "/api/tags")["models"] if x["name"] in models}
        report["models_after"] = after
        if any(after[name]["digest"] != models[name]["digest"] for name in models):
            raise RuntimeError("model manifest changed during demo")
        report["process_ids_distinct"] = len({t["pid"] for t in turns}) == 5
        report["passed"] = delivered and report["process_ids_distinct"]
        report["classification"] = "REAL_MODEL_SUBSTRATE_DELIVERY_MEASURED" if report["passed"] else "FAILED"
        report["limitations"] = [
            "Same host, separate processes/directories; no physical USB claim",
            "Manifest identity is not loaded-parameter attestation",
            "Exact fact emission is separate from memory delivery and conversational quality",
        ]
    except Exception as exc:
        report["classification"] = "BLOCKED_OR_FAILED"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        path = args.output / "story-receipt.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
        files = [p for p in args.output.glob("*.json")]
        (args.output / "SHA256SUMS").write_text(
            "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(files))
        )
        print(
            json.dumps({key: report[key] for key in ("passed", "classification", "memory_delivery", "interpretation")})
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if "--child" in sys.argv:
        print(json.dumps(child()))
    else:
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("--model-a", required=True)
        p.add_argument("--model-b", required=True)
        p.add_argument("--url", default="http://127.0.0.1:11434")
        p.add_argument("--output", type=Path, required=True)
        raise SystemExit(measure(p.parse_args()))
