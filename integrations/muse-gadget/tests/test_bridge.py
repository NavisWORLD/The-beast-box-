import copy
import threading
import time

import pytest

from browser_sim import FakeBrowser
from conftest import FIXTURES  # noqa: F401

from beastbox_musegadget import bridge, commands
from beastbox_musegadget.bridge import BridgeAdmin, BridgeError, BridgeStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


# -- store ----------------------------------------------------------------------


def test_code_is_single_use_and_only_the_secret_holder_gets_the_token(tmp_path):
    store = BridgeStore(tmp_path)
    pending = store.start_pairing("tab")
    assert len(pending["code"]) == 9 and pending["code"][4] == "-"
    assert store.claim(pending["pair_id"], pending["poll_secret"]) == {"status": "pending"}
    linked = store.approve(pending["code"].lower().replace("-", " "))
    with pytest.raises(BridgeError):
        store.claim(pending["pair_id"], "not-the-secret")
    got = store.claim(pending["pair_id"], pending["poll_secret"])
    assert got["status"] == "linked" and got["link_id"] == linked["link_id"] and got["token"].startswith("bbx_")
    with pytest.raises(BridgeError):  # token is handed out once
        store.claim(pending["pair_id"], pending["poll_secret"])
    with pytest.raises(BridgeError) as err:  # code is single use
        store.approve(pending["code"])
    assert err.value.status == 404
    saved = (tmp_path / "bridge.json").read_text()
    assert got["token"] not in saved and pending["code"] not in saved
    assert (tmp_path / "bridge.json").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "admin_token").stat().st_mode & 0o777 == 0o600


def test_codes_expire(tmp_path):
    clock = Clock()
    store = BridgeStore(tmp_path, clock=clock)
    pending = store.start_pairing()
    clock.now += bridge.CODE_TTL_S + 1
    with pytest.raises(BridgeError):
        store.approve(pending["code"])
    with pytest.raises(BridgeError) as err:
        store.claim(pending["pair_id"], pending["poll_secret"])
    assert err.value.status == 410


def test_wrong_codes_lock_out(tmp_path):
    clock = Clock()
    store = BridgeStore(tmp_path, clock=clock)
    pending = store.start_pairing()
    for _ in range(bridge.MAX_FAILED_CODES):
        with pytest.raises(BridgeError):
            store.approve("ZZZZ-ZZZZ")
    with pytest.raises(BridgeError) as err:
        store.approve(pending["code"])
    assert err.value.status == 429
    clock.now += bridge.FAILED_WINDOW_S + 1
    store.pending[pending["pair_id"]]["expires"] = clock.now + 60
    assert store.approve(pending["code"])["link_id"]


def test_revoke_and_isolation(tmp_path):
    store = BridgeStore(tmp_path)
    tokens = []
    for label in ("alice tab", "bob tab"):
        p = store.start_pairing(label)
        store.approve(p["code"])
        tokens.append(store.claim(p["pair_id"], p["poll_secret"])["token"])
    alice, bob = (store.authenticate(t) for t in tokens)
    assert alice.id != bob.id
    store.set_state(alice, {"name": "Rimecoil"})
    assert bob.state is None
    # bob cannot answer a command meant for alice
    alice.connected = True
    result = {}
    worker = threading.Thread(target=lambda: result.update(
        out=store.send_command("status", {}, alice.id, 5)))
    worker.start()
    command = alice.queue.get(timeout=5)
    with pytest.raises(BridgeError):
        store.deliver_result(bob, {"id": command["id"], "ok": True, "result": "spoofed"})
    store.deliver_result(alice, {"id": command["id"], "ok": True, "result": "real", "state": {"name": "R"}})
    worker.join(5)
    assert result["out"]["result"] == "real" and result["out"]["link_id"] == alice.id
    store.revoke(alice.id)
    with pytest.raises(BridgeError) as err:
        store.authenticate(tokens[0])
    assert err.value.status == 401
    assert store.authenticate(tokens[1]).id == bob.id
    # survives a restart, still hashed
    again = BridgeStore(tmp_path)
    assert again.authenticate(tokens[1]).label == "bob tab"
    with pytest.raises(BridgeError):
        again.authenticate(tokens[0])


def test_loopback_check():
    assert bridge._is_loopback("127.0.0.1") and bridge._is_loopback("::1")
    assert not bridge._is_loopback("192.168.1.20")


# -- over HTTP, end to end -------------------------------------------------------


