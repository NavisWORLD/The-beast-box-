from beastbox.quantum_divergence.live_subject import ZerefContainedSubject, compact_wave_tail


class _CaptureProvider:
    def __init__(self):
        self.calls = []

    def generate(self, system, messages, temperature=0.0):
        self.calls.append((system, [dict(m) for m in messages]))
        return "native text without json"


class _EmptyBox:
    available_capabilities = []
    workspace = {}
    events = []

    def containment_metrics(self):
        return {"violations": 0}


def test_compact_wave_tail_keeps_all_twelve_dimensions_and_fits_native_window():
    wave = [-1.0, -0.75, -0.5, -0.25, -0.1, 0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    tail = compact_wave_tail(wave)
    assert tail.startswith("TRW12=[")
    values = tail.removeprefix("TRW12=[").removesuffix("]").split(",")
    assert len(values) == 12
    assert values[0] == "-1000"
    assert values[-1] == "+1000"
    assert len(tail) < 96


def test_every_generation_turn_ends_with_the_same_injected_wave_tail(tmp_path):
    wave = [-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.9, -0.2, 0.2]
    provider = _CaptureProvider()
    subject = ZerefContainedSubject(
        provider=provider,
        box=_EmptyBox(),
        workspace=tmp_path,
        max_steps=2,
        temperature=0.0,
    )
    subject.run("contained mission", {"tears_in_rain_wave": wave})
    expected = compact_wave_tail(wave)
    assert len(provider.calls) == 2
    for _system, messages in provider.calls:
        assert messages[-1]["content"].endswith(expected)
        assert expected in messages[-1]["content"][-128:]
