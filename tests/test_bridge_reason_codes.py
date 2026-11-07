import io, json, socket, unittest, urllib.error
from beastbox.reason_codes import reason_for, timed_guest_call, log_502, clean_reason


class ReasonCodes(unittest.TestCase):
    def test_exception_mapping(self):
        self.assertEqual(reason_for(TimeoutError()), "upstream_timeout")
        self.assertEqual(reason_for(socket.timeout()), "upstream_timeout")
        self.assertEqual(reason_for(urllib.error.URLError(socket.timeout())), "upstream_timeout")
        self.assertEqual(reason_for(urllib.error.HTTPError("http://x", 500, "m", {}, None)), "model_error:HTTPError:500")
        self.assertEqual(reason_for(ConnectionRefusedError()), "model_error:ConnectionRefusedError")
        self.assertEqual(reason_for(KeyError("secret prompt text")), "model_error:KeyError")

    def test_502_logs_one_content_free_line_and_adds_request_id(self):
        out = io.StringIO()
        code, body = timed_guest_call("guest-growing", lambda: (502, {"error": "x", "reason": "empty_reply"}), stream=out)
        self.assertEqual(code, 502); self.assertEqual(body["reason"], "empty_reply")
        self.assertRegex(body["request_id"], r"^[0-9a-f]{12}$")
        line = json.loads(out.getvalue())
        self.assertEqual(set(line), {"event", "route", "reason", "latency_ms", "request_id"})
        self.assertEqual((line["route"], line["reason"], line["request_id"]), ("guest-growing", "empty_reply", body["request_id"]))

    def test_non_502_untouched_and_silent(self):
        out = io.StringIO(); body = {"reply": "hi"}
        self.assertEqual(timed_guest_call("guest-growing", lambda: (200, body), stream=out), (200, body))
        self.assertEqual(out.getvalue(), "")

    def test_no_content_can_reach_the_log(self):
        out = io.StringIO()
        log_502("guest-local", "empty_reply; prompt=hello sk-abc", 3.2, "zz-not-hex-0123456789abcdef", stream=out)
        line = json.loads(out.getvalue())
        self.assertEqual(line["reason"], "unknown"); self.assertNotIn("hello", out.getvalue())
        self.assertEqual(line["request_id"], "0123456789ab"[:0] + line["request_id"]); self.assertRegex(line["request_id"], r"^[0-9a-f]{0,12}$")
        self.assertEqual(clean_reason(None), "unknown")
        for ok in ("empty_reply", "oversize", "identity_fail", "upstream_timeout", "model_error:HTTPError:500", "model_error:BadStatus"):
            self.assertEqual(clean_reason(ok), ok)


if __name__ == "__main__":
    unittest.main()