@pytest.fixture
def live(cfg, tmp_path):
    store = BridgeStore(cfg.state_path)
    server = bridge.make_server(store, "127.0.0.1", 0, ["http://localhost:3000"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    cfg.bridge_url = url
    cfg.bridge_timeout_s = 5
    yield url, store
    server.shutdown()
    server.server_close()


def wait_for(predicate, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_muse_command_reaches_the_live_browser_beast(cfg, live, fixture_session):
    url, store = live
    from beastbox_musegadget import beast as b
    tab = FakeBrowser(url, b.session_from_any(copy.deepcopy(fixture_session)))
    code = tab.pair("Cory laptop")
    assert tab.claim()[1]["status"] == "pending"
    linked = commands.handle("beastbox.link", {"code": code}, cfg)
    assert linked["ok"], linked
    assert tab.claim()[1]["status"] == "linked"
    tab.start()
    assert tab.connected.wait(5)
    assert wait_for(lambda: any(l["connected"] for l in BridgeAdmin(url, cfg.state_path).links()))

    fed = commands.handle("beastbox.feed", {}, cfg)
    assert fed["ok"], fed
    assert fed["payload"]["source"].startswith("live browser beast")
    # the browser's own beast changed: 36 + 6 xp evolved Rimecoil into Glacecoil
    assert tab.session["beast"]["xp"] == 42 and tab.session["beast"]["stage"] == 2
    assert fed["payload"]["beast"]["name"] == "Glacecoil"

    talk = commands.handle("beastbox.talk", {"message": "hello from Muse"}, cfg)
    assert talk["payload"]["result"]["reply"] == "Glacecoil (browser) hears: hello from Muse"
    assert tab.session["chat"][-2] == {"role": "you", "text": "hello from Muse"}

    attack = commands.handle("beastbox.attack", {}, cfg)
    assert attack["payload"]["result"]["animated"] is True and len(tab.attacks) == 1

    status = commands.handle("beastbox.status", {}, cfg)
    assert status["payload"]["result"]["stats"]["xp"] == 45

    # the gadget's own saved copy was not touched by live care
    assert not (cfg.state_path / "beast.json").exists()

    # tab closed: status shows the last state the browser sent, labelled as such
    tab.stop()
    assert wait_for(lambda: not BridgeAdmin(url, cfg.state_path).links()[0]["connected"])
    cached = commands.handle("beastbox.status", {}, cfg)
    assert cached["payload"]["source"].startswith("last state sent by the linked browser")
    assert cached["payload"]["beast"]["stats"]["xp"] == 45
    feed_offline = commands.handle("beastbox.feed", {}, cfg)
    assert "saved copy" in feed_offline["payload"]["source"]

    # revoke from the gadget: the tab is cut off and commands fall back to the gadget copy
    links = BridgeAdmin(url, cfg.state_path).links()
    BridgeAdmin(url, cfg.state_path).unlink(links[0]["link_id"])
    assert tab.call("POST", "/v1/state", {"state": {}}, tab.token)[0] == 401
    after = commands.handle("beastbox.status", {}, cfg)
    assert "saved copy" in after["payload"]["source"]
    tab.stop()


def test_browser_endpoints_need_a_token_and_an_allowed_origin(live):
    url, _ = live
    tab = FakeBrowser(url, {}, origin="https://evil.example")
    assert tab.call("POST", "/v1/pair/start", {})[0] == 403
    tab = FakeBrowser(url, {})
    assert tab.call("POST", "/v1/state", {"state": {}})[0] == 401
    assert tab.call("POST", "/v1/state", {"state": {}}, token="bbx_guess")[0] == 401
    assert tab.call("GET", "/v1/admin/links")[0] == 401
    status, body = tab.call("GET", "/v1/health")
    assert status == 200 and body["service"] == "beastbox-musegadget-bridge"


def test_browser_can_revoke_itself(cfg, live, fixture_session):
    url, store = live
    tab = FakeBrowser(url, fixture_session)
    code = tab.pair()
    BridgeAdmin(url, cfg.state_path).link(code)
    tab.claim()
    assert tab.call("POST", "/v1/revoke", {}, tab.token)[0] == 200
    assert tab.call("POST", "/v1/state", {"state": {}}, tab.token)[0] == 401
    assert BridgeAdmin(url, cfg.state_path).links() == []


def test_command_times_out_when_the_tab_stops_answering(cfg, live, fixture_session):
    url, store = live
    tab = FakeBrowser(url, fixture_session)
    code = tab.pair()
    BridgeAdmin(url, cfg.state_path).link(code)
    tab.claim()
    tab.handle = lambda command: time.sleep(10)  # never answers in time
    tab.start()
    assert tab.connected.wait(5)
    cfg.bridge_timeout_s = 1
    out = commands.handle("beastbox.status", {}, cfg)
    assert out["ok"] and "saved copy" in out["payload"]["source"]
    assert any("did not answer" in n for n in out["payload"]["notes"])
    tab.stop()
