"""Owner-verified explicit retention of temporary-context chat replies."""
import importlib.util
import json
from pathlib import Path
import time
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_remember_tests", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TOKEN = "temporary-reply-test-token-strong-fixture-2026"
AUTH = "Bearer " + TOKEN


def dispatch(app, method, path, body=None, auth=AUTH):
    encoded = b"" if body is None else json.dumps(body).encode()
    return app.dispatch(method, path, auth, encoded)


def test_temporary_reply_remains_private_until_explicit_owner_consent(tmp_path):
    app = module.OwnerBridge(tmp_path, TOKEN)
    _, staged = dispatch(app, "POST", "/api/context",
                         {"scope": "temporary_attachment", "name": "secret-demo.txt",
                          "text": "Private attachment marker: MOONLIGHT_TEST_ONLY"})
    assert isinstance(staged["id"], int)
    payload = {"text": "Describe this document",
               "context_ids": [staged["id"]], "request_id": str(uuid.uuid4())}
    code, job = dispatch(app, "POST", "/api/chat-start", payload)
    assert code in (200, 202)
    job_id = job["job_id"]
    state = job
    for _ in range(150):
        if state["state"] != "running":
            break
        time.sleep(.01)
        code, state = app.dispatch("GET", "/api/chat-job?id=" + job_id, AUTH)
        assert code == 200
    assert state["state"] == "complete", state
    assert state["result"]["response_persistent"] is False
    assert state["result"]["context_used"] == [staged["id"]]
    _, history = dispatch(app, "GET", "/api/conversation")
    assert [t["kind"] for t in history["turns"]] == ["user_turn"]
    baseline = state["result"]["runtime"]["checkpoint_sha256"]

    body = {"job_id": job_id, "consent": True}
    assert dispatch(app, "POST", "/api/remember-reply", body, auth="")[0] == 401
    assert dispatch(app, "POST", "/api/remember-reply", {**body, "consent": False})[0] == 400
    assert dispatch(app, "POST", "/api/remember-reply", {**body, "text": "injected"})[0] == 400
    _, history = dispatch(app, "GET", "/api/conversation")
    assert len(history["turns"]) == 1  # No implicit private persistence.

    code, saved = dispatch(app, "POST", "/api/remember-reply", body)
    assert code == 200, saved
    assert saved["remembered"] is True
    assert saved["already_remembered"] is False
    assert saved["raw_media_saved"] is False
    assert saved["checkpoint_sha256"] != baseline
    code, duplicate = dispatch(app, "POST", "/api/remember-reply", body)
    assert code == 200 and duplicate["already_remembered"] is True
    assert duplicate["memory_id"] == saved["memory_id"]
    _, history = dispatch(app, "GET", "/api/conversation")
    assert [t["kind"] for t in history["turns"]] == ["user_turn", "assistant_turn"]
    assert history["turns"][-1]["text"] == state["result"]["result"]["response"]
    reboot = module.OwnerBridge(tmp_path, TOKEN)
    _, again = dispatch(reboot, "GET", "/api/conversation")
    assert again["turns"] == history["turns"]
    assert reboot.app.service.runtime.inspect()["valid"] if hasattr(reboot.app.service, "runtime") else True
