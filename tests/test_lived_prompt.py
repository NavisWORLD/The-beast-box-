"""PR B1: versioned lived state in the local mouth prompt.

The delegate sees the canonical numbers, labels, and presence. A missing or
stale snapshot says unavailable. Guests do not receive the owner chain.
"""
import ast
import json
import sys
from pathlib import Path

import pytest

from beastbox.durable import DurableRuntime
from beastbox.guest_hebbian import MAX_ASSEMBLED_BYTES, _formatted_bytes
from beastbox.hashutil import sha256_text
from beastbox.lived_events import (
    CANONICAL_SUBJECT,
    FACE_BIO_HONESTY,
    FACE_BIO_SCHEMA,
    FACE_BIO_SOURCE,
    FEELING_WORDS,
    STALE_MS,
    host_attachment,
)
from beastbox.lived_prompt import (
    backbone_ready,
    capability_receipt,
    owner_view,
    project_descriptor,
    reset_pins,
)
from beastbox.lived_state import LivedStore

ROOT = Path(__file__).resolve().parents[1]
NOW = 1_700_000_000_000
ORIGIN = "ab" * 32
PRIOR = "cd" * 32
GUEST = "a" * 64


def measured(value, source, quality=1.0):
    return {"label": "MEASURED", "value": value, "status": "present", "source": source, "quality": quality}


def absent(source="none"):
    return {"label": "ABSENT", "value": None, "status": "absent", "source": source, "quality": None}


def face_record(*, present=True, scale=0.22, x=0.05, y=-0.1, blink=0.3, pulse=None):
    return {
        "schema": FACE_BIO_SCHEMA,
        "source": FACE_BIO_SOURCE,
        "heartbeat_label": "ESTIMATE",
        "honesty": FACE_BIO_HONESTY,
        "face": {"present": present, "scale": scale, "x": x, "y": y, "blink": blink},
        "pulse": pulse,
        "raw_audio_published": False,
        "raw_video_published": False,
        "raw_frames_in_packet": False,
    }


def sample(seq, brightness, *, pulse=61.0, captured=NOW):
    return {
        "schema": "sensor-sample-v1",
        "surface_id": "owner-shell",
        "session_id": "session-a",
        "consent_epoch": 1,
        "source_seq": seq,
        "captured_at_ms": captured,
        "channels": {
            "brightness": measured(brightness, "camera"),
            "hue": measured(12.5, "camera"),
            "frame_motion": absent("camera"),
            "device_motion": absent(),
            "sound": absent("microphone"),
            "pulse_bpm": measured(pulse, "fingertip_ppg"),
        },
        "face": face_record(pulse={"bpm": 72.0, "sqi": 0.55}),
    }


def activate(monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "on")
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", ORIGIN)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", PRIOR)
    monkeypatch.setattr("beastbox.lived_prompt._now_ms", lambda: NOW + 1000)
    reset_pins()


def open_owner(root: Path):
    path = root / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    attachment = host_attachment()
    fields = {key: attachment[key] for key in (
        "schema", "subject_id", "scope", "basis", "origin_commitment", "prior_head", "verified",
    )}
    return LivedStore.open(path, fields)


def span(prompt: str) -> str:
    begin = "LIVED-STATE-DESCRIPTOR\n"
    end = "\nEND-LIVED-STATE-DESCRIPTOR\n"
    start = prompt.index(begin) + len(begin)
    return prompt[start:prompt.index(end, start)]


class Capture:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "noted"


class RemoteCapture(Capture):
    allow_remote = True


@pytest.fixture(autouse=True)
def _clear_pins():
    reset_pins()
    yield
    reset_pins()


def test_env_flag_is_a_literal_and_there_is_no_training_switch():
    source = (ROOT / "beastbox" / "lived_prompt.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    reads = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        env_get = (
            isinstance(func, ast.Attribute) and func.attr == "get"
            and isinstance(func.value, ast.Attribute) and func.value.attr == "environ"
        )
        env_getenv = (
            isinstance(func, ast.Attribute) and func.attr == "getenv"
            and isinstance(func.value, ast.Name) and func.value.id == "os"
        )
        if not env_get and not env_getenv:
            continue
        arg = node.args[0]
        assert isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        reads.append(arg.value)
    assert reads == ["BEASTBOX_LIVED_BACKBONE"]
    assert "random" not in source
    assert "ZEREF_COND54_PAIR" not in source
    assert "Math.random" not in source


