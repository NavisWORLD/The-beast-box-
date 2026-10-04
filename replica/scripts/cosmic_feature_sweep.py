#!/usr/bin/env python3
"""Exercise every COSMIC.CYPHER UI feature/setting through the same HTTP API the browser UI calls.
Usage: cosmic_feature_sweep.py --port 8082 --workspace /scratch/git/repo --out results/cosmic_features.json
Run it against a SCRATCH Cosmic instance: it grants/revokes authority, writes durable test memories,
writes one file in the scratch workspace and exports/imports snapshots under /tmp. Ends with master stop.
"""
import argparse, json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))
from cosmic_client import Cosmic

ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8082)
ap.add_argument("--workspace", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
c = Cosmic(a.port); rows = []
tmp = tempfile.mkdtemp(prefix="cosmic-sweep-")


def t(area, feature, method, path, body=None, expect=200, note=""):
    t0 = time.time(); st, r = c.call(method, path, body, timeout=600)
    ok = st == expect
    brief = r.get("error") if isinstance(r, dict) and "error" in r else ""
    if isinstance(r, dict) and r.get("provider_failure"):
        brief += f" [{r['provider_failure']}]"
    rows.append({"area": area, "feature": feature, "call": f"{method} {path}", "expected": expect, "status": st,
                 "pass": ok, "detail": brief or note, "seconds": round(time.time() - t0, 2)})
    print(f"{'PASS' if ok else 'FAIL'} {st} {area:<11} {feature:<46} {brief or note}"[:220])
    return r


REF = {"kind": "reference", "model": "COSMOS reference"}
QWEN = {"kind": "ollama", "model": "qwen2.5:1.5b", "base_url": "http://127.0.0.1:11434"}
RAWR = {"kind": "compatible", "model": "rawrphos-native", "base_url": "http://127.0.0.1:8767/v1", "api_key_env": "RAWRPHOS_API_KEY"}
PHOS = {"kind": "compatible", "model": "qc67-phos", "base_url": "http://127.0.0.1:8771/v1", "api_key_env": "RAWRPHOS_API_KEY"}
CLOUD = {"kind": "compatible", "model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1", "allow_remote": True, "api_key_env": "OPENAI_API_KEY"}
OCLOUD = {"kind": "compatible", "model": "gpt-oss:20b", "base_url": "https://ollama.com/v1", "allow_remote": True, "api_key_env": "OLLAMA_API_KEY"}
HF = {"kind": "hf_space", "model": "rawrphos-native", "base_url": "https://huggingface.co/spaces/phera-ra/rawrphos-12k-zerogpu", "allow_remote": True}
EV = lambda text, f: {"schema": "sensor-event-v1", "source": "software-event", "text": text, "features": f}

# ---- probes / read views
t("health", "/healthz liveness", "GET", "/healthz")
t("health", "/readyz readiness (durable runtime valid)", "GET", "/readyz")
orbit = t("orbit", "ORBIT snapshot (runtime, authority, capabilities)", "GET", "/api/orbit")
t("memory", "MEMORY VAULT records", "GET", "/api/memory")
t("trace", "SYNAPSE TRACE / SIGNALS (checkpoint history)", "GET", "/api/trace")
t("brain", "Active brain profile", "GET", "/api/provider")
t("connections", "CONNECTIONS / Q-BAY resource config (IBM/Azure)", "GET", "/api/resources")
t("storage", "SETTINGS / STORAGE status", "GET", "/api/storage")
t("brain", "Conversation history", "GET", "/api/conversation")
t("files", "Context inventory", "GET", "/api/context")
t("workspace", "Workspace snapshot (none selected)", "GET", "/api/workspace")
t("workspace", "Repo status with no workspace -> rejected", "GET", "/api/workspace/status", expect=400)

# ---- Brain Bay (provider kinds) + chat
t("brain-bay", "Clock in: Reference fixture", "POST", "/api/provider", REF)
t("brain", "Chat via reference fixture", "POST", "/api/chat", {"text": "feature sweep hello, reference"})
t("brain-bay", "Clock in: Ollama qwen2.5:1.5b", "POST", "/api/provider", QWEN)
t("brain", "Chat via Ollama", "POST", "/api/chat", {"text": "Reply with one short sentence: feature sweep check."})
t("brain-bay", "Clock in: OpenAI-compatible -> RAWRPHOS 14K", "POST", "/api/provider", RAWR)
t("brain", "Chat via RAWRPHOS 14K", "POST", "/api/chat", {"text": "Once upon a time"})
t("brain-bay", "Clock in: OpenAI-compatible -> QC67 PHOS", "POST", "/api/provider", PHOS)
t("brain", "Chat via QC67 PHOS", "POST", "/api/chat", {"text": "the moon"})
t("brain", "Chat with inline provider switch (one call)", "POST", "/api/chat", {"text": "inline switch back to qwen, say ok", "provider": QWEN})
t("brain-bay", "Ollama model that is not installed -> chat fails closed", "POST", "/api/chat",
  {"text": "hi", "provider": {"kind": "ollama", "model": "not-installed:1b", "base_url": "http://127.0.0.1:11434"}}, expect=400,
  note="no silent fallback")
t("brain-bay", "Non-loopback Ollama URL rejected", "POST", "/api/provider", {"kind": "ollama", "model": "x", "base_url": "http://10.0.0.5:11434"}, expect=400)
t("brain-bay", "Remote HTTPS compatible w/o cloud authority -> 403", "POST", "/api/provider", CLOUD, expect=403)
t("brain-bay", "Remote without allow_remote -> rejected", "POST", "/api/provider", {**CLOUD, "allow_remote": False}, expect=400)
t("brain-bay", "HF Space RAWRPHOS 12K w/o cloud authority -> 403", "POST", "/api/provider", HF, expect=403)
t("authority", "Grant cloud", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain-bay", "Clock in remote OpenAI (cloud granted)", "POST", "/api/provider", CLOUD, note="profile saved; key env var NOT set")
t("authority", "Re-grant cloud (changing brain revokes every grant, by design)", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain", "Chat via remote OpenAI without key -> fails before any network call", "POST", "/api/chat", {"text": "hi"}, expect=400,
  note="needs OPENAI_API_KEY in Cosmic's environment")
t("authority", "Grant cloud again (brain change revoked it)", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain-bay", "Clock in Ollama Cloud gpt-oss:20b (cloud granted)", "POST", "/api/provider", OCLOUD)
t("authority", "Re-grant cloud", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain", "Chat via Ollama Cloud without key -> fails before network", "POST", "/api/chat", {"text": "hi"}, expect=400,
  note="needs OLLAMA_API_KEY")
t("authority", "Grant cloud again", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain-bay", "Clock in HF Space RAWRPHOS 12K (cloud granted)", "POST", "/api/provider", HF)
t("authority", "Re-grant cloud", "POST", "/api/authority", {"action": "grant", "name": "cloud"})
t("brain", "Chat via HF Space without owner token -> MODEL_AUTH_REJECTED / prompt-length guard", "POST", "/api/chat", {"text": "hi"}, expect=502,
  note="needs Cory's HF token from his owner vault (not wired in beastbox-cosmic)")
t("brain-bay", "Clock back in Ollama qwen2.5:1.5b", "POST", "/api/provider", QWEN)

# ---- authority
names = sorted((orbit or {}).get("authority", {}).keys())
for n in names:
    t("authority", f"Grant {n}", "POST", "/api/authority", {"action": "grant", "name": n})
    t("authority", f"Revoke {n}", "POST", "/api/authority", {"action": "revoke", "name": n})
t("authority", "Unknown authority rejected", "POST", "/api/authority", {"action": "grant", "name": "root"}, expect=400)
t("authority", "MASTER PRIVACY STOP", "POST", "/api/authority", {"action": "master_stop"})

# ---- reality / vision / listen events
t("reality", "Sensor observation w/o authority -> 403", "POST", "/api/event", {"modality": "sensor", "event": EV("light 0.4", [0.4])}, expect=403)
t("authority", "Grant sensors", "POST", "/api/authority", {"action": "grant", "name": "sensors"})
t("reality", "SEND AUTHORIZED OBSERVATION (sensor)", "POST", "/api/event", {"modality": "sensor", "event": EV("sweep: bench light level 0.4", [0.4, -0.1])})
t("authority", "Grant camera", "POST", "/api/authority", {"action": "grant", "name": "camera"})
t("vision", "Camera bounded observation (synthetic features, no device)", "POST", "/api/event", {"modality": "camera", "event": EV("sweep camera luma sample", [0.1, 0.2, 0.3])},
  note="browser getUserMedia path itself needs a real camera")
t("authority", "Grant microphone", "POST", "/api/authority", {"action": "grant", "name": "microphone"})
t("listen", "Mic RMS feature sample (synthetic, no device)", "POST", "/api/event", {"modality": "microphone", "event": EV("sweep mic rms", [-0.8])},
  note="browser mic capture needs a real microphone")

# ---- continuous operation queue
t("activation", "Queue status", "GET", "/api/activation")
t("activation", "QUEUE OBSERVATION (sensors granted)", "POST", "/api/activation", {"action": "enqueue_event", "event": EV("sweep queued light 0.2", [0.2])})
t("activation", "QUEUE MAINTENANCE", "POST", "/api/activation", {"action": "enqueue_maintenance"})
t("activation", "EXPLICIT RESUME", "POST", "/api/activation", {"action": "resume", "reason": "feature sweep"})
t("activation", "RUN ONE TASK", "POST", "/api/activation", {"action": "run", "max_tasks": 1, "wall_seconds": 30})
t("activation", "RUN remaining task", "POST", "/api/activation", {"action": "run", "max_tasks": 1, "wall_seconds": 30})
q = t("activation", "EMERGENCY STOP", "POST", "/api/activation", {"action": "stop", "reason": "feature sweep stop"})
q2 = c.call("POST", "/api/activation", {"action": "enqueue_maintenance"})[1]
tid = q2.get("task_id") or (q2.get("task") or {}).get("task_id") or q2.get("id")
if tid:
    t("activation", "Cancel a queued task", "POST", "/api/activation", {"action": "cancel", "task_id": tid, "reason": "sweep"})

# ---- quantum
t("q-bay", "Submit quantum job w/o quantum_live -> 403", "POST", "/api/quantum", {"provider": "ibm", "shots": 16}, expect=403)
t("authority", "Grant quantum_live", "POST", "/api/authority", {"action": "grant", "name": "quantum_live"})
t("q-bay", "IBM hardware adapter (no IBM creds) -> 503", "POST", "/api/quantum", {"provider": "ibm", "shots": 16}, expect=503,
  note="needs IBM_QUANTUM_TOKEN + IBM_QUANTUM_BACKEND (+INSTANCE)")
t("q-bay", "Azure IonQ simulator (no Azure creds) -> 503", "POST", "/api/quantum", {"provider": "azure", "shots": 16}, expect=503,
  note="needs AZURE_QUANTUM_RESOURCE_ID/LOCATION/TARGET + Azure login")

# ---- files / context
r = t("files", "ADD CONTEXT: temporary attachment", "POST", "/api/context", {"scope": "temporary_attachment", "name": "note.txt", "text": "The sweep secret word is NEBULA-7."})
t("files", "Chat using the temporary attachment", "POST", "/api/chat", {"text": "What is the sweep secret word in the attachment?", "context_ids": [r.get("id")]})
r2 = t("files", "ADD CONTEXT: conversation context", "POST", "/api/context", {"scope": "conversation_context", "name": "conv.txt", "text": "Session-only fact: the sweep ran at night."})
t("files", "ADD CONTEXT: persistent memory w/o confirm -> 400", "POST", "/api/context", {"scope": "persistent_memory", "name": "p.txt", "text": "x"}, expect=400)
t("files", "ADD CONTEXT: persistent memory (confirm_persist)", "POST", "/api/context", {"scope": "persistent_memory", "name": "persist.txt", "text": "Durable sweep fact: the beast likes comets.", "confirm_persist": True})
t("files", "Remove context item", "POST", "/api/context/remove", {"id": r2.get("id")})

# ---- workspace
ws = a.workspace
t("workspace", "ALLOW WORKSPACE w/o filesystem -> 403", "POST", "/api/workspace/allow", {"root": ws}, expect=403)
t("authority", "Grant filesystem", "POST", "/api/authority", {"action": "grant", "name": "filesystem"})
t("workspace", "ALLOW WORKSPACE", "POST", "/api/workspace/allow", {"root": ws})
t("workspace", "SELECT WORKSPACE (+ file tree)", "POST", "/api/workspace/select", {"root": ws})
t("workspace", "REPO STATUS", "GET", "/api/workspace/status")
t("workspace", "READ FILE", "POST", "/api/workspace/read", {"path": "README.md"})
t("workspace", "Path escape ../ rejected", "POST", "/api/workspace/read", {"path": "../../etc/passwd"}, expect=400)
t("workspace", "WORKSPACE SEARCH", "POST", "/api/workspace/search", {"query": "hello"})
t("workspace", "PREVIEW DIFF", "POST", "/api/workspace/diff", {"path": "README.md", "content": "# scratch\nhello beast, edited by sweep\n"})
t("workspace", "WRITE FILE w/o repo_write -> 403", "POST", "/api/workspace/write", {"path": "README.md", "content": "x\n"}, expect=403)
t("authority", "GRANT WRITE (repo_write)", "POST", "/api/authority", {"action": "grant", "name": "repo_write"})
t("workspace", "WRITE FILE WITH BACKUP", "POST", "/api/workspace/write", {"path": "sweep-output.md", "content": "written by cosmic feature sweep\n"})
t("files", "ADD CONTEXT: workspace knowledge", "POST", "/api/context", {"scope": "workspace_knowledge", "path": "README.md"})
t("workspace", "RUN AUTHORIZED COMMAND w/o tools -> 403", "POST", "/api/workspace/run", {"argv": ["git", "status", "--short"]}, expect=403)
t("authority", "Grant tools", "POST", "/api/authority", {"action": "grant", "name": "tools"})
for argv in (["git", "status", "--short", "--branch"], ["git", "diff", "--stat"], ["git", "log", "-5", "--oneline"]):
    t("workspace", "RUN " + " ".join(argv), "POST", "/api/workspace/run", {"argv": argv})
t("workspace", "Arbitrary command rejected", "POST", "/api/workspace/run", {"argv": ["rm", "-rf", "/"]}, expect=400)

# ---- storage / continuity capsule
e = t("storage", "EXPORT SNAPSHOT (plaintext v1)", "POST", "/api/storage/export", {"destination": tmp + "/snap-v1"})
h = (e or {}).get("manifest_sha256")
t("storage", "VERIFY SNAPSHOT", "POST", "/api/storage/verify", {"bundle": tmp + "/snap-v1", "manifest_sha256": h or "0" * 64})
t("storage", "VERIFY with wrong hash -> rejected", "POST", "/api/storage/verify", {"bundle": tmp + "/snap-v1", "manifest_sha256": "0" * 64}, expect=400)
t("storage", "IMPORT SNAPSHOT to new dir", "POST", "/api/storage/import", {"bundle": tmp + "/snap-v1", "destination": tmp + "/restored-v1", "manifest_sha256": h or "0" * 64})
e2 = t("storage", "EXPORT SNAPSHOT sealed v2 (passphrase)", "POST", "/api/storage/export", {"destination": tmp + "/snap-v2", "passphrase": "sweep-passphrase-123"})
h2 = (e2 or {}).get("manifest_sha256")
t("storage", "VERIFY sealed snapshot", "POST", "/api/storage/verify", {"bundle": tmp + "/snap-v2", "manifest_sha256": h2 or "0" * 64, "passphrase": "sweep-passphrase-123"})
t("storage", "IMPORT sealed snapshot", "POST", "/api/storage/import", {"bundle": tmp + "/snap-v2", "destination": tmp + "/restored-v2", "manifest_sha256": h2 or "0" * 64, "passphrase": "sweep-passphrase-123"})

# ---- guards
st, _ = c.call("POST", "/api/chat", {"text": ""}); rows.append({"area": "guards", "feature": "Empty chat rejected", "call": "POST /api/chat", "expected": 400, "status": st, "pass": st == 400, "detail": ""})
import urllib.request, urllib.error
try:
    urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(c.base + "/api/chat", data=b"{}", method="POST"), timeout=5); s3 = 200
except urllib.error.HTTPError as ex:
    s3 = ex.code
rows.append({"area": "guards", "feature": "POST without session token -> 403 (CSRF)", "call": "POST /api/chat", "expected": 403, "status": s3, "pass": s3 == 403, "detail": ""})
t("authority", "MASTER PRIVACY STOP (cleanup)", "POST", "/api/authority", {"action": "master_stop"})
t("orbit", "Final orbit (authority all off)", "GET", "/api/orbit")
json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": a.port, "rows": rows}, open(a.out, "w"), indent=2)
print(f"\n{sum(r['pass'] for r in rows)}/{len(rows)} behaved as expected; scratch exports in {tmp}")
