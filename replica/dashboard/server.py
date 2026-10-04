#!/usr/bin/env python3
"""Phera's Beast Box: a tiny loopback dashboard next to Cory's Beast Box. Standard library only.

* GET  /                 the single-page dashboard (index.html)
* GET  /api/stats        live machine stats from /proc (CPU %, load, RAM, disk, uptime, CPU flags)
* GET  /api/health       last real setup/gauntlet/doctor/test results (results/summary.json) + live service checks
* POST /api/generate     RAWRPHOS text generation via the local authenticated rawrphos server (127.0.0.1:8767)
* POST /api/gauntlet     re-run `beastbox run --condition all` + `beastbox doctor` right now (about 1 s)

The RAWRPHOS API key is read from BB_HOME/secrets and only used server-side; it never reaches the browser.
Nothing here edits the Beast Box repo.
"""
import argparse
import json
import os
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
        for name, port in (("cosmic", self.cosmic_port), ("rawrphos", 8767), ("dashboard", None)):
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
