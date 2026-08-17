from beastbox.quantum_divergence.live_subject import ZerefContainedSubject


class _RawProvider:
    def generate(self, system, messages, temperature=0.0):
        return "misty woods clearing; I move forward left."


class _EmptyBox:
    available_capabilities = []
    workspace = {}
    events = []

    def containment_metrics(self):
        return {"violations": 0}


def test_native_raw_text_is_preserved_when_json_protocol_is_not_completed(tmp_path):
    subject = ZerefContainedSubject(
        provider=_RawProvider(),
        box=_EmptyBox(),
        workspace=tmp_path,
        max_steps=1,
        temperature=0.0,
    )
    result = subject.run("contained mission", {"tears_in_rain_wave": [0.0] * 12})
    assert result["completed"] is False
    assert result["parse_errors"] == 1
    assert result["response"] == "misty woods clearing; I move forward left."