def test_missing_hashes_do_not_crash_the_mouth_when_the_flag_is_on(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.close()
    monkeypatch.delenv("BEASTBOX_LIVED_BACKBONE", raising=False)
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", "")
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", "")
    view = owner_view(tmp_path, now_ms=NOW + 1000)
    assert view.status == "unavailable"
    assert view.reason == "missing"


def test_flag_off_leaves_the_owner_prompt_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "off")
    assert backbone_ready() is False
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello from the shell")
    runtime.close()
    assert "lived_state" not in result
    assert "LIVED-STATE-DESCRIPTOR" not in capture.prompts[0]
    assert "USER INPUT:\nhello from the shell\n" in capture.prompts[0]


def test_fake_delegate_transport_sees_exact_snapshot(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    snap = store.read_lived_snapshot("owner")
    store.close()
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello from the shell")
    runtime.close()
    prompt = capture.prompts[0]
    body = json.loads(span(prompt))
    assert body["channels"]["brightness"] == {
        "label": "MEASURED", "source": "camera", "status": "present", "value": 0.137,
    }
    assert body["channels"]["sound"]["label"] == "ABSENT"
    assert body["channels"]["sound"]["value"] is None
    assert body["channels"]["pulse_bpm"]["label"] == "MEASURED"
    assert body["channels"]["pulse_bpm"]["source"] == "fingertip_ppg"
    assert body["channels"]["pulse_bpm"]["value"] == 61.0
    assert body["face"]["label"] == "ESTIMATE"
    assert body["face"]["pulse"]["label"] == "ESTIMATE"
    assert body["face"]["pulse"]["bpm"] == 72.0
    assert body["feelings"]["label"] == "DERIVED"
    assert body["feelings"]["confused"] is None
    assert set(FEELING_WORDS) <= set(body["feelings"])
    assert body["changes_model_tensors"] is False
    assert body["state12"] == [float(item) for item in snap["state12"]]
    assert ORIGIN not in prompt and CANONICAL_SUBJECT not in prompt
    assert "browser_face" not in prompt and "Cory" not in prompt and "waveform" not in prompt
    receipt = result["lived_state"]
    assert receipt["status"] == "delivered" and receipt["conditioned"] is True
    assert receipt["sequence"] == snap["sequence"]
    assert receipt["state_sha256"] == snap["state_sha256"]
    assert receipt["descriptor_sha256"] == sha256_text(span(prompt))
    assert receipt["changes_model_tensors"] is False
    assert receipt["counts_as_memory_used"] is False
    assert "0.5" not in json.dumps(body["channels"]["sound"])


def test_different_snapshots_make_different_prompts(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    first = project_descriptor(store.read_lived_snapshot("owner"))
    store.admit_sensor(sample(2, 0.91, pulse=80.0), now_ms=NOW + 1000)
    second = project_descriptor(store.read_lived_snapshot("owner"))
    store.close()
    assert first != second
    assert "0.137" in first and "0.91" not in first
    assert "0.91" in second and "0.137" not in second


def test_two_drafts_share_one_pinned_snapshot(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    store.close()
    first = owner_view(tmp_path, "exchange-1", now_ms=NOW + 1000)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(2, 0.91), now_ms=NOW + 1000)
    store.close()
    second = owner_view(tmp_path, "exchange-1", now_ms=NOW + 1000)
    assert first.descriptor == second.descriptor
    assert "0.137" in first.descriptor and "0.91" not in second.descriptor
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    runtime._lived_exchange_id = "exchange-1"
    runtime.respond("first draft")
    runtime.respond("second draft")
    runtime.close()
    assert "0.137" in capture.prompts[0] and "0.137" in capture.prompts[1]
    assert "0.91" not in capture.prompts[0] and "0.91" not in capture.prompts[1]
    assert sha256_text(span(capture.prompts[0])) == sha256_text(span(capture.prompts[1]))


def test_missing_snapshot_says_unavailable_and_creates_nothing(tmp_path, monkeypatch):
    activate(monkeypatch)
    path = tmp_path / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello")
    runtime.close()
    assert not path.exists()
    body = json.loads(span(capture.prompts[0]))
    assert body["status"] == "unavailable" and body["reason"] == "missing"
    assert "state12" not in body and "0.137" not in capture.prompts[0]
    receipt = result["lived_state"]
    assert receipt["status"] == "unavailable" and receipt["conditioned"] is False
    assert receipt["sequence"] is None and receipt["state_sha256"] is None
    assert receipt["descriptor_sha256"] == sha256_text(span(capture.prompts[0]))
    assert receipt["changes_model_tensors"] is False


def test_stale_snapshot_is_unavailable_and_not_spoken(tmp_path, monkeypatch):
    activate(monkeypatch)
    monkeypatch.setattr("beastbox.lived_prompt._now_ms", lambda: NOW + STALE_MS + 1)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW)
    snap = store.read_lived_snapshot("owner")
    store.close()
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello")
    runtime.close()
    assert "0.137" not in capture.prompts[0] and "state12" not in span(capture.prompts[0])
    assert json.loads(span(capture.prompts[0]))["status"] == "unavailable"
    receipt = result["lived_state"]
    assert receipt["status"] == "unavailable" and receipt["reason"] == "stale"
    assert receipt["conditioned"] is False
    assert receipt["sequence"] == snap["sequence"]
    assert receipt["state_sha256"] == snap["state_sha256"]
    assert receipt["descriptor_sha256"] == sha256_text(span(capture.prompts[0]))


def test_sequence_zero_is_labelled_software_and_channels_stay_null(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.close()
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    runtime.respond("hello")
    runtime.close()
    body = json.loads(span(capture.prompts[0]))
    assert body["sequence"] == 0
    assert body["initial_state_kind"] == "software-initial-not-history"
    assert body["classical_software"] is True
    for name, channel in body["channels"].items():
        assert channel["label"] == "ABSENT" and channel["value"] is None, name
    assert body["face"] == {"label": "ABSENT", "value": None}
    assert "0.5" not in span(capture.prompts[0])


def test_remote_provider_does_not_receive_the_numbers(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    store.close()
    capture = RemoteCapture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello")
    runtime.close()
    assert "0.137" not in capture.prompts[0] and "fingertip_ppg" not in capture.prompts[0]
    assert result["lived_state"]["status"] == "unavailable"
    assert result["lived_state"]["reason"] == "remote_withheld"
    assert result["lived_state"]["conditioned"] is False
    assert result["lived_state"]["changes_model_tensors"] is False
    assert result["lived_state"]["sequence"] is not None


def test_omitted_descriptor_is_not_reported_as_delivered(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    snap = store.read_lived_snapshot("owner")
    store.close()
    huge = "Q" * 5000

    def oversized(_snapshot):
        return huge

    monkeypatch.setattr("beastbox.lived_prompt.project_descriptor", oversized)
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello")
    runtime.close()
    # The oversized text never enters the prompt. Omission is its own status.
    assert "QQQQ" not in capture.prompts[0]
    assert "LIVED-STATE-DESCRIPTOR" not in capture.prompts[0]
    receipt = result["lived_state"]
    assert receipt["status"] == "omitted" and receipt["reason"] == "budget"
    assert receipt["conditioned"] is False
    assert receipt["descriptor_sha256"] is None
    assert receipt["changes_model_tensors"] is False
    assert receipt["sequence"] == snap["sequence"]
    assert receipt["state_sha256"] == snap["state_sha256"]


def _guest_server(monkeypatch, sent):
    from beastbox import guest_local

    class Resp:
        status = 200
        headers = {"Content-Length": "0"}

        def __init__(self, body):
            self._b = body

        def read(self, n):
            return self._b

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, req, timeout=0):
            sent.append(json.loads(req.data))
            return Resp(json.dumps({
                "model": guest_local.MODEL,
                "checkpoint_sha256": guest_local.SHA,
                "hebbian": True,
                "state_mode": "tri",
                "choices": [{"message": {"content": "hi there"}}],
            }).encode())

    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    monkeypatch.setattr(guest_local, "_local_opener", lambda: Opener())
    monkeypatch.setattr(guest_local, "native_status", lambda: {
        "readiness": "INSTALLED_AND_READY",
        "loaded_step": guest_local.STEP,
        "checkpoint_sha256": guest_local.SHA,
        "cond54": False,
    })
    return guest_local


def test_guests_stay_isolated_from_the_owner_snapshot(tmp_path, monkeypatch):
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    store.close()
    opened = []

    def spy_open(*args, **kwargs):
        opened.append(args)
        raise AssertionError("guest mouth opened a lived store")

    monkeypatch.setattr("beastbox.lived_state.LivedStore.open", spy_open)
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": GUEST})
    assert code == 200 and opened == []
    assert body["memory_used"] is False
    assert body["lived_state"]["status"] == "unavailable"
    assert body["lived_state"]["reason"] == "isolated"
    assert body["lived_state"]["scope"] == "guest"
    assert body["lived_state"]["changes_model_tensors"] is False
    assert body["lived_state"]["counts_as_memory_used"] is False
    encoded = json.dumps(sent[0])
    assert "0.137" not in encoded and "fingertip_ppg" not in encoded
    assert "condition54" not in sent[0]
    assert sent[0]["messages"][0]["role"] == "system"
    assert json.loads(sent[0]["messages"][0]["content"])["status"] == "unavailable"
    assert body["lived_state"]["descriptor_sha256"] == sha256_text(sent[0]["messages"][0]["content"])
    code, rejected = guest_local.guest_local_infer(tmp_path, {
        "text": "hello", "guest_identity": GUEST, "state": "brightness 0.137",
    })
    assert code == 400 and len(sent) == 1 and "0.137" not in rejected.get("error", "")


def test_two_guest_drafts_share_the_pinned_unavailable_descriptor(tmp_path, monkeypatch):
    activate(monkeypatch)
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    import beastbox.growing as growing
    import beastbox.providers as providers
    monkeypatch.setenv("BEASTBOX_GROWING_ENABLED", "yes")
    monkeypatch.setattr(growing, "current", lambda: {
        "tag": "zeref-growing-020", "step": 41584, "checkpoint_sha256": "f" * 64,
    })

    class Quota:
        def __init__(self, root):
            pass

        def reserve(self, ident):
            return 200, "t", ""

        def release(self, token):
            pass

    monkeypatch.setattr(guest_local, "GuestQuota", Quota)
    growing_sent = []

    class Opener:
        def open(self, req, timeout=0):
            growing_sent.append(json.loads(req.data))
            return type("R", (), {
                "read": lambda self, n: json.dumps({
                    "model": "rawrphos-native",
                    "checkpoint_sha256": "f" * 64,
                    "choices": [{"message": {"content": "hello"}}],
                }).encode(),
                "__enter__": lambda self: self,
                "__exit__": lambda self, *a: False,
            })()

    monkeypatch.setattr(providers, "_local_opener", lambda: Opener())
    code, first = guest_local.guest_local_infer(
        tmp_path, {"text": "hello", "guest_identity": GUEST}, exchange_id="draft-7",
    )
    def explode(*args, **kwargs):
        raise AssertionError("second draft rebuilt the snapshot")
    monkeypatch.setattr("beastbox.lived_prompt._isolated_guest", explode)
    code2, second = growing.growing_infer(
        tmp_path, {"text": "hello", "guest_identity": GUEST}, exchange_id="draft-7",
    )
    assert code == 200 and code2 == 200
    assert first["lived_state"]["descriptor_sha256"] == second["lived_state"]["descriptor_sha256"]
    assert first["memory_used"] is False and second["memory_used"] is False
    assert sent[0]["messages"][0]["content"] == growing_sent[0]["messages"][0]["content"]


def test_unicode_1800_and_worst_byte_prompts_keep_the_descriptor(tmp_path, monkeypatch):
    activate(monkeypatch)
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    short = "héllo 🌟 你"
    code, body = guest_local.guest_local_infer(tmp_path, {"text": short, "guest_identity": GUEST})
    assert code == 200
    assert sent[0]["messages"][-1]["content"] == short
    assert json.loads(sent[0]["messages"][0]["content"])["status"] == "unavailable"
    assert _formatted_bytes(sent[0]["messages"]) <= MAX_ASSEMBLED_BYTES
    assert body["lived_state"]["omitted_current_text_bytes"] == 0

    cjk = "你" * 1800
    code, body = guest_local.guest_local_infer(tmp_path, {"text": cjk, "guest_identity": GUEST})
    assert code == 200
    spoken = sent[1]["messages"][-1]["content"]
    assert body["lived_state"]["status"] == "unavailable"
    assert body["lived_state"]["omitted_current_text_bytes"] == len(cjk.encode("utf-8")) - len(
        spoken.split(" [omitted ", 1)[0].encode("utf-8")
    )
    assert _formatted_bytes(sent[1]["messages"]) <= MAX_ASSEMBLED_BYTES
    assert json.loads(sent[1]["messages"][0]["content"])["changes_model_tensors"] is False

    worst = "😀" * 1800
    code, body = guest_local.guest_local_infer(tmp_path, {"text": worst, "guest_identity": GUEST})
    assert code == 200
    spoken = sent[2]["messages"][-1]["content"]
    assert "omitted" in spoken and spoken != worst
    assert body["lived_state"]["conditioned"] is False
    assert body["lived_state"]["status"] != "delivered"
    assert _formatted_bytes(sent[2]["messages"]) <= MAX_ASSEMBLED_BYTES
    prefix = spoken.split(" [omitted ", 1)[0]
    assert worst.encode("utf-8").startswith(prefix.encode("utf-8"))
    assert body["lived_state"]["omitted_current_text_bytes"] == len(worst.encode()) - len(prefix.encode())


def test_flag_off_long_prompt_stays_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "off")
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    text = "a" * 1800
    code, body = guest_local.guest_local_infer(tmp_path, {"text": text, "guest_identity": GUEST})
    assert code == 200 and "lived_state" not in body
    assert sent[0]["messages"] == [{"role": "user", "content": text}]
    assert "condition54" not in sent[0]


def test_guest_budget_omission_is_not_success(tmp_path, monkeypatch):
    activate(monkeypatch)
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    from beastbox.lived_prompt import LivedExchange
    huge = LivedExchange("guest", "delivered", None, 3, "cd" * 32, "Q" * 5000)
    monkeypatch.setattr("beastbox.guest_local.guest_view", lambda *args, **kwargs: huge)
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": GUEST})
    assert code == 200
    assert body["lived_state"]["status"] == "omitted"
    assert body["lived_state"]["conditioned"] is False
    assert body["lived_state"]["descriptor_sha256"] is None
    assert body["lived_state"]["changes_model_tensors"] is False
    assert body["memory_used"] is False
    assert "QQQQ" not in json.dumps(sent[0]["messages"])
    assert sent[0]["messages"] == [{"role": "user", "content": "hello"}]


def test_capability_receipt_does_not_call_a_model(monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "off")
    assert capability_receipt()["state_conditioning"] == "unavailable"
    assert capability_receipt()["changes_model_tensors"] is False
    assert capability_receipt()["clients_submit_state"] is False
    activate(monkeypatch)
    assert capability_receipt()["state_conditioning"] == "available"
    bridge = ROOT / "apps" / "beastbox-cloud" / "bridge"
    sys.path.insert(0, str(bridge))
    import owner_bridge
    health = owner_bridge.served_pin_health()
    assert health["lived_state"]["schema"] == "lived-state-capability-v1"
    assert health["lived_state"]["state_conditioning"] == "available"
    assert health["lived_state"]["changes_model_tensors"] is False
    assert health["lived_state"]["clients_submit_state"] is False
    assert "context_fields" in health
