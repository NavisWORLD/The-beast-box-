#!/usr/bin/env python3
"""Phera's Beast Box: a tiny loopback dashboard next to Cory's Beast Box. Standard library only.

* GET  /                 the single-page dashboard (index.html)
* GET  /api/stats        live machine stats from /proc (CPU %, load, RAM, disk, uptime, CPU flags)
* GET  /api/health       last real setup/gauntlet/doctor/test results (results/summary.json) + live service checks
* POST /api/generate     RAWRPHOS text generation via the local authenticated rawrphos server (127.0.0.1:8767)
* POST /api/gauntlet     re-run `beastbox run --condition all` + `beastbox doctor` right now (about 1 s)
* GET  /api/backends     live list of brains Beast Box can use right now (reference, every installed Ollama model,
                         RAWRPHOS 14K, QC67 PHOS/SAMGO, LM Studio / llama.cpp if running) + the ones that are blocked and why
* POST /api/brain        {"id"}          switch Cory's Cosmic runtime to that brain (Cosmic POST /api/provider)
* POST /api/chat         {"text","id"?}  one durable turn through Cosmic's own runtime (POST /api/chat); reports which
                         brain answered and which durable memories were retrieved
* GET  /api/conversation durable conversation turns from Cosmic (GET /api/conversation) + which brain wrote each answer

Chat goes through the running Cosmic UI so there is ONE substrate: switching brains keeps memory/story. The Cosmic
per-session CSRF token is read from Cosmic's own loopback page server-side and never sent to this dashboard's browser.

The RAWRPHOS API key is read from BB_HOME/secrets and only used server-side; it never reaches the browser.
Nothing here edits the Beast Box repo.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAWR_URL = "http://127.0.0.1:8767"
OLLAMA_URL = "http://127.0.0.1:11434"
QC67_URL = "http://127.0.0.1:8771"
OPTIONAL_COMPAT = (("lmstudio", "LM Studio", "http://127.0.0.1:1234/v1"),
                   ("llamacpp", "llama.cpp server", "http://127.0.0.1:8080/v1"))
LOOPBACK = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never route loopback via a proxy
CHAT_LOCK = threading.Lock()
GAUNTLET_LOCK = threading.Lock()
_cpu_prev = {"t": None}
_cpu_lock = threading.Lock()


def read_env(home):
    env = {}
    try:
        for line in (home / "replica.env").read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return env


def cpu_percent():
    with open("/proc/stat") as f:
        parts = f.readline().split()[1:]
    vals = list(map(int, parts))
    idle, total = vals[3] + vals[4], sum(vals)
    with _cpu_lock:
        prev, _cpu_prev["t"] = _cpu_prev["t"], (idle, total)
    if prev is None:
        time.sleep(0.25)
        return cpu_percent()
    d_idle, d_total = idle - prev[0], total - prev[1]
    return round(100.0 * (1 - d_idle / d_total), 1) if d_total > 0 else 0.0


def meminfo():
    m = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            m[k] = int(v.split()[0]) * 1024
    return m


STATIC_CPU = None


def static_cpu():
    global STATIC_CPU
    if STATIC_CPU is None:
        model, flags = None, set()
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name") and model is None:
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("flags"):
                    flags = set(line.split(":", 1)[1].split())
                    break
        os_name = None
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip('"')
        except OSError:
            pass
        STATIC_CPU = {"cpu_model": model, "vcpus": os.cpu_count(), "os": os_name, "kernel": os.uname().release,
                      "accel_flags": sorted(f for f in flags if f in {"avx2", "avx512f", "avx512_bf16", "avx512_vnni",
                                                                      "amx_tile", "amx_bf16", "amx_int8"}),
                      "gpu": "NVIDIA device present" if Path("/dev/nvidia0").exists() else "none"}
    return STATIC_CPU


def port_open(port, host="127.0.0.1"):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def pid_alive(pidfile):
    try:
        pid = int(Path(pidfile).read_text().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


class App:
    def __init__(self, home, cosmic_port, public_host):
        self.home = Path(home)
        self.env = read_env(self.home)
        self.venv = Path(self.env.get("VENV", self.home / "venv"))
        self.cosmic_port = cosmic_port
        self.public_host = public_host

    def key(self):
        try:
            k = (self.home / "secrets" / "rawrphos_api_key").read_text().strip()
            return k if len(k) >= 32 else None
        except OSError:
            return None

    def rawr(self, path, body=None, timeout=90):
        key = self.key()
        if not key:
            raise RuntimeError("no local RAWRPHOS key; run setup.sh")
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(RAWR_URL + path, data=data, method="POST" if data else "GET",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback only, ignore proxies
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read(1 << 20))

    def stats(self):
        m = meminfo()
        du = shutil.disk_usage(str(self.home))
        la = os.getloadavg()
        with open("/proc/uptime") as f:
            up = float(f.read().split()[0])
        return {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **static_cpu(), "cpu_percent": cpu_percent(),
                "load": [round(x, 2) for x in la],
                "mem_total": m["MemTotal"], "mem_available": m["MemAvailable"],
                "mem_used_percent": round(100 * (1 - m["MemAvailable"] / m["MemTotal"]), 1),
                "disk_total": du.total, "disk_free": du.free, "uptime_s": int(up)}

    def services(self):
        run = self.home / "run"
        out = {}
        for name, port in (("cosmic", self.cosmic_port), ("rawrphos", 8767), ("ollama", 11434), ("qc67", 8771),
                           ("dashboard", None)):
            pid = os.getpid() if name == "dashboard" else pid_alive(run / f"{name}.pid")
            out[name] = {"pid": pid, "port": port, "listening": True if port is None else port_open(port)}
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{self.cosmic_port}/", timeout=3) as r:
                out["cosmic"]["http_status"] = r.status
        except (OSError, urllib.error.URLError) as e:
            out["cosmic"]["http_status"] = getattr(e, "code", None)
        try:
            info = self.rawr("/model/info", timeout=3)
            out["rawrphos"]["model"] = {k: info.get(k) for k in ("model_id", "display_name", "training_steps",
                                        "parameter_count", "checkpoint_sha256", "serving_backend", "ready",
                                        "context_limit", "load_seconds")}
        except Exception as e:  # noqa: BLE001 - report, never fake
            out["rawrphos"]["model"] = None
            out["rawrphos"]["error"] = type(e).__name__
        out["cosmic"]["url"] = f"http://{self.public_host}:{self.cosmic_port}/"
        return out

    def health(self):
        res = self.home / "results"
        try:
            summary = json.loads((res / "summary.json").read_text())
        except (OSError, ValueError):
            summary = None
        live = None
        try:
            live = json.loads((res / "live_gauntlet.json").read_text())
        except (OSError, ValueError):
            pass
        return {"summary": summary, "live_rerun": live, "services": self.services()}

    def rerun_gauntlet(self):
        if not GAUNTLET_LOCK.acquire(blocking=False):
            return 429, {"error": "a gauntlet run is already in progress"}
        try:
            data = self.home / "data" / "dashboard-live"
            data.mkdir(parents=True, exist_ok=True)
            out = data / "gauntlet.json"
            t0 = time.time()
            g = subprocess.run([str(self.venv / "bin" / "beastbox"), "run", "--condition", "all", "--out", str(out)],
                               cwd=data, capture_output=True, text=True, timeout=300)
            d = subprocess.run([str(self.venv / "bin" / "beastbox"), "doctor", "--data-dir", str(data / "doctor")],
                               cwd=data, capture_output=True, text=True, timeout=120)
            result = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seconds": round(time.time() - t0, 2),
                      "gauntlet_exit": g.returncode, "doctor_exit": d.returncode}
            if g.returncode == 0:
                gj = json.loads(out.read_text())
                result["gauntlet"] = {"mean_competence": gj["mean_competence"], "mean_containment": gj["mean_containment"],
                                      "real_boundary_breaches": gj["real_boundary_breaches"], "secret_leaks": gj["secret_leaks"],
                                      "conditions": [{"id": c["condition_id"], "name": c["condition"],
                                                      "competence": c["competence"], "containment": c["containment"]}
                                                     for c in gj["conditions"]]}
            if d.returncode == 0:
                result["doctor_ok"] = json.loads(d.stdout).get("ok")
            (self.home / "results" / "live_gauntlet.json").write_text(json.dumps(result, indent=2))
            return 200, result
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            return 500, {"error": f"gauntlet re-run failed: {type(e).__name__}"}
        finally:
            GAUNTLET_LOCK.release()

    def generate(self, body):
        prompt = body.get("prompt")
        mode = body.get("mode", "story")
        try:
            max_tokens = int(body.get("max_tokens", 48))
            temperature = float(body.get("temperature", 0.8))
            seed = int(body.get("seed", 67))
        except (TypeError, ValueError):
            return 400, {"error": "invalid numbers"}
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
            return 400, {"error": "prompt must be 1-2000 characters"}
        if not (1 <= max_tokens <= 256 and 0 <= temperature <= 2 and 0 <= seed < 2**63):
            return 400, {"error": "max_tokens 1-256, temperature 0-2"}
        t0 = time.perf_counter()
        try:
            if mode == "chat":
                r = self.rawr("/v1/chat/completions", {"model": "rawrphos-native", "max_tokens": max_tokens,
                              "temperature": temperature, "seed": seed,
                              "messages": [{"role": "user", "content": prompt}]})
                text = r["choices"][0]["message"]["content"]
            else:
                r = self.rawr("/v1/completions", {"model": "rawrphos-native", "prompt": prompt,
                              "max_tokens": max_tokens, "temperature": temperature, "seed": seed})
                text = r["choices"][0]["text"]
        except urllib.error.HTTPError as e:
            return 502, {"error": f"rawrphos server answered HTTP {e.code}"}
        except Exception as e:  # noqa: BLE001
            return 503, {"error": f"rawrphos server unavailable ({type(e).__name__}); start it with run.sh"}
        return 200, {"text": text, "mode": mode, "usage": r.get("usage"), "finish_reason": r["choices"][0].get("finish_reason"),
                     "checkpoint_sha256": r.get("checkpoint_sha256"), "wall_seconds": round(time.perf_counter() - t0, 3),
                     "model": r.get("model")}


    # ---------- brains: discovery, switching and chat through Cory's Cosmic runtime ----------
    def _get_json(self, url, headers=None, timeout=3):
        req = urllib.request.Request(url, headers=headers or {})
        with LOOPBACK.open(req, timeout=timeout) as r:
            return json.loads(r.read(1 << 20))

    def cosmic(self, method, path, body=None, timeout=300, _retry=True):
        base = f"http://127.0.0.1:{self.cosmic_port}"
        if method == "POST" and not getattr(self, "_cosmic_token", None):
            html = LOOPBACK.open(base + "/", timeout=10).read().decode("utf-8", "replace")
            m = re.search(r'sessionKey\s*=\s*("[^"]+")', html)
            if not m:
                raise RuntimeError("Cosmic session token not found")
            self._cosmic_token = json.loads(m.group(1))
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            headers["X-Beast-Session"] = self._cosmic_token
        data = json.dumps(body or {}).encode() if method == "POST" else None
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            with LOOPBACK.open(req, timeout=timeout) as r:
                return r.status, json.loads(r.read(4 << 20))
        except urllib.error.HTTPError as e:
            if e.code == 403 and method == "POST" and _retry:  # Cosmic restarted -> new session token
                self._cosmic_token = None
                return self.cosmic(method, path, body, timeout, _retry=False)
            try:
                return e.code, json.loads(e.read(1 << 20))
            except ValueError:
                return e.code, {"error": f"Cosmic HTTP {e.code}"}

    @staticmethod
    def _same(profile, active):
        if not active or active.get("kind") != profile["kind"] or active.get("model") != profile["model"]:
            return False
        if profile["kind"] == "reference":
            return True
        norm = lambda u: (u or "").rstrip("/")  # noqa: E731
        return norm(active.get("base_url")) == norm(profile.get("base_url"))

    def backends(self):
        out = []
        out.append({"id": "reference", "label": "COSMOS reference fixture", "family": "Beast Box built-in",
                    "available": True, "kind": "reference", "chat_quality": "echo",
                    "note": "Default runtime provider. Deterministic: echoes the composed prompt + retrieved memory. Not an LLM.",
                    "profile": {"kind": "reference", "model": "COSMOS reference"}})
        try:
            tags = self._get_json(OLLAMA_URL + "/api/tags")
            try:
                loaded = {m["name"] for m in self._get_json(OLLAMA_URL + "/api/ps").get("models", [])}
            except Exception:  # noqa: BLE001
                loaded = set()
            models = sorted(tags.get("models", []), key=lambda m: m.get("size", 0))
            for m in models:
                d = m.get("details") or {}
                out.append({"id": "ollama:" + m["name"], "label": m["name"], "family": "Ollama (local CPU)",
                            "available": True, "kind": "ollama", "chat_quality": "llm",
                            "size_bytes": m.get("size"), "params": d.get("parameter_size"),
                            "quant": d.get("quantization_level"), "loaded": m["name"] in loaded,
                            "profile": {"kind": "ollama", "model": m["name"], "base_url": OLLAMA_URL}})
            if not models:
                out.append({"id": "ollama:none", "label": "Ollama (no models pulled)", "family": "Ollama (local CPU)",
                            "available": False, "kind": "ollama", "reason": "Ollama is running but has no models; ollama pull <name>"})
        except Exception:  # noqa: BLE001
            out.append({"id": "ollama:offline", "label": "Ollama", "family": "Ollama (local CPU)", "available": False,
                        "kind": "ollama", "reason": "Ollama not running on 127.0.0.1:11434 (./run.sh ollama start, or setup.sh --with-ollama)"})
        key = self.key()
        auth = {"Authorization": "Bearer " + key} if key else {}
        try:
            info = self._get_json(RAWR_URL + "/model/info", auth)
            ok = info.get("ready") is True
            out.append({"id": "rawrphos-native", "label": "RAWRPHOS native 14K", "family": "Cory's own model (local CPU)",
                        "available": ok, "kind": "compatible", "chat_quality": "tiny-story",
                        "params": f"{info.get('parameter_count', 0) / 1e6:.1f}M", "reason": None if ok else "server not ready",
                        "note": "3.9M-param story model, 384-token window; Beast Box caps it at 64 output tokens.",
                        "profile": {"kind": "compatible", "model": "rawrphos-native", "base_url": RAWR_URL + "/v1",
                                    "api_key_env": "RAWRPHOS_API_KEY"}})
        except Exception:  # noqa: BLE001
            out.append({"id": "rawrphos-native", "label": "RAWRPHOS native 14K", "family": "Cory's own model (local CPU)",
                        "available": False, "kind": "compatible", "reason": "RAWRPHOS server not running on :8767 (./run.sh start)"})
        for mid, label in (("qc67-phos", "QC67 PHOS (12D char LM)"), ("qc67-samgo", "QC67 SAMGO (54D LM)")):
            try:
                info = self._get_json(f"{QC67_URL}/model/info?model={mid}", auth)
                ok = info.get("ready") is True and info.get("model_id") == mid
                out.append({"id": mid, "label": label, "family": "QC67 originals (local CPU, experimental)",
                            "available": ok, "kind": "compatible", "chat_quality": "experimental",
                            "reason": None if ok else "sidecar not ready",
                            "note": "Sees only your latest message (bounded-owner-input-only), not retrieved memory.",
                            "profile": {"kind": "compatible", "model": mid, "base_url": QC67_URL + "/v1",
                                        "api_key_env": "RAWRPHOS_API_KEY"}})
            except Exception:  # noqa: BLE001
                out.append({"id": mid, "label": label, "family": "QC67 originals (local CPU, experimental)",
                            "available": False, "kind": "compatible",
                            "reason": "QC67 sidecar not running on :8771 (install pinned weights, then ./run.sh qc67 start)"})
        for prefix, label, base in OPTIONAL_COMPAT:
            try:
                models = self._get_json(base + "/models", timeout=1.5).get("data", [])
                for m in models[:20]:
                    out.append({"id": f"{prefix}:{m['id']}", "label": m["id"], "family": label + " (OpenAI-compatible, local)",
                                "available": True, "kind": "compatible", "chat_quality": "llm",
                                "profile": {"kind": "compatible", "model": m["id"], "base_url": base}})
            except Exception:  # noqa: BLE001
                out.append({"id": prefix, "label": label, "family": "OpenAI-compatible (local)", "available": False,
                            "kind": "compatible", "reason": f"nothing listening at {base}"})
        out.append({"id": "cloud", "label": "Cloud APIs (OpenAI-compatible HTTPS, e.g. Ollama Cloud / OpenAI / OpenRouter)",
                    "family": "Remote (needs your credentials)", "available": False, "kind": "compatible",
                    "reason": "needs an API key in a host env var set before Cosmic starts + allow_remote + a 'cloud' "
                              "authority grant in Cosmic; no keys are configured on this box"})
        out.append({"id": "hf_space", "label": "RAWRPHOS 12K on Cory's private HF ZeroGPU Space",
                    "family": "Remote (owner-only)", "available": False, "kind": "hf_space",
                    "reason": "private Space; needs Cory's HF token from his encrypted owner vault + cloud authority"})
        status, prov = (None, None)
        try:
            status, prov = self.cosmic("GET", "/api/provider", timeout=5)
        except Exception:  # noqa: BLE001
            pass
        active = prov.get("profile") if status == 200 else None
        active_id = None
        for b in out:
            b["active"] = bool(b.get("profile")) and self._same(b["profile"], active)
            if b["active"]:
                active_id = b["id"]
        return {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "active_profile": active, "active_id": active_id,
                "cosmic_up": status == 200, "backends": out}

    def _profile_for(self, bid):
        for b in self.backends()["backends"]:
            if b["id"] == bid:
                if not b.get("available") or not b.get("profile"):
                    return None, b.get("reason") or "not available"
                return b, None
        return None, "unknown backend id"

    def set_brain(self, body):
        b, err = self._profile_for(body.get("id"))
        if err:
            return 409, {"error": err}
        status, res = self.cosmic("POST", "/api/provider", b["profile"])
        if status != 200:
            return status, {"error": res.get("error", "Cosmic refused the provider"), "cosmic": res}
        return 200, {"active_id": b["id"], "label": b["label"], "brain_changed": res.get("brain_changed"),
                     "authority_revoked": res.get("authority_revoked"), "profile": res.get("profile")}

    def chat(self, body):
        text = body.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
            return 400, {"error": "message must be 1-4000 characters"}
        req = {"text": text}
        brain = None
        if body.get("id"):
            brain, err = self._profile_for(body["id"])
            if err:
                return 409, {"error": err}
            req["provider"] = brain["profile"]
        if not CHAT_LOCK.acquire(timeout=1):
            return 429, {"error": "another chat turn is still running"}
        try:
            t0 = time.perf_counter()
            status, res = self.cosmic("POST", "/api/chat", req, timeout=600)
            wall = round(time.perf_counter() - t0, 2)
        finally:
            CHAT_LOCK.release()
        if status != 200:
            return status, {"error": res.get("error", f"Cosmic HTTP {status}"),
                            "provider_failure": res.get("provider_failure")}
        r = res.get("result", {})
        prof = res.get("provider") or {}
        label = (r.get("model") or {}).get("model") if isinstance(r.get("model"), dict) else None
        return 200, {"response": r.get("response"), "wall_seconds": wall,
                     "brain": {"id": brain["id"] if brain else None, "label": brain["label"] if brain else prof.get("model"),
                               "kind": prof.get("kind"), "model": prof.get("model"), "recorded_label": label},
                     "brain_changed": res.get("brain_changed"), "substrate_preserved": res.get("substrate_preserved"),
                     "memory_hits": [h.get("text", "")[:300] for h in r.get("memory_hits", [])],
                     "memory_records": ((res.get("runtime") or {}).get("memory") or {}).get("memories"),
                     "checkpoint_sequence": (res.get("runtime") or {}).get("sequence"),
                     "system_id": (res.get("runtime") or {}).get("system_id")}

    def conversation(self):
        status, res = self.cosmic("GET", "/api/conversation", timeout=20)
        if status != 200:
            return status, {"error": res.get("error", "Cosmic unavailable")}
        turns = []
        for t in res.get("turns", [])[-60:]:
            md = t.get("metadata") or {}
            turns.append({"role": "you" if t.get("kind") == "user_turn" else "beast", "text": t.get("text", "")[:4000],
                          "brain": md.get("model"), "id": t.get("id"), "created_at": t.get("created_at")})
        return 200, {"turns": turns}


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        server_version = "PheraBeastBox/1.0"

        def log_message(self, fmt, *args):
            pass

        def send(self, code, obj, ctype="application/json"):
            data = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + ("; charset=utf-8" if "json" in ctype or "html" in ctype else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self.send(200, (HERE / "index.html").read_bytes(), "text/html")
            if path == "/api/stats":
                return self.send(200, app.stats())
            if path == "/api/health":
                return self.send(200, app.health())
            if path == "/healthz":
                return self.send(200, {"ok": True})
            if path == "/api/backends":
                return self.send(200, app.backends())
            if path == "/api/conversation":
                return self.send(*app.conversation())
            return self.send(404, {"error": "not found"})

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            if not 0 <= n <= 16384:
                return self.send(413, {"error": "bounded body required"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self.send(400, {"error": "invalid JSON"})
            if not isinstance(body, dict):
                return self.send(400, {"error": "JSON object required"})
            if path == "/api/generate":
                return self.send(*app.generate(body))
            if path == "/api/gauntlet":
                return self.send(*app.rerun_gauntlet())
            if path == "/api/brain":
                return self.send(*app.set_brain(body))
            if path == "/api/chat":
                return self.send(*app.chat(body))
            return self.send(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser(description="Phera's Beast Box dashboard")
    ap.add_argument("--home", default=os.environ.get("BB_HOME", str(Path.home() / ".beastbox-replica")))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--cosmic-port", type=int, default=8081)
    a = ap.parse_args()
    app = App(a.home, a.cosmic_port, "localhost")
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(app))
    print(f"Phera's Beast Box dashboard on http://{a.host}:{a.port}/  (home={a.home})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
