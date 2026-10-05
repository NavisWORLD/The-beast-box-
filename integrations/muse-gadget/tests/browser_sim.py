"""A Python stand-in for a Beast Box browser tab, speaking the bridge protocol.

It holds a session like the browser's (beast, chat, train) and applies commands
with the same care rules, so tests can check that a Muse command changes the
"browser" beast. The JavaScript client has its own end-to-end test.
"""

import http.client
import json
import threading
import urllib.parse
import urllib.request

from beastbox_musegadget import beast as b
from beastbox_musegadget import moves


class FakeBrowser:
    def __init__(self, url, session, origin="http://localhost:3000"):
        self.url = url.rstrip("/")
        self.session = session
        self.origin = origin
        self.token = None
        self.attacks = []
        self.connected = threading.Event()
        self.thread = None
        self.conn = None

    def call(self, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json", "Origin": self.origin}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def pair(self, label="test tab"):
        status, data = self.call("POST", "/v1/pair/start", {"label": label})
        assert status == 200, data
        self.pending = data
        return data["code"]

    def claim(self):
        status, data = self.call("POST", "/v1/pair/claim",
                                 {"pair_id": self.pending["pair_id"], "poll_secret": self.pending["poll_secret"]})
        if data.get("status") == "linked":
            self.token = data["token"]
        return status, data

    def state(self):
        return b.summary(self.session)

    def handle(self, command):
        action, args = command["action"], command.get("args") or {}
        if action == "status":
            return {"ok": True, "result": self.state()}
        if action == "feed":
            return {"ok": True, "result": b.care_action(self.session, "feed")}
        if action == "play":
            return {"ok": True, "result": b.care_action(self.session, args.get("game") or "spark")}
        if action == "talk":
            reply = f"{b.shown_name(self.session['beast'])} (browser) hears: {args['message']}"
            b.remember_exchange(self.session, args["message"], reply)
            return {"ok": True, "result": {"reply": reply}}
        if action == "attack":
            move = moves.pick_attack(moves.build_moveset(self.session["beast"]["genome"]), len(self.attacks), "chat")
            self.attacks.append(move["name"])
            return {"ok": True, "result": {"move": move["name"], "animated": True}}
        return {"ok": False, "error": "unsupported in fake browser"}

    def start(self):
        parsed = urllib.parse.urlparse(self.url)
        self.conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=30)
        self.conn.request("GET", "/v1/events", headers={"Authorization": "Bearer " + self.token,
                                                        "Origin": self.origin})
        response = self.conn.getresponse()
        assert response.status == 200, response.status
        self.response = response
        self.call("POST", "/v1/state", {"state": self.state()}, self.token)
        self.thread = threading.Thread(target=self._loop, args=(response,), daemon=True)
        self.thread.start()
        return self

    def _loop(self, response):
        event, data = None, []
        try:
            for raw in response:
                line = raw.decode().rstrip("\n")
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data.append(line[5:].strip())
                elif line == "":
                    if event == "hello":
                        self.connected.set()
                    elif event == "command" and data:
                        command = json.loads("\n".join(data))
                        reply = self.handle(command)
                        self.call("POST", "/v1/results", {"id": command["id"], **reply, "state": self.state()},
                                  self.token)
                    event, data = None, []
        except (OSError, ValueError, AttributeError):
            pass  # the test closed the stream

    def stop(self):
        response = getattr(self, "response", None)
        if response is not None and response.fp is not None:
            try:
                response.fp.raw._sock.shutdown(2)
            except (AttributeError, OSError):
                pass
            response.close()
        if self.conn:
            self.conn.close()
