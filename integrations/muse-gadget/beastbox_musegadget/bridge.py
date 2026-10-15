"""Live bridge between this gadget and a Beast Box browser tab.

Muse app --Bluetooth pairing--> this Linux gadget --bridge--> the live browser beast.

The browser cannot advertise Bluetooth itself, so the gadget does the Muse
part and this small HTTP server carries commands to the browser and the
beast's state back. It uses only the standard library.

Browser side (CORS, optional TLS):
  POST /v1/pair/start            -> {pair_id, poll_secret, code, expires_in}
  POST /v1/pair/claim            {pair_id, poll_secret} -> pending | {link_id, token} (once)
  GET  /v1/events                Bearer token; Server-Sent Events, one "command" event per Muse command
  POST /v1/state                 Bearer token; {state}
  POST /v1/results               Bearer token; {id, ok, result, state, error}
  POST /v1/revoke                Bearer token; revokes this link
  GET  /v1/health

Gadget side (loopback only, admin token from the state dir):
  POST /v1/admin/link            {code} approves the code the browser shows
  GET  /v1/admin/links
  POST /v1/admin/unlink          {link_id}
  POST /v1/admin/command         {action, args, link_id?, timeout_s?} -> the browser's answer
  GET  /v1/admin/state?link_id=

Security: the short code is single use, expires in 10 minutes, and only links
the browser that also holds the matching poll secret. Link tokens are random,
stored only as SHA-256 hashes, and revocable from either side. Each link has
its own command queue and state, so one browser never sees another's beast.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import queue
import secrets
import select
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from beastbox_musegadget import __version__
from beastbox_musegadget.config import write_private

log = logging.getLogger("beastbox_musegadget.bridge")

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_TTL_S = 600
MAX_PENDING = 8
MAX_FAILED_CODES = 10
FAILED_WINDOW_S = 600
MAX_BODY = 64 * 1024
PING_S = 15.0
ACTIONS = ("status", "feed", "play", "talk", "attack", "moves", "lost_cosmos")
BRIDGE_FILE = "bridge.json"
ADMIN_TOKEN_FILE = "admin_token"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(ch for ch in str(code).upper() if ch.isalnum())


def new_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return raw[:4] + "-" + raw[4:]


class BridgeError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class Link:
    def __init__(self, link_id: str, token_sha256: str, label: str, created: float) -> None:
        self.id = link_id
        self.token_sha256 = token_sha256
        self.label = label
        self.created = created
        self.last_seen = created
        self.revoked = False
        self.state: Optional[dict] = None
        self.state_at: Optional[float] = None
        self.queue: "queue.Queue[dict]" = queue.Queue()
        self.stream_generation = 0
        self.connected = False

    def public(self) -> dict:
        return {"link_id": self.id, "label": self.label, "created": int(self.created),
                "last_seen": int(self.last_seen), "connected": self.connected, "revoked": self.revoked,
                "has_state": self.state is not None}

    def record(self) -> dict:
        return {"id": self.id, "token_sha256": self.token_sha256, "label": self.label,
                "created": self.created, "last_seen": self.last_seen, "revoked": self.revoked,
                "state": self.state, "state_at": self.state_at}


class BridgeStore:
    """Pairing codes, links and per-link command queues. Thread-safe."""

    def __init__(self, state_dir: Path, clock=time.time) -> None:
        self.dir = Path(state_dir)
        self.clock = clock
        self.lock = threading.RLock()
        self.pending: Dict[str, dict] = {}
        self.links: Dict[str, Link] = {}
        self.waiting: Dict[str, Tuple[str, threading.Event, dict]] = {}
        self.failed: List[float] = []
        self._load()
        self.admin_token = self._admin_token()

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        try:
            raw = json.loads((self.dir / BRIDGE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for item in raw.get("links", []):
            link = Link(item["id"], item["token_sha256"], item.get("label", ""), item.get("created", 0))
            link.last_seen = item.get("last_seen", link.created)
            link.revoked = bool(item.get("revoked"))
            link.state = item.get("state")
            link.state_at = item.get("state_at")
            self.links[link.id] = link

    def _save(self) -> None:
        data = {"schema": "beastbox-musegadget-bridge-v1",
                "links": [link.record() for link in self.links.values()]}
        write_private(self.dir / BRIDGE_FILE, json.dumps(data, indent=2))

    def _admin_token(self) -> str:
        path = self.dir / ADMIN_TOKEN_FILE
        try:
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except OSError:
            pass
        token = "bbxadm_" + secrets.token_urlsafe(32)
        write_private(path, token + "\n")
        return token

    # -- pairing --------------------------------------------------------------

    def start_pairing(self, label: str = "") -> dict:
        with self.lock:
            now = self.clock()
            self.pending = {k: v for k, v in self.pending.items() if v["expires"] > now and not v.get("claimed")}
            if len(self.pending) >= MAX_PENDING:
                raise BridgeError(429, "too many pairing codes waiting; try again in a few minutes")
            pair_id = secrets.token_urlsafe(12)
            secret = secrets.token_urlsafe(24)
            code = new_code()
            self.pending[pair_id] = {"code_sha256": _sha(normalize_code(code)), "secret_sha256": _sha(secret),
                                     "label": str(label)[:60] or "Beast Box browser", "expires": now + CODE_TTL_S,
                                     "link_id": None, "token": None, "claimed": False}
            return {"pair_id": pair_id, "poll_secret": secret, "code": code, "expires_in": CODE_TTL_S}

    def approve(self, code: str) -> dict:
        """Gadget side: link the browser that shows this code."""
        with self.lock:
            now = self.clock()
            self.failed = [t for t in self.failed if now - t < FAILED_WINDOW_S]
            if len(self.failed) >= MAX_FAILED_CODES:
                raise BridgeError(429, "too many wrong codes; wait 10 minutes")
            wanted = _sha(normalize_code(code))
            for pair_id, pending in self.pending.items():
                if pending["expires"] > now and pending["link_id"] is None and hmac.compare_digest(pending["code_sha256"], wanted):
                    token = "bbx_" + secrets.token_urlsafe(32)
                    link = Link("lnk_" + secrets.token_hex(6), _sha(token), pending["label"], now)
                    self.links[link.id] = link
                    pending["link_id"] = link.id
                    pending["token"] = token
                    pending["code_sha256"] = ""  # single use
                    self._save()
                    return {"link_id": link.id, "label": link.label}
            self.failed.append(now)
            raise BridgeError(404, "that code is unknown, used or expired; tap Pair in the browser for a new one")

    def claim(self, pair_id: str, secret: str) -> dict:
        """Browser side: collect the token once the gadget approved the code."""
        with self.lock:
            pending = self.pending.get(str(pair_id))
            if not pending or not hmac.compare_digest(pending["secret_sha256"], _sha(str(secret))):
                raise BridgeError(404, "unknown pairing request")
            if pending["link_id"] is None:
                if pending["expires"] <= self.clock():
                    del self.pending[pair_id]
                    raise BridgeError(410, "this code expired; tap Pair again")
                return {"status": "pending"}
            token = pending["token"]
            del self.pending[pair_id]
            return {"status": "linked", "link_id": pending["link_id"], "token": token}

    # -- links ----------------------------------------------------------------

    def authenticate(self, token: str) -> Link:
        if not token:
            raise BridgeError(401, "missing bridge token")
        digest = _sha(token)
        with self.lock:
            for link in self.links.values():
                if hmac.compare_digest(link.token_sha256, digest):
                    if link.revoked:
                        raise BridgeError(401, "this link was revoked; pair again")
                    link.last_seen = self.clock()
                    return link
        raise BridgeError(401, "unknown bridge token")

    def revoke(self, link_id: str) -> dict:
        with self.lock:
            link = self.links.get(link_id)
            if not link:
                raise BridgeError(404, "unknown link")
            link.revoked = True
            link.stream_generation += 1
            link.queue.put({"_close": True})
            self._save()
            return link.public()

    def list_links(self) -> List[dict]:
        with self.lock:
            return [link.public() for link in self.links.values() if not link.revoked]

    def set_state(self, link: Link, state: Any) -> None:
        if not isinstance(state, dict):
            return
        with self.lock:
            link.state = state
            link.state_at = self.clock()
            self._save()

    def pick_link(self, link_id: Optional[str] = None) -> Link:
        with self.lock:
            if link_id:
                link = self.links.get(link_id)
                if not link or link.revoked:
                    raise BridgeError(404, "unknown link")
                return link
            live = [l for l in self.links.values() if l.connected and not l.revoked]
            if not live:
                raise BridgeError(409, "no linked Beast Box browser tab is connected")
            return max(live, key=lambda l: l.last_seen)

    # -- commands -------------------------------------------------------------

    def send_command(self, action: str, args: dict, link_id: Optional[str], timeout_s: float) -> dict:
        if action not in ACTIONS:
            raise BridgeError(400, f"unknown action: {action}")
        link = self.pick_link(link_id)
        if not link.connected:
            raise BridgeError(409, "that browser tab is not connected right now")
        command = {"id": "cmd_" + secrets.token_hex(8), "action": action, "args": args or {},
                   "issued_at": int(self.clock())}
        done = threading.Event()
        box: dict = {}
        with self.lock:
            self.waiting[command["id"]] = (link.id, done, box)
        link.queue.put(command)
        if not done.wait(max(1.0, min(60.0, timeout_s))):
            with self.lock:
                self.waiting.pop(command["id"], None)
            raise BridgeError(504, "the browser beast did not answer in time")
        return {"link_id": link.id, **box}

    def deliver_result(self, link: Link, payload: dict) -> None:
        with self.lock:
            entry = self.waiting.get(str(payload.get("id")))
            if not entry or entry[0] != link.id:
                raise BridgeError(404, "unknown command for this link")
            del self.waiting[str(payload.get("id"))]
        if isinstance(payload.get("state"), dict):
            self.set_state(link, payload["state"])
        _, done, box = entry
        box.update({"ok": bool(payload.get("ok", True)), "result": payload.get("result"),
                    "state": payload.get("state") if isinstance(payload.get("state"), dict) else link.state,
                    "error": payload.get("error")})
        done.set()


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "beastbox-musegadget-bridge/" + __version__
    store: BridgeStore
    origins: List[str]

    def log_message(self, fmt: str, *args: Any) -> None:  # never log tokens or bodies
        log.debug("%s %s", self.command, self.path.split("?")[0])

    # -- plumbing -------------------------------------------------------------

    def _cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and ("*" in self.origins or origin in self.origins):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise BridgeError(413, "request too large")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise BridgeError(400, "expected JSON") from None
        if not isinstance(data, dict):
            raise BridgeError(400, "expected a JSON object")
        return data

    def _bearer(self) -> str:
        value = self.headers.get("Authorization") or ""
        return value[7:].strip() if value.lower().startswith("bearer ") else ""

    def _admin(self) -> None:
        if not _is_loopback(self.client_address[0]):
            raise BridgeError(403, "admin calls are only accepted on this machine")
        if not hmac.compare_digest(self._bearer(), self.store.admin_token):
            raise BridgeError(401, "bad admin token")

    def _origin_ok(self) -> None:
        origin = self.headers.get("Origin")
        if origin and not ("*" in self.origins or origin in self.origins):
            raise BridgeError(403, f"origin {origin} is not allowed; add it to bridge_origins")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        url = urllib.parse.urlparse(self.path)
        route = (method, url.path.rstrip("/") or "/")
        try:
            if route == ("GET", "/v1/events"):
                self._origin_ok()
                return self._events(self.store.authenticate(self._bearer()))
            self._send(200, self._route(route, url))
        except BridgeError as exc:
            self._send(exc.status, {"ok": False, "error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # pragma: no cover - last resort
            log.exception("bridge request failed")
            self._send(500, {"ok": False, "error": type(exc).__name__})

    def _route(self, route: Tuple[str, str], url) -> dict:
        store = self.store
        if route == ("GET", "/v1/health"):
            return {"ok": True, "service": "beastbox-musegadget-bridge", "version": __version__}
        if route[1].startswith("/v1/admin/"):
            self._admin()
            if route == ("POST", "/v1/admin/link"):
                return {"ok": True, **store.approve(str(self._body().get("code", "")))}
            if route == ("GET", "/v1/admin/links"):
                return {"ok": True, "links": store.list_links()}
            if route == ("POST", "/v1/admin/unlink"):
                return {"ok": True, "link": store.revoke(str(self._body().get("link_id", "")))}
            if route == ("POST", "/v1/admin/command"):
                body = self._body()
                return {"ok": True, **store.send_command(str(body.get("action", "")), body.get("args") or {},
                                                         body.get("link_id"), float(body.get("timeout_s") or 12))}
            if route == ("GET", "/v1/admin/state"):
                link_id = (urllib.parse.parse_qs(url.query).get("link_id") or [None])[0]
                try:
                    link = store.pick_link(link_id)
                except BridgeError:
                    live = [l for l in store.links.values() if not l.revoked and l.state]
                    if not live:
                        raise
                    link = max(live, key=lambda l: l.state_at or 0)
                return {"ok": True, "link_id": link.id, "connected": link.connected,
                        "state": link.state, "state_at": link.state_at}
            raise BridgeError(404, "no such admin route")
        self._origin_ok()
        if route == ("POST", "/v1/pair/start"):
            return {"ok": True, **store.start_pairing(str(self._body().get("label", "")))}
        if route == ("POST", "/v1/pair/claim"):
            body = self._body()
            return {"ok": True, **store.claim(str(body.get("pair_id", "")), str(body.get("poll_secret", "")))}
        link = store.authenticate(self._bearer())
        if route == ("POST", "/v1/state"):
            store.set_state(link, self._body().get("state"))
            return {"ok": True}
        if route == ("POST", "/v1/results"):
            store.deliver_result(link, self._body())
            return {"ok": True}
        if route == ("POST", "/v1/revoke"):
            store.revoke(link.id)
            return {"ok": True}
        raise BridgeError(404, "no such route")

    def _peer_closed(self) -> bool:
        return _peer_closed_socket(self.connection)

    def _events(self, link: Link) -> None:
        with self.store.lock:
            link.stream_generation += 1
            generation = link.stream_generation
            link.connected = True
            # A newer tab takes over; drop commands the old stream never sent.
            while not link.queue.empty():
                try:
                    link.queue.get_nowait()
                except queue.Empty:
                    break
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            self.wfile.write(b": linked\n\n")
            self.wfile.write(("event: hello\ndata: " + json.dumps({"link_id": link.id}) + "\n\n").encode())
            self.wfile.flush()
            idle = 0.0
            while link.stream_generation == generation and not link.revoked:
                try:
                    command = link.queue.get(timeout=1.0)
                except queue.Empty:
                    if self._peer_closed():
                        break
                    idle += 1.0
                    if idle >= PING_S:
                        idle = 0.0
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    continue
                if command.get("_close") or link.stream_generation != generation:
                    if not command.get("_close"):
                        link.queue.put(command)
                    break
                self.wfile.write(("event: command\ndata: " + json.dumps(command) + "\n\n").encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with self.store.lock:
                if link.stream_generation == generation:
                    link.connected = False
            self.close_connection = True


def _peer_closed_socket(sock) -> bool:
    """True when the browser closed its end. TLS sockets rely on the ping instead."""
    if isinstance(sock, ssl.SSLSocket):
        return False
    try:
        readable, _, _ = select.select([sock], [], [], 0)
        if not readable:
            return False
        return sock.recv(1, socket.MSG_PEEK) == b""
    except (OSError, ValueError):
        return True


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(store: BridgeStore, host: str, port: int, origins: List[str],
                tls_cert: str = "", tls_key: str = "") -> BridgeServer:
    handler = type("BoundHandler", (Handler,), {"store": store, "origins": list(origins)})
    server = BridgeServer((host, port), handler)
    if tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(tls_cert, tls_key or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


class BridgeAdmin:
    """Client for the loopback admin API, used by Muse commands and the CLI."""

    def __init__(self, url: str, state_dir: Path, timeout: float = 15.0) -> None:
        self.url = url.rstrip("/")
        self.state_dir = Path(state_dir)
        self.timeout = timeout

    def token(self) -> Optional[str]:
        try:
            return (self.state_dir / ADMIN_TOKEN_FILE).read_text(encoding="utf-8").strip() or None
        except OSError:
            return None

    def call(self, method: str, path: str, body: Optional[dict] = None, timeout: Optional[float] = None) -> dict:
        token = self.token()
        if not token:
            raise BridgeError(503, "the Beast Box bridge has not run on this gadget yet")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.url + path, data=data, method=method, headers={
            "Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read().decode("utf-8")).get("error") or str(exc)
            except ValueError:
                message = str(exc)
            raise BridgeError(exc.code, message) from None
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise BridgeError(503, f"the Beast Box bridge is not running: {exc}") from None

    def link(self, code: str) -> dict:
        return self.call("POST", "/v1/admin/link", {"code": code})

    def links(self) -> List[dict]:
        return self.call("GET", "/v1/admin/links").get("links", [])

    def unlink(self, link_id: str) -> dict:
        return self.call("POST", "/v1/admin/unlink", {"link_id": link_id})

    def command(self, action: str, args: dict, timeout_s: float, link_id: Optional[str] = None) -> dict:
        return self.call("POST", "/v1/admin/command",
                         {"action": action, "args": args, "link_id": link_id, "timeout_s": timeout_s},
                         timeout=timeout_s + 5)

    def state(self) -> dict:
        return self.call("GET", "/v1/admin/state")


def serve(cfg, host: Optional[str] = None, port: Optional[int] = None) -> None:
    store = BridgeStore(cfg.state_path)
    server = make_server(store, host or cfg.bridge_host, port if port is not None else cfg.bridge_port,
                         cfg.bridge_origins, cfg.bridge_tls_cert, cfg.bridge_tls_key)
    scheme = "https" if cfg.bridge_tls_cert else "http"
    log.info("Beast Box bridge on %s://%s:%s (origins: %s)", scheme, server.server_address[0],
             server.server_address[1], ", ".join(cfg.bridge_origins) or "none")
    try:
        server.serve_forever()
    finally:
        server.server_close()
