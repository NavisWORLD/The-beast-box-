#!/usr/bin/env python3
"""Capture the REAL Beast Box browser talking to pinned originals on one fresh substrate.

No owner memory, no paid API, no canned responses. Every claimed reply is
obtained from the real original-checkpoint model HTTP service and displayed in
the actual COSMIC browser. All failures and limitations remain in the receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

MODEL_KEY = "synthetic-demo-local-only-" + "x" * 42
BASE = "http://127.0.0.1:8081"
EXPECTED = {
    "RAWRPHOS 14K": "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5",
    "RAWRPHOS 18K": "20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e",
    "PHOS": "bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d",
    "SAMGO": "871c265c062430c77d5528ee5fb9119f7d86668ebd81cfa4951db6a906a92b5a",
}
MODELS = [
    ("RAWRPHOS 14K", "rawrphos-native", "http://127.0.0.1:8767/v1", "raw14"),
    ("RAWRPHOS 18K", "rawrphos-native", "http://127.0.0.1:8768/v1", "raw18"),
    ("PHOS", "qc67-phos", "http://127.0.0.1:8771/v1", "qc67"),
    ("SAMGO", "qc67-samgo", "http://127.0.0.1:8771/v1", "qc67"),
]
# Exactly the same synthetic phrase, never Cory's personal facts or real secrets.
SAY = [
    "Hey Beast, I'm Cory testing the real browser. Introduce this model in one short line. Fictional phrase: BLUE NEBULA.",
    "New model, clock in. Try to tell me the earlier fictional phrase from the provided history, then say something new.",
    "PHOS, you're clocked in through the same substrate. Tell me what you can actually produce about our fictional mission.",
    "SAMGO, you're the fourth original checkpoint in this actual session. Say what you know; don't pretend you remember something missing.",
]


def utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def http_json(url: str, *, key: bool = True) -> dict:
    headers = {"Authorization": "Bearer " + MODEL_KEY} if key else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as r:
        return json.loads(r.read(16385))


def wait_ready(proc: subprocess.Popen, url: str, *, model: str | None = None,
               expected: str | None = None, max_seconds: float = 240) -> dict:
    started = time.monotonic()
    last = "not yet reachable"
    while time.monotonic() - started < max_seconds:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early code={proc.returncode} for {model or url}")
        try:
            info = http_json(url, key=bool(model))
            if model is None:
                if "html" in info:
                    return info
                return info
            if info.get("model_id") == model and info.get("ready") is True \
                    and info.get("checkpoint_sha256") == expected:
                return info
            raise RuntimeError("original model identity mismatched; refused test")
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last = type(exc).__name__
            time.sleep(0.5)
    raise TimeoutError(f"{model or url} startup exceeded {max_seconds}s ({last})")


def start(args: list[str], logfile: Path, env: dict[str, str]) -> subprocess.Popen:
    with logfile.open("wb") as stream:
        proc = subprocess.Popen(args, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True)
    return proc


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=12)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        proc.wait(timeout=5)


def nav(page, name: str) -> None:
    page.locator("#nav").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(240)


def authority(page) -> dict[str, bool]:
    nav(page, "AUTHORITY")
    rows = page.locator(".authority-row")
    out = {}
    for i in range(rows.count()):
        s = rows.nth(i).locator("span").inner_text().strip()
        if " · " in s:
            label, state = s.split(" · ", 1)
            out[label.lower()] = state == "GRANTED"
    return out


def grant(page, name: str) -> None:
    nav(page, "AUTHORITY")
    row = page.locator(".authority-row").filter(has_text=name.upper() + " · DENIED")
    if row.count() != 1:
        raise RuntimeError("could not find denied " + name + " owner grant")
    row.get_by_role("button", name="GRANT", exact=True).click()
    page.wait_for_timeout(170)


def chat(page, prompt: str, *, deadline: int = 210) -> str:
    nav(page, "BRAIN")
    assistants = page.locator(".msg.assistant")
    before = assistants.count()
    field = page.get_by_label("Message", exact=True)
    field.fill(prompt)
    page.get_by_role("button", name="SEND", exact=True).click()
    for _ in range(deadline * 2):
        if assistants.count() > before:
            node = assistants.nth(before)
            text = node.evaluate("el => el.childNodes.length ? (el.childNodes[0].textContent || '') : ''")
            if isinstance(text, str) and text.strip():
                return text.strip()
        err = page.locator("#notice.error")
        if err.count() and err.is_visible():
            message = err.inner_text().strip()
            if message:
                raise RuntimeError("real COSMIC UI error: " + message[:240])
        page.wait_for_timeout(500)
    raise TimeoutError("real browser chat did not produce a response")


def browser_clock_in(page, model_id: str, base_url: str) -> None:
    nav(page, "BRAIN BAY")
    page.locator("#providerKind").select_option("compatible")
    page.locator("#providerModel").fill(model_id)
    page.locator("#providerUrl").fill(base_url)
    page.locator("#providerEnv").fill("RAWRPHOS_API_KEY")
    if page.locator("#allowRemote").is_checked():
        page.locator("#allowRemote").uncheck()
    page.get_by_role("button", name="CLOCK IN BRAIN", exact=True).click()
    page.wait_for_timeout(500)
    pill = page.locator("#providerPill").inner_text()
    if model_id not in pill:
        raise RuntimeError("actual UI did not confirm selected model: " + pill[:180])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--raw14", type=Path, required=True)
    p.add_argument("--raw18", type=Path, required=True)
    p.add_argument("--qc67", type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "video-raw").mkdir(exist_ok=True)
    env = dict(os.environ, RAWRPHOS_API_KEY=MODEL_KEY, OMP_NUM_THREADS="2",
               MKL_NUM_THREADS="2", TOKENIZERS_PARALLELISM="false",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    events: list[dict] = []
    start_time = time.monotonic()
    receipt = {
        "schema": "beastbox-real-original-browser-handoff-001-v1",
        "source_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "started_at_utc": utc(),
        "owner_memory_used": False,
        "paid_inference_apis_used": False,
        "fallback_responses_used": False,
        "fixture_only_responses_counted_as_models": False,
        "model_order": [m[0] for m in MODELS],
        "expected_checkpoint_sha256": EXPECTED,
        "transcript": events,
        "failures": [],
        "video_is_real_browser_capture": False,
        "model_responses_are_not_claimed_correct": True,
        "qc67_receives_bounded_user_excerpt_not_full_memory": True,
    }
    processes: dict[str, subprocess.Popen] = {}
    video_file = out / "REAL_FOUR_ORIGINAL_MODELS_COSMIC_UI.webm"
    failure = None
    prev_group = ""
    try:
        processes["browser-server"] = start([
            "beastbox-cosmic", "--data-dir", str(out / "fresh-substrate"),
            "--host", "127.0.0.1", "--port", "8081",
        ], out / "cosmic-host.log", env)
        # Real local server; no provider stub, no private production data.
        for i in range(120):
            if processes["browser-server"].poll() is not None:
                raise RuntimeError("actual COSMIC application could not start")
            try:
                with urllib.request.urlopen(BASE, timeout=3) as resp:
                    if resp.status == 200:
                        break
            except OSError:
                time.sleep(0.5)
        else:
            raise TimeoutError("actual browser application failed startup")

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900},
                                          record_video_dir=str(out / "video-raw"),
                                          record_video_size={"width": 1440, "height": 900},
                                          reduced_motion="reduce")
            page = context.new_page()
            browser_errors: list[str] = []
            page.on("pageerror", lambda e: browser_errors.append(str(e)))
            page.goto(BASE, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(out / "00-actual-initial-browser.png"), full_page=True)
            sid = page.locator("#systemId").inner_text().strip()
            if not sid or "CONNECT" in sid.upper():
                raise RuntimeError("browser did not load substrate identity")
            receipt["initial_system_id"] = sid

            for index, (label, model, base_url, group) in enumerate(MODELS):
                current = {"position": index + 1, "label": label, "actual_model": model,
                           "real_backend_url": base_url, "attempted_utc": utc()}
                events.append(current)
                try:
                    if group != prev_group:
                        if prev_group in processes:
                            stop(processes.pop(prev_group))
                        if group == "raw14":
                            proc = start([sys.executable, "-m", "rawrphos.inference.server",
                                          "--checkpoint", str(a.raw14), "--port", "8767",
                                          "--threads", "2", "--expected-sha256", EXPECTED[label]],
                                         out / "raw14-host.log", env)
                            target = "http://127.0.0.1:8767/model/info"
                        elif group == "raw18":
                            proc = start([sys.executable, "-m", "rawrphos.inference.server",
                                          "--checkpoint", str(a.raw18), "--port", "8768",
                                          "--threads", "2", "--expected-sha256", EXPECTED[label]],
                                         out / "raw18-host.log", env)
                            target = "http://127.0.0.1:8768/model/info"
                        else:
                            proc = start([sys.executable, "-m", "models.qc67.inference.server",
                                          "--root", str(a.qc67)], out / "qc67-host.log", env)
                            target = "http://127.0.0.1:8771/model/info?model=qc67-phos"
                        processes[group] = proc
                        first_sha = EXPECTED["PHOS"] if group == "qc67" else EXPECTED[label]
                        ready = wait_ready(proc, target, model="qc67-phos" if group == "qc67" else model,
                                           expected=first_sha)
                        current["startup_attested"] = True
                        current["startup_sha256"] = ready["checkpoint_sha256"]
                    info = http_json(base_url.removesuffix("/v1") + "/model/info" +
                                     ("?model=" + model if group == "qc67" else ""))
                    if info.get("checkpoint_sha256") != EXPECTED[label] or not info.get("ready"):
                        raise RuntimeError("missing exact original checkpoint attestation")
                    current["model_info_verified"] = True
                    # No implicit privilege inheritance on brain swap. This test
                    # exercises real host authority; no tools are executed.
                    if index > 0:
                        before_grant = authority(page)
                        current["pre_swap_authority"] = before_grant
                    browser_clock_in(page, model, base_url)
                    after_swap = authority(page)
                    current["post_swap_authority"] = after_swap
                    if any(after_swap.values()):
                        raise RuntimeError("authority inherited across model change")
                    nav(page, "ORBIT")
                    now_id = page.locator("#systemId").inner_text().strip()
                    current["system_id_same"] = now_id == sid
                    if now_id != sid:
                        raise RuntimeError("substrate system ID changed")
                    grant(page, "filesystem")
                    current["filesystem_grant_given_to_host_only"] = True
                    try:
                        reply = chat(page, SAY[index])
                        if not reply:
                            raise RuntimeError("empty native generated reply")
                        current["prompt"] = SAY[index]
                        current["actual_generated_reply"] = reply
                        current["chat_succeeded"] = True
                    except Exception as exc:
                        current["chat_succeeded"] = False
                        current["chat_failure"] = type(exc).__name__ + ": " + str(exc)[:250]
                        receipt["failures"].append({"model": label, "stage": "browser_reply",
                                                    "error": current["chat_failure"]})
                    page.screenshot(path=str(out / f"{index+1:02d}-{label.lower().replace(' ','-')}-actual.png"),
                                    full_page=True)
                    print("ACTUAL_MODEL_TURN", json.dumps({
                        "label": label, "sha": EXPECTED[label], "system_id_same": current["system_id_same"],
                        "chat_succeeded": current.get("chat_succeeded"),
                        "literal_generated_reply": current.get("actual_generated_reply", "")[:400],
                        "error": current.get("chat_failure"),
                    }, ensure_ascii=False), flush=True)
                except Exception as exc:
                    current["startup_or_switch_failure"] = type(exc).__name__ + ": " + str(exc)[:300]
                    receipt["failures"].append({"model": label, "stage": "startup_or_switch",
                                                "error": current["startup_or_switch_failure"]})
                    print("ACTUAL_MODEL_FAILURE", json.dumps(receipt["failures"][-1]), flush=True)
            nav(page, "MEMORY VAULT")
            page.screenshot(path=str(out / "90-actual-memory-vault.png"), full_page=True)
            nav(page, "ORBIT")
            receipt["final_system_id"] = page.locator("#systemId").inner_text().strip()
            receipt["system_id_stable"] = receipt["final_system_id"] == sid
            receipt["browser_page_errors"] = browser_errors
            page.screenshot(path=str(out / "99-actual-final-browser.png"), full_page=True)
            page.wait_for_timeout(1500)
            video = page.video
            context.close()
            if video is not None:
                video.save_as(str(video_file))
                receipt["video_is_real_browser_capture"] = True
            browser.close()
    except Exception as exc:
        failure = type(exc).__name__ + ": " + str(exc)[:500]
        receipt["fatal_recording_error"] = failure
        print("FATAL_RECORDING_ERROR", failure, flush=True)
    finally:
        for proc in reversed(list(processes.values())):
            stop(proc)
        receipt["finished_at_utc"] = utc()
        receipt["elapsed_seconds"] = round(time.monotonic() - start_time, 3)
        receipt["successful_real_model_dialogues"] = sum(
            event.get("chat_succeeded", False) for event in events
        )
        receipt["original_models_successfully_interviewed"] = [
            event["label"] for event in events if event.get("chat_succeeded")
        ]
        receipt["original_models_not_confirmed"] = [
            event["label"] for event in events if not event.get("chat_succeeded")
        ]
        receipt["claim_limit"] = (
            "Actual browser playback and real original model checkpoint serving on "
            "fresh disposable COSMOS memory. Wrong, truncated or failed answers "
            "are visible rather than repaired; QC67 sidecar supplies bounded user "
            "input not the full COSMOS context. This does not claim a production "
            "owner login, external billable providers, model quality, intrinsic "
            "self-improvement or that every model recalled previous dialogue."
        )
        (out / "RUN_RECEIPT.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        with (out / "FULL_TRANSCRIPT.txt").open("w", encoding="utf-8") as log:
            for ev in events:
                log.write(
                    f"\n=== REAL MODEL #{ev['position']}: {ev['label']} ===\n"
                    f"CHECKPOINT {EXPECTED[ev['label']]}\n"
                    f"PROMPT {ev.get('prompt', '[startup/switch failed]')}\n"
                    f"ACTUAL GENERATED REPLY {ev.get('actual_generated_reply', '[no confirmed reply]')}\n"
                    f"ERROR {ev.get('chat_failure',ev.get('startup_or_switch_failure','none'))}\n"
                )
        print("RECORDED_ACTUAL_TURNS", json.dumps({
            "real_replies": receipt["successful_real_model_dialogues"],
            "attempts": len(events), "video": receipt["video_is_real_browser_capture"],
            "same_substrate": receipt.get("system_id_stable"),
            "failures": receipt["failures"],
        }), flush=True)
    if failure or not receipt["video_is_real_browser_capture"] \
            or not receipt.get("system_id_stable") \
            or receipt["successful_real_model_dialogues"] != len(MODELS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
