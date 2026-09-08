"""COSMIC.CYPHER owner UI over the canonical durable Beast Box runtime.

The browser owns camera/microphone device handles. The Python side accepts only
explicit bounded events and never grants those host capabilities to model output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from typing import Any
import urllib.parse

from .durable import DurableRuntime
from .optional_resources import ResourceUnavailable, quantum_event
from .product_services import AuthoritySession, ProductService
from .providers import CompatibleChatProvider, LocalOllamaProvider, ReferenceTextProvider, TextProvider

_MAX_REQUEST_BYTES = 1024 * 1024
_ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


def _is_loopback_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_bind_host(host: str) -> str:
    if host == "localhost":
        return host
    try:
        if ipaddress.ip_address(host).is_loopback:
            return host
    except ValueError:
        pass
    raise ValueError("cosmic UI must bind to a loopback host")


@dataclass(frozen=True)
class ProviderProfile:
    kind: str = "reference"
    model: str = "COSMOS reference"
    base_url: str = ""
    allow_remote: bool = False
    api_key_env: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProviderProfile:
        if not isinstance(value, dict):
            raise ValueError("provider profile must be an object")
        allowed = {"kind", "model", "base_url", "allow_remote", "api_key_env"}
        if set(value) - allowed:
            raise ValueError("provider profile contains unsupported fields")
        kind = value.get("kind", "reference")
        model = value.get("model", "COSMOS reference")
        base_url = value.get("base_url", "")
        allow_remote = value.get("allow_remote", False)
        api_key_env = value.get("api_key_env")
        if kind not in {"reference", "ollama", "compatible"}:
            raise ValueError("provider kind must be reference, ollama, or compatible")
        if not isinstance(model, str) or not model.strip() or len(model) > 256:
            raise ValueError("provider model must contain 1..256 characters")
        if not isinstance(base_url, str) or len(base_url) > 2048:
            raise ValueError("provider base URL is invalid")
        if type(allow_remote) is not bool:
            raise ValueError("allow_remote must be boolean")
        if api_key_env is not None and (
            not isinstance(api_key_env, str) or _ENV_NAME_RE.fullmatch(api_key_env) is None
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if kind == "ollama" and not base_url:
            base_url = "http://127.0.0.1:11434"
        if kind == "compatible" and not base_url:
            base_url = "http://127.0.0.1:1234/v1"
        profile = cls(kind, model.strip(), base_url, allow_remote, api_key_env)
        profile.make_provider()
        return profile

    @property
    def remote(self) -> bool:
        return self.kind == "compatible" and not _is_loopback_url(self.base_url)

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.kind, self.model, self.base_url

    def make_provider(self) -> TextProvider:
        if self.kind == "reference":
            return ReferenceTextProvider(prefix=self.model)
        if self.kind == "ollama":
            return LocalOllamaProvider(model=self.model, base_url=self.base_url)
        return CompatibleChatProvider(
            model=self.model,
            base_url=self.base_url,
            allow_remote=self.allow_remote,
            api_key_env=self.api_key_env,
        )


def _provider_path(root: Path) -> Path:
    return root / "cosmic-provider.json"


def save_provider_profile(root: Path, profile: ProviderProfile) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = _provider_path(root)
    if path.is_symlink():
        raise ValueError("provider settings cannot be a symlink")
    payload = json.dumps(asdict(profile), sort_keys=True, indent=2) + "\n"
    fd, name = tempfile.mkstemp(prefix=".cosmic-provider-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_provider_profile(root: Path) -> ProviderProfile:
    path = _provider_path(root)
    if not path.exists():
        return ProviderProfile()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("provider settings must be a small regular file")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProviderProfile.from_dict(raw)


class CosmicApp:
    """Testable product controller; HTTP is only a transport adapter around this."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        if self.root.is_symlink():
            raise ValueError("cosmic runtime root cannot be a symlink")
        self.authority = AuthoritySession()
        self.service = ProductService(self.root, authority=self.authority)
        self.profile = load_provider_profile(self.root)

    def _provider(self, profile: ProviderProfile | None = None) -> TextProvider:
        selected = profile or self.profile
        if selected.remote and not self.authority.allowed("cloud"):
            raise PermissionError("cloud authority required")
        return selected.make_provider()

    def _runtime(self, profile: ProviderProfile | None = None) -> DurableRuntime:
        return DurableRuntime(self.root, self._provider(profile))

    def _set_profile(self, raw: dict[str, Any]) -> ProviderProfile:
        profile = ProviderProfile.from_dict(raw)
        self._provider(profile)
        save_provider_profile(self.root, profile)
        self.profile = profile
        return profile

    def _authority(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        action = body.get("action")
        if action == "master_stop" and set(body) == {"action"}:
            stopped = self.authority.master_privacy_stop()
            return 200, {"stopped": stopped, "authority": self.authority.snapshot()}
        if action not in {"grant", "revoke"} or set(body) != {"action", "name"}:
            return 400, {"error": "invalid authority request"}
        name = body.get("name")
        if not isinstance(name, str):
            return 400, {"error": "invalid authority name"}
        try:
            if action == "grant":
                self.authority.grant(name)
            else:
                self.authority.revoke(name)
        except ValueError as exc:
            return 400, {"error": str(exc)}
        return 200, {"authority": self.authority.snapshot()}

    def _chat(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        text = body.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8192:
            return 400, {"error": "chat text must contain 1..8192 characters"}
        previous = self.profile.identity
        profile = self.profile
        if "provider" in body:
            raw = body.get("provider")
            if not isinstance(raw, dict):
                return 400, {"error": "provider must be an object"}
            profile = self._set_profile(raw)
        runtime = self._runtime(profile)
        try:
            before = runtime.inspect()
            result = runtime.respond(text)
            after = runtime.inspect()
        finally:
            runtime.close()
        return 200, {
            "result": result,
            "runtime": after,
            "brain_changed": previous != profile.identity,
            "substrate_preserved": before["system_id"] == after["system_id"],
            "provider": asdict(profile),
        }

    def _event(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        modality = body.get("modality")
        event = body.get("event")
        authority_name = {"camera": "camera", "microphone": "microphone", "sensor": "sensors"}.get(modality)
        if authority_name is None or not isinstance(event, dict) or set(body) != {"modality", "event"}:
            return 400, {"error": "invalid bounded event request"}
        if not self.authority.allowed(authority_name):
            return 403, {"error": f"{authority_name} authority required"}
        runtime = self._runtime()
        try:
            result = runtime.respond_event(event)
            inspection = runtime.inspect()
        finally:
            runtime.close()
        return 200, {"result": result, "runtime": inspection, "raw_media_transmitted": False}

    def _quantum(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self.authority.allowed("quantum_live"):
            return 403, {"error": "quantum live authority required"}
        if set(body) != {"provider", "shots"}:
            return 400, {"error": "invalid quantum request"}
        provider = body.get("provider")
        shots = body.get("shots")
        try:
            event = quantum_event(provider, shots=shots, allow_live=True)
            runtime = self._runtime()
            try:
                result = runtime.respond_event(event)
            finally:
                runtime.close()
        except ResourceUnavailable as exc:
            return 503, {"error": str(exc)}
        except (ValueError, TypeError):
            return 400, {"error": "invalid quantum request"}
        return 200, {"event": event, "result": result, "experimental": True}

    def dispatch(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        data = body or {}
        try:
            if method == "GET" and path == "/api/orbit":
                return 200, self.service.orbit_snapshot()
            if method == "GET" and path == "/api/memory":
                return 200, {"records": self.service.memory_records()}
            if method == "GET" and path == "/api/trace":
                return 200, {"events": self.service.trace_events()}
            if method == "GET" and path == "/api/provider":
                return 200, {"profile": asdict(self.profile), "secret_storage": "ENVIRONMENT_REFERENCE_ONLY"}
            if method == "GET" and path == "/api/resources":
                return 200, {"resources": self.service.resource_status()}
            if method == "POST" and path == "/api/authority":
                return self._authority(data)
            if method == "POST" and path == "/api/provider":
                profile = self._set_profile(data)
                return 200, {"profile": asdict(profile), "secret_storage": "ENVIRONMENT_REFERENCE_ONLY"}
            if method == "POST" and path == "/api/chat":
                return self._chat(data)
            if method == "POST" and path == "/api/event":
                return self._event(data)
            if method == "POST" and path == "/api/quantum":
                return self._quantum(data)
            return 404, {"error": "not found"}
        except PermissionError as exc:
            return 403, {"error": str(exc)}
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
            return 400, {"error": "request rejected; no fallback was performed"}


def render_cosmic_ui(session_token: str = "local-test-session") -> str:
    token = json.dumps(session_token)
    return _COSMIC_HTML.replace("__BEAST_SESSION__", token)


_COSMIC_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beast Box · COSMIC.CYPHER</title>
<style>
:root{color-scheme:dark;--bg:#05070c;--panel:#0b1020e8;--panel2:#10182a;--line:#27324b;--text:#edf3ff;--muted:#92a0b8;--pulse:#72d8d1;--warn:#f5c76a;--danger:#ff7b83;--ok:#89e6a2}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 72% 18%,#14203d 0,#080d18 24%,var(--bg) 58%);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.18;background-image:radial-gradient(#dce9ff 1px,transparent 1px);background-size:43px 43px;mask-image:linear-gradient(to bottom,#000,transparent 70%)}
button,input,select,textarea{font:inherit}button{border:1px solid var(--line);background:#121b2d;color:var(--text);padding:.58rem .8rem;border-radius:9px;cursor:pointer}button:hover,button:focus-visible{border-color:#7181a5;outline:none}button.danger{border-color:#6c313c;color:#ffd9de;background:#281117}.app{display:grid;grid-template-columns:220px 1fr;min-height:100vh}.rail{position:sticky;top:0;height:100vh;padding:18px 14px;border-right:1px solid var(--line);background:#060a12e8;backdrop-filter:blur(16px);overflow:auto}.brand{font-weight:800;letter-spacing:.12em;font-size:16px;margin:4px 8px 18px}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.2em;margin-top:4px}.nav button{width:100%;text-align:left;margin:2px 0;background:transparent;border-color:transparent;color:#b8c4d8}.nav button.active{color:white;background:#111a2b;border-color:#26334e}.main{padding:24px;max-width:1500px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:20px}.eyebrow{color:var(--pulse);letter-spacing:.16em;font-size:11px;font-weight:700}.statusbar{display:flex;flex-wrap:wrap;gap:8px}.pill{border:1px solid var(--line);border-radius:999px;padding:5px 9px;color:var(--muted);background:#0b1220}.pill.live{color:#d8fff7;border-color:#39736f}.view{display:none}.view.active{display:block}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{grid-column:span 4;background:linear-gradient(150deg,#101829e8,#090e18e8);border:1px solid var(--line);border-radius:14px;padding:15px;min-height:110px;box-shadow:0 18px 50px #0005}.wide{grid-column:span 8}.full{grid-column:1/-1}.half{grid-column:span 6}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em}.value{font-size:21px;font-weight:720;margin-top:7px;word-break:break-word}.sub{color:var(--muted);margin-top:5px}.pulse{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--pulse);box-shadow:0 0 14px var(--pulse);animation:pulse 1.8s ease-in-out infinite}@keyframes pulse{50%{opacity:.3;transform:scale(.75)}}.flow{display:flex;align-items:center;justify-content:space-between;gap:7px;flex-wrap:wrap}.node{padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:#0b1323}.arrow{color:#64728a}.chatlog{height:410px;overflow:auto;padding:12px;border:1px solid var(--line);background:#060a12;border-radius:12px}.msg{max-width:82%;padding:10px 12px;margin:8px 0;border-radius:12px;background:#111a2c;white-space:pre-wrap}.msg.user{margin-left:auto;background:#17223a}.composer{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:10px}.composer textarea{min-height:74px}.field,textarea,select,input{width:100%;border:1px solid var(--line);background:#080d17;color:var(--text);border-radius:9px;padding:9px}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.camera{width:100%;max-height:390px;background:#000;border-radius:12px;border:1px solid var(--line)}canvas.scope{width:100%;height:120px;background:#05070c;border:1px solid var(--line);border-radius:10px}.warning{border-left:3px solid var(--warn);padding:8px 10px;background:#2b210f66;color:#f8e2ae}.privacy{border:1px solid #62323d;background:#241117;border-radius:14px;padding:13px;margin-bottom:14px}.authority-row{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid #1d2739}.authority-row:last-child{border:0}pre{white-space:pre-wrap;word-break:break-word;background:#050811;border:1px solid var(--line);padding:12px;border-radius:10px;max-height:460px;overflow:auto}.trace-node{border-left:2px solid #405d79;padding:6px 10px;margin:7px 0}.hidden{display:none}@media(max-width:900px){.app{grid-template-columns:1fr}.rail{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--line)}.nav{display:flex;overflow:auto}.nav button{width:auto;white-space:nowrap}.card,.wide,.half{grid-column:1/-1}.main{padding:15px}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style></head><body><div class="app"><aside class="rail"><div class="brand">BEAST BOX<small>COSMIC.CYPHER</small></div><nav class="nav" id="nav">
<button data-view="orbit" class="active">ORBIT</button><button data-view="brain">BRAIN</button><button data-view="bay">BRAIN BAY</button><button data-view="vision">VISION</button><button data-view="listen">LISTEN</button><button data-view="voice">VOICE</button><button data-view="reality">REALITY</button><button data-view="memory">MEMORY VAULT</button><button data-view="trace">SYNAPSE TRACE</button><button data-view="files">FILES</button><button data-view="workspace">WORKSPACE</button><button data-view="qbay">Q-BAY</button><button data-view="connections">CONNECTIONS</button><button data-view="authority">AUTHORITY</button><button data-view="settings">SETTINGS</button></nav></aside>
<main class="main"><div class="top"><div><div class="eyebrow">OWNER-CONTROLLED PERSISTENT SUBSTRATE</div><h1 style="margin:.2rem 0">Swap the brain. Keep the story.</h1></div><div class="statusbar"><span class="pill" id="providerPill">provider —</span><span class="pill" id="substratePill"><span class="pulse"></span> substrate</span><span class="pill" id="cloudPill">local boundary</span></div></div>
<div class="privacy"><b>MASTER PRIVACY</b> · stop camera, microphone, sensors, cloud and live experimental jobs. <button class="danger" id="masterStop">STOP ALL LIVE FLOWS</button></div>
<section id="orbit" class="view active"><div class="grid"><div class="card"><div class="label">Active brain</div><div class="value" id="brainValue">—</div><div class="sub" id="providerValue">—</div></div><div class="card"><div class="label">System ID</div><div class="value" style="font-size:13px" id="systemId">—</div></div><div class="card"><div class="label">Memory records</div><div class="value" id="memoryCount">—</div></div><div class="card"><div class="label">Checkpoint</div><div class="value" style="font-size:13px" id="checkpoint">—</div></div><div class="card"><div class="label">Authority grants</div><div class="value" id="grantCount">0</div></div><div class="card"><div class="label">Q-Bay</div><div class="value">EXPERIMENTAL</div><div class="sub">configuration ≠ live validation</div></div><div class="card full"><div class="label">SYSTEM MAP</div><div class="flow" style="margin-top:13px"><span class="node">USER</span><span class="arrow">→</span><span class="node">SENSORS / FILES / WORKSPACE</span><span class="arrow">→</span><span class="node">CNS / CST STATE</span><span class="arrow">→</span><span class="node">MEMORY + R12</span><span class="arrow">→</span><span class="node">MODEL PROVIDER</span><span class="arrow">→</span><span class="node">POLICY / TOOLS</span><span class="arrow">→ WORLD ↺</span></div></div></div></section>
<section id="brain" class="view"><div class="grid"><div class="card full"><div class="label">BRAIN · CONVERSATION</div><div id="swapBanner" class="warning hidden" style="margin:10px 0">BRAIN CHANGED · SUBSTRATE PRESERVED</div><div class="chatlog" id="chatlog"></div><div class="composer"><textarea id="chatText" placeholder="Talk to your system…"></textarea><button id="sendChat">SEND</button></div><div class="sub">Every turn reports the exact configured provider. No silent inference fallback.</div></div></div></section>
<section id="bay" class="view"><div class="grid"><div class="card full"><div class="label">BRAIN BAY · PROVIDER CLOCK-IN</div><div class="fields" style="margin-top:12px"><label>Kind<select id="providerKind"><option value="reference">Reference fixture</option><option value="ollama">Ollama</option><option value="compatible">OpenAI-compatible</option></select></label><label>Model<input id="providerModel" value="COSMOS reference"></label><label>Base URL<input id="providerUrl" placeholder="http://127.0.0.1:11434"></label><label>API key environment variable<input id="providerEnv" placeholder="OPTIONAL_ENV_NAME"></label></div><label style="display:block;margin-top:10px"><input style="width:auto" type="checkbox" id="allowRemote"> Explicitly allow a configured HTTPS remote endpoint</label><button id="saveProvider" style="margin-top:10px">CLOCK IN BRAIN</button><div class="sub">Credential values are not accepted here. The profile stores only an environment-variable name.</div></div></div></section>
<section id="vision" class="view"><div class="grid"><div class="card wide"><div class="label">VISION · LOCAL CAMERA</div><video id="cameraPreview" class="camera" autoplay muted playsinline></video><canvas id="cameraCanvas" class="hidden"></canvas><div style="margin-top:10px"><button id="cameraOn">ENABLE CAMERA</button> <button id="cameraSample">SAMPLE BOUNDED OBSERVATION</button> <button id="cameraOff">STOP CAMERA</button></div></div><div class="card"><div class="label">Boundary</div><div class="value" id="cameraStatus">OFF</div><div class="sub">Camera-derived features are not vision understanding. Raw frames stay in this browser in the current implementation.</div></div></div></section>
<section id="listen" class="view"><div class="grid"><div class="card wide"><div class="label">LISTEN · LOCAL MICROPHONE</div><canvas id="audioScope" class="scope" width="900" height="180"></canvas><div style="margin-top:10px"><button id="micOn">ENABLE MIC</button> <button id="micSample">SEND FEATURE SAMPLE</button> <button id="micOff">STOP MIC</button></div></div><div class="card"><div class="label">LIVE MIC</div><div class="value" id="micStatus">OFF</div><div class="sub">Raw continuous audio is never posted by this UI. RMS/spectrum-derived bounded features require explicit microphone authority.</div></div></div></section>
<section id="voice" class="view"><div class="grid"><div class="card full"><div class="label">VOICE · LOCAL BROWSER TTS</div><textarea id="voiceText" placeholder="Text to speak"></textarea><button id="speak">SPEAK LOCALLY</button> <button id="stopSpeak">STOP VOICE</button><div class="sub">Uses browser speechSynthesis. Authorized custom voice cloning is NOT ESTABLISHED in the current validated product path.</div></div></div></section>
<section id="reality" class="view"><div class="grid"><div class="card full"><div class="label">REALITY · SENSOR / BIO LOOP</div><div class="warning">Current browser surface accepts bounded normalized sensor events. Physical Reality Probe hardware remains separate physical validation. Bio observations are nonmedical.</div><pre id="realityOut">No live device stream connected.</pre></div></div></section>
<section id="memory" class="view"><div class="grid"><div class="card full"><div class="label">MEMORY VAULT</div><button id="refreshMemory">REFRESH</button><pre id="memoryOut">—</pre></div></div></section>
<section id="trace" class="view"><div class="grid"><div class="card full"><div class="label">SYNAPSE TRACE · SYSTEM EVENTS, NOT PRIVATE CHAIN-OF-THOUGHT</div><button id="refreshTrace">REFRESH</button><div id="traceOut"></div></div></div></section>
<section id="files" class="view"><div class="grid"><div class="card full"><div class="label">FILES · TEMPORARY LOCAL INSPECTION</div><input type="file" id="fileInput" multiple><pre id="fileOut">Choose files. This browser inspection does not silently make them permanent memory.</pre></div></div></section>
<section id="workspace" class="view"><div class="grid"><div class="card full"><div class="label">WORKSPACE</div><div class="warning">The backend contains a confined read-only WorkspaceGrant, but this browser shell does not auto-open any local directory. Repository write remains a separate authority grant.</div></div></div></section>
<section id="qbay" class="view"><div class="grid"><div class="card half"><div class="label">Q-BAY · IBM / AZURE</div><button id="refreshResources">CHECK CONFIGURATION</button><pre id="resourcesOut">—</pre></div><div class="card half"><div class="label">LIVE EXPERIMENTAL JOB</div><select id="qProvider"><option value="ibm">IBM hardware adapter</option><option value="azure">Azure IonQ simulator</option></select><input id="qShots" type="number" min="1" max="1024" value="128"><button id="qRun">SUBMIT AUTHORIZED JOB</button><div class="sub">Requires a separate quantum_live authority grant. Quantum provenance ≠ quantum advantage.</div></div></div></section>
<section id="connections" class="view"><div class="grid"><div class="card full"><div class="label">CONNECTIONS</div><pre id="connectionsOut">IBM / Azure status reports configuration only. Ollama and compatible model endpoints are configured in Brain Bay. Secret values remain host configuration.</pre></div></div></section>
<section id="authority" class="view"><div class="grid"><div class="card full"><div class="label">AUTHORITY · DOES NOT TRAVEL WITH MEMORY</div><div id="authorityList"></div></div></div></section>
<section id="settings" class="view"><div class="grid"><div class="card full"><div class="label">SETTINGS</div><div class="sub">Basic mode: chat, camera, mic, model, memory, voice. Advanced: sensor/workspace/storage/authority. Lab: CNS/R12/Q-Bay/provenance. This surface keeps experimental labels visible rather than hiding them.</div></div></div></section>
</main></div><script>
const sessionKey=__BEAST_SESSION__;let orbit=null,cameraStream=null,audioStream=null,audioCtx=null,analyser=null,lastAnswer='';
async function api(path,method='GET',body=null){const opt={method,headers:{'X-Beast-Session':sessionKey}};if(body!==null){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body)}const r=await fetch(path,opt);let j={};try{j=await r.json()}catch{}if(!r.ok)throw new Error(j.error||('HTTP '+r.status));return j}
function show(view){document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id===view));document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('active',x.dataset.view===view))}document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>show(b.dataset.view));
function addMsg(role,text){const d=document.createElement('div');d.className='msg '+role;d.textContent=text;document.getElementById('chatlog').appendChild(d);d.scrollIntoView({block:'end'})}
async function loadOrbit(){orbit=await api('/api/orbit');const r=orbit.runtime;document.getElementById('systemId').textContent=r.system_id;document.getElementById('checkpoint').textContent=r.checkpoint_sha256.slice(0,20)+'…';document.getElementById('memoryCount').textContent=r.memory.memories;const grants=Object.values(orbit.authority).filter(Boolean).length;document.getElementById('grantCount').textContent=grants;renderAuthority(orbit.authority);const p=await api('/api/provider');document.getElementById('brainValue').textContent=p.profile.model;document.getElementById('providerValue').textContent=p.profile.kind;document.getElementById('providerPill').textContent=p.profile.kind+' · '+p.profile.model;document.getElementById('cloudPill').textContent=orbit.authority.cloud?'CLOUD AUTHORIZED':'LOCAL BOUNDARY'}
function renderAuthority(a){const box=document.getElementById('authorityList');box.innerHTML='';Object.entries(a).forEach(([name,on])=>{const row=document.createElement('div');row.className='authority-row';const s=document.createElement('span');s.textContent=name+' · '+(on?'GRANTED':'DENIED');const b=document.createElement('button');b.textContent=on?'REVOKE':'GRANT';b.onclick=async()=>{await api('/api/authority','POST',{action:on?'revoke':'grant',name});await loadOrbit()};row.append(s,b);box.appendChild(row)})}
document.getElementById('masterStop').onclick=async()=>{stopCamera();stopMic();speechSynthesis.cancel();await api('/api/authority','POST',{action:'master_stop'});await loadOrbit()};
document.getElementById('sendChat').onclick=async()=>{const t=document.getElementById('chatText');const text=t.value.trim();if(!text)return;addMsg('user',text);t.value='';try{const j=await api('/api/chat','POST',{text});lastAnswer=j.result.response;addMsg('assistant',lastAnswer);document.getElementById('voiceText').value=lastAnswer;document.getElementById('swapBanner').classList.toggle('hidden',!j.brain_changed);await loadOrbit()}catch(e){addMsg('assistant','Request failed: '+e.message)}};
document.getElementById('saveProvider').onclick=async()=>{const body={kind:document.getElementById('providerKind').value,model:document.getElementById('providerModel').value,base_url:document.getElementById('providerUrl').value,allow_remote:document.getElementById('allowRemote').checked,api_key_env:document.getElementById('providerEnv').value||null};try{await api('/api/provider','POST',body);await loadOrbit();show('brain')}catch(e){alert(e.message)}};
async function grant(name){await api('/api/authority','POST',{action:'grant',name});await loadOrbit()}
async function revoke(name){try{await api('/api/authority','POST',{action:'revoke',name})}catch{}await loadOrbit()}
async function startCamera(){if(cameraStream)return;await grant('camera');cameraStream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});document.getElementById('cameraPreview').srcObject=cameraStream;document.getElementById('cameraStatus').textContent='CAMERA LIVE'}
function stopCamera(){if(cameraStream){cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null}document.getElementById('cameraPreview').srcObject=null;document.getElementById('cameraStatus').textContent='OFF';revoke('camera')}
async function sampleCamera(){if(!cameraStream)throw new Error('camera is off');const v=document.getElementById('cameraPreview'),c=document.getElementById('cameraCanvas');c.width=Math.max(1,v.videoWidth||320);c.height=Math.max(1,v.videoHeight||180);const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(v,0,0,c.width,c.height);const d=x.getImageData(0,0,c.width,c.height).data;let sum=0,n=0;const stride=Math.max(4,Math.floor(d.length/4096/4)*4);for(let i=0;i<d.length;i+=stride){sum+=(d[i]+d[i+1]+d[i+2])/(3*255);n++}const mean=n?sum/n:0;return api('/api/event','POST',{modality:'camera',event:{schema:'sensor-event-v1',source:'software-event',text:JSON.stringify({source:'browser-camera',mode:'local-brightness-summary',mean}),features:[mean*2-1]}})}
document.getElementById('cameraOn').onclick=()=>startCamera().catch(e=>alert(e.message));document.getElementById('cameraOff').onclick=stopCamera;document.getElementById('cameraSample').onclick=()=>sampleCamera().catch(e=>alert(e.message));
function drawAudio(){if(!analyser)return;const a=new Uint8Array(analyser.fftSize);analyser.getByteTimeDomainData(a);const c=document.getElementById('audioScope'),x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);x.beginPath();for(let i=0;i<a.length;i++){const px=i/(a.length-1)*c.width,py=a[i]/255*c.height;i?x.lineTo(px,py):x.moveTo(px,py)}x.strokeStyle='#72d8d1';x.stroke();requestAnimationFrame(drawAudio)}
async function startMic(){if(audioStream)return;await grant('microphone');audioStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});audioCtx=new AudioContext();analyser=audioCtx.createAnalyser();analyser.fftSize=1024;audioCtx.createMediaStreamSource(audioStream).connect(analyser);document.getElementById('micStatus').textContent='MIC LIVE';drawAudio()}
function stopMic(){if(audioStream){audioStream.getTracks().forEach(t=>t.stop());audioStream=null}if(audioCtx){audioCtx.close();audioCtx=null}analyser=null;document.getElementById('micStatus').textContent='OFF';revoke('microphone')}
async function sampleMic(){if(!analyser)throw new Error('microphone is off');const a=new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(a);let s=0;for(const v of a)s+=v*v;const rms=Math.sqrt(s/a.length);const bounded=Math.max(-1,Math.min(1,rms*2-1));return api('/api/event','POST',{modality:'microphone',event:{schema:'sensor-event-v1',source:'software-event',text:JSON.stringify({source:'browser-microphone',mode:'local-rms-feature',rms}),features:[bounded]}})}
document.getElementById('micOn').onclick=()=>startMic().catch(e=>alert(e.message));document.getElementById('micOff').onclick=stopMic;document.getElementById('micSample').onclick=()=>sampleMic().catch(e=>alert(e.message));
document.getElementById('speak').onclick=()=>{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(document.getElementById('voiceText').value);speechSynthesis.speak(u)};document.getElementById('stopSpeak').onclick=()=>speechSynthesis.cancel();
document.getElementById('refreshMemory').onclick=async()=>document.getElementById('memoryOut').textContent=JSON.stringify(await api('/api/memory'),null,2);
document.getElementById('refreshTrace').onclick=async()=>{const j=await api('/api/trace'),o=document.getElementById('traceOut');o.innerHTML='';j.events.forEach(e=>{const d=document.createElement('div');d.className='trace-node';d.textContent='#'+e.sequence+' · '+e.stages.join(' → ')+' · '+(e.model.provider||'system');o.appendChild(d)})};
document.getElementById('refreshResources').onclick=async()=>document.getElementById('resourcesOut').textContent=JSON.stringify(await api('/api/resources'),null,2);
document.getElementById('qRun').onclick=async()=>{if(!confirm('Submit one explicitly authorized experimental quantum workload?'))return;try{await grant('quantum_live');const j=await api('/api/quantum','POST',{provider:document.getElementById('qProvider').value,shots:Number(document.getElementById('qShots').value)});document.getElementById('resourcesOut').textContent=JSON.stringify(j,null,2)}catch(e){alert(e.message)}};
document.getElementById('fileInput').onchange=async ev=>{const out=[];for(const f of ev.target.files){const b=await f.arrayBuffer(),h=await crypto.subtle.digest('SHA-256',b);out.push({name:f.name,bytes:f.size,sha256:[...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join(''),persistence:'TEMPORARY_BROWSER_ONLY'})}document.getElementById('fileOut').textContent=JSON.stringify(out,null,2)};
window.addEventListener('beforeunload',()=>{if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());if(audioStream)audioStream.getTracks().forEach(t=>t.stop())});loadOrbit().catch(e=>addMsg('assistant','Runtime unavailable: '+e.message));
</script></body></html>'''


class _CosmicHandler(BaseHTTPRequestHandler):
    server_version = "BeastBoxCosmic/1"

    @property
    def app(self) -> CosmicApp:
        return self.server.cosmic_app  # type: ignore[attr-defined,no-any-return]

    @property
    def session_token(self) -> str:
        return self.server.session_token  # type: ignore[attr-defined,no-any-return]

    def _headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]")
        try:
            validate_bind_host(host)
            return True
        except ValueError:
            return False

    def _json(self, status: int, value: dict[str, Any]) -> None:
        raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if not self._host_ok():
            self._json(400, {"error": "invalid host"})
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            raw = render_cosmic_ui(self.session_token).encode("utf-8")
            self._headers(200, "text/html; charset=utf-8")
            self.wfile.write(raw)
            return
        status, value = self.app.dispatch("GET", path)
        self._json(status, value)

    def do_POST(self) -> None:
        if not self._host_ok():
            self._json(400, {"error": "invalid host"})
            return
        if not secrets.compare_digest(self.headers.get("X-Beast-Session", ""), self.session_token):
            self._json(403, {"error": "invalid session"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= _MAX_REQUEST_BYTES:
                raise ValueError
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON request"})
            return
        path = urllib.parse.urlparse(self.path).path
        status, value = self.app.dispatch("POST", path, body)
        self._json(status, value)

    def log_message(self, format: str, *args: Any) -> None:
        return


class CosmicHTTPServer(ThreadingHTTPServer):
    cosmic_app: CosmicApp
    session_token: str


def serve(root: str | Path, host: str = "127.0.0.1", port: int = 8081) -> None:
    bind = validate_bind_host(host)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("port must be an integer in 1..65535")
    server = CosmicHTTPServer((bind, port), _CosmicHandler)
    server.cosmic_app = CosmicApp(root)
    server.session_token = secrets.token_urlsafe(32)
    try:
        server.serve_forever()
    finally:
        server.server_close()
