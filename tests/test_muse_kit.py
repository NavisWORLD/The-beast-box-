"""Muse kit: synthetic headband, packet fixtures, privacy, and the shared trait schema."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from beastbox_muse.bands import band_powers, mock_traits, mock_window, relative_bands
from beastbox_muse.bio_map import snapshot_from_samples
from beastbox_muse.ble import classify_characteristics, read_window
from beastbox_muse.cli import main as muse_main
from beastbox_muse.discover import BleOffer, Discovery, StreamOffer, choose
from beastbox_muse.lsl_inlet import channel_index, samples_from_chunk
from beastbox_muse.packets import (
    decode_athena_eeg_af7,
    decode_eeg_packet,
    encode_athena_eeg_packet,
    encode_command,
    encode_legacy_eeg_packet,
)
from beastbox_muse.privacy import ConsentRequired, MuseKitError, append_raw, derived_record, require_consent
from beastbox_muse.schema import ATHENA_DATA, ATHENA_UV_MIDPOINT, CONTROL_UUID, DISCLAIMER, LEGACY_EEG
from beastbox_muse.service import discover_live, run_simulate

from beastbox.bio_inputs import bio_event
from beastbox.cosmic_ui import render_cosmic_ui
from beastbox.signal_fusion import source_from_bio_event

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "packages/beastbox-muse/src/beastbox_muse/muse_browser.js"
WEB_JS = ROOT / "html/muse.js"


class FakeGatt:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.writes: list[bytes] = []
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def characteristics(self) -> set[str]:
        if self.kind == "athena":
            return {CONTROL_UUID, *ATHENA_DATA}
        return {CONTROL_UUID, *LEGACY_EEG.values()}

    async def write(self, uuid: str, data: bytes) -> None:
        assert uuid == CONTROL_UUID
        self.writes.append(bytes(data))

    async def start_notify(self, uuid: str, callback) -> None:
        if self.kind == "legacy" and uuid == LEGACY_EEG["AF7"]:
            codes = [0x800] * 256
            codes[0] = 0x810
            for start in range(0, 256, 12):
                callback(encode_legacy_eeg_packet(start, codes[start:start + 12]))
        if self.kind == "athena" and uuid == ATHENA_DATA[0]:
            for index in range(64):
                callback(encode_athena_eeg_packet([ATHENA_UV_MIDPOINT + 10] * 4, packet_index=index))

    async def disconnect(self) -> None:
        self.connected = False


class FakeInlet:
    def __init__(self, rows: list[list[float]], labels: tuple[str, ...] = ()) -> None:
        self.name = "Muse-LSL"
        self.stream_type = "EEG"
        self.channel_count = len(rows[0])
        self.nominal_rate = 256
        self.labels = labels
        self._rows = rows

    def pull(self, max_samples: int, timeout: float) -> list[list[float]]:
        chunk = self._rows[:max_samples]
        self._rows = self._rows[max_samples:]
        return chunk


def test_companion_mock_traits_are_shared_game_signals() -> None:
    traits = mock_traits()
    fixture = json.loads((ROOT / "packages/beastbox-muse/src/beastbox_muse/fixtures/companion_mock_traits.json").read_text())
    assert traits == {"schema": fixture["schema"], "focus": fixture["focus"], "calm": fixture["calm"], "spark": fixture["spark"]}
    # Rounding each share can make the three integers add to 101. That matches Math.round.
    relative = relative_bands(band_powers(mock_window()))
    assert relative["alpha"] > relative["beta"] > relative["gamma"]
    assert abs(sum(relative.values()) - 1) < 1e-9


def test_simulated_window_drives_bio_inputs_end_to_end() -> None:
    snapshot = snapshot_from_samples(mock_window(), transport="simulate", model_family="simulated", simulated=True)
    assert snapshot["disclaimer"] == DISCLAIMER
    assert snapshot["raw_eeg"] == "omitted"
    assert snapshot["hardware_attested"] is False
    event = snapshot["bio_event"]
    assert len(event["features"]) == 12
    # Missing non-EEG channels stay the explicit zero placeholder.
    assert event["features"][0] == 0.0
    assert event["features"][6] == 0.0
    # Alpha is channel index 7 and is above the midpoint of [0, 1] for this tone.
    assert event["features"][7] > 0
    parsed = json.loads(event["text"])
    assert parsed["schema"] == "bio-measurement-v1"
    assert parsed["source_label"] == "manual"
    assert "eeg_alpha_relative" in parsed["channels_present"]
    assert "heart_rate_bpm" in parsed["missing_channels"]
    assert "samples" not in event["text"]
    source = source_from_bio_event(
        {"schema": event["schema"], "source": event["source"], "text": event["text"], "features": event["features"]},
        source_id="muse-simulate",
    )
    assert source.kind == "bio12-v1"
    assert source.family == "sensory"
    assert list(source.vector) == snapshot["signal_source"]["vector"]


def test_legacy_and_athena_packet_fixtures_round_trip() -> None:
    packet = encode_legacy_eeg_packet(7, [0x800, 0x801, 0, 4095])
    sequence, samples = decode_eeg_packet(packet)
    assert sequence == 7
    assert samples[0] == 0
    assert samples[1] == pytest.approx(0.48828125)
    assert encode_command("h") == bytes([2, ord("h"), 10])
    assert encode_command("p21") == bytes([4, ord("p"), ord("2"), ord("1"), 10])

    athena = encode_athena_eeg_packet([ATHENA_UV_MIDPOINT + 10] * 4, packet_index=3)
    decoded = decode_athena_eeg_af7(athena)
    assert len(decoded) == 4
    assert decoded[0] == pytest.approx(10 * (1450.0 / 16383.0))
    assert decode_athena_eeg_af7(b"\x00\x01") == []


def test_fake_headbands_emit_one_af7_window() -> None:
    import asyncio

    legacy = FakeGatt("legacy")
    family, samples, sent = asyncio.run(read_window(legacy, model="auto", name="Muse-1234", delay=0))
    assert family == "muse2"
    assert len(samples) == 256
    assert samples[0] != 0
    commands = [blob.decode("ascii", "ignore") for blob in sent]
    assert any("p21" in command for command in commands)
    assert legacy.connected is False

    athena = FakeGatt("athena")
    family, samples, sent = asyncio.run(read_window(athena, model="auto", name="MuseS-Athena", delay=0))
    assert family == "muse_s_athena"
    assert len(samples) == 256
    assert any("p1041" in blob.decode("ascii", "ignore") for blob in sent)
    assert any("dc001" in blob.decode("ascii", "ignore") for blob in sent)
    with pytest.raises(MuseKitError):
        classify_characteristics(set(), "athena")


def test_fallback_order_never_invents_a_simulator() -> None:
    lsl = choose(Discovery(
        lsl_streams=(StreamOffer("MindMonitor", "EEG", 4, "mind_monitor"),),
        ble_devices=(BleOffer("Muse-ABCD", "AA:BB"),),
        bleak_installed=True,
        pylsl_installed=True,
    ))
    assert lsl["transport"] == "lsl"
    assert lsl["source_hint"] == "mind_monitor"
    ble = choose(Discovery(ble_devices=(BleOffer("MuseS-1000", "CC:DD"),), bleak_installed=True))
    assert ble["transport"] == "ble"
    assert ble["model_hint"] == "muse_s"
    missed = choose(Discovery(bleak_installed=False, pylsl_installed=False))
    assert missed["transport"] is None
    assert [step["step"] for step in missed["tried"]] == ["lsl", "ble"]
    assert "simulate" in missed["next"]
    forced = choose(Discovery(), "simulate")
    assert forced["transport"] == "simulate"
    live = discover_live(
        preference="auto",
        scan_ble=lambda: [("Muse-ZZ", "11:22")],
        scan_lsl=list,
    )
    assert live["transport"] == "ble"
    petal = type("Stream", (), {"name": "PetalMetrics", "stream_type": "EEG", "channel_count": 4})()
    preferred = discover_live(preference="auto", scan_lsl=lambda: [petal], scan_ble=lambda: [("Muse-ZZ", "11:22")])
    assert preferred["transport"] == "lsl"


def test_lsl_fixture_uses_af7_when_labeled() -> None:
    row = [float(i) for i in range(4)]
    inlet = FakeInlet([row] * 256, labels=("TP9", "AF7", "AF8", "TP10"))
    assert channel_index(inlet.labels, 4) == 1
    samples, mode = samples_from_chunk(inlet)
    assert mode == "eeg"
    assert samples[0] == 1.0
    bands = FakeInlet([[1, 2, 3, 4, 5]], labels=("delta", "theta", "alpha", "beta", "gamma"))
    assert channel_index(bands.labels, 5) is None


def test_consent_and_raw_opt_in_stay_local(tmp_path: Path) -> None:
    with pytest.raises(ConsentRequired):
        require_consent(False)
    with pytest.raises(ConsentRequired):
        run_simulate(consent=False)
    snapshots = run_simulate(consent=True, windows=1)
    record = derived_record(snapshots[0])
    assert record["raw_eeg"] == "omitted"
    assert "samples" not in record
    assert record["upload"] is False
    derived_path = tmp_path / "session.jsonl"
    from beastbox_muse.service import record_snapshots
    from beastbox_muse.simulate import window

    saved = record_snapshots(snapshots, derived_path, raw_samples=[window(0)])
    text = derived_path.read_text(encoding="utf-8")
    assert "samples" not in text
    assert "focus" in text
    raw_path = Path(saved["raw_eeg_file"])
    assert raw_path.parent == tmp_path
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw["storage"] == "local-only"
    assert raw["upload"] is False
    assert len(raw["samples"]) == 256
    with pytest.raises(MuseKitError):
        append_raw(Path("https://example.invalid/eeg.jsonl"), [0.0], transport="simulate", model_family="simulated")


def test_cli_simulate_demo_and_status(capsys: pytest.CaptureFixture[str]) -> None:
    assert muse_main(["status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["fallback_order"] == ["lsl", "ble"]
    assert status["raw_eeg_default"] == "omitted"
    assert muse_main(["simulate"]) == 2
    err = capsys.readouterr().err
    assert "consent" in err.lower()
    assert muse_main(["simulate", "--consent", "--demo"]) == 0
    demo = json.loads(capsys.readouterr().out)
    assert demo["schema"] == "beastbox-muse-demo-v1"
    assert demo["drove_bio_inputs"] is True
    assert demo["simulated"] is True
    assert len(demo["bio_event"]["features"]) == 12
    assert "samples" not in json.dumps(demo)
    direct = bio_event(
        readings={
            "eeg_delta_relative": demo["relative_bands"]["delta"],
            "eeg_theta_relative": demo["relative_bands"]["theta"],
            "eeg_alpha_relative": demo["relative_bands"]["alpha"],
            "eeg_beta_relative": demo["relative_bands"]["beta"],
            "eeg_gamma_relative": demo["relative_bands"]["gamma"],
        },
        source="manual",
        consent=True,
    )
    assert direct["features"] == demo["bio_event"]["features"]


def test_beastbox_muse_help_and_simulate() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "packages/beastbox-muse/src"), env.get("PYTHONPATH", "")])
    help_run = subprocess.run(
        [sys.executable, "-m", "beastbox", "muse", "--help"],
        check=False, capture_output=True, text=True, env=env,
    )
    assert help_run.returncode == 0
    assert "simulate" in help_run.stdout
    demo = subprocess.run(
        [sys.executable, "-m", "beastbox", "muse", "simulate", "--consent", "--demo"],
        check=False, capture_output=True, text=True, env=env,
    )
    assert demo.returncode == 0, demo.stderr
    payload = json.loads(demo.stdout)
    assert payload["traits"]["schema"] == "cosmic-muse-traits-v1"
    assert payload["bio_event"]["features"][7] > 0


def test_browser_module_matches_python_and_is_served_with_the_ui() -> None:
    assert JS.is_file()
    assert WEB_JS.read_bytes() == JS.read_bytes()
    source = JS.read_text(encoding="utf-8")
    assert "cosmic-muse-traits-v1" in source
    assert "Safari and iOS" in source
    assert "https://" not in source
    html = render_cosmic_ui()
    assert ">MUSE</button>" in html
    assert "Wellness and game signals only" in html
    assert "museConsent" in html
    assert "window.BeastboxMuse" in html
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; Python fixtures still lock the trait schema")
    script = (
        "const api=require(process.argv[1]);"
        "const snap=api.simulatedSnapshot();"
        "if(snap.rawEeg!=='omitted') throw new Error('raw');"
        "process.stdout.write(JSON.stringify({traits:snap.traits,features:snap.bioFeatures,support:api.browserSupport()}));"
    )
    run = subprocess.run([node, "-e", script, str(JS)], check=False, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    assert payload["traits"] == mock_traits()
    snapshot = snapshot_from_samples(mock_window(), transport="simulate", model_family="simulated", simulated=True)
    assert payload["features"] == pytest.approx(snapshot["bio_event"]["features"])
    assert "Safari" in payload["support"]["reason"] or payload["support"]["reason"] == "" or "Web Bluetooth" in payload["support"]["reason"]


def test_record_cli_writes_derived_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "taken.jsonl"
    assert muse_main(["simulate", "--consent", "--seconds", "2", "--out", str(out), "--raw"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["record"]["raw_eeg"] == "local-only"
    assert "samples" not in out.read_text(encoding="utf-8")
    raw = Path(body["record"]["raw_eeg_file"])
    assert raw.is_file()
    assert json.loads(raw.read_text(encoding="utf-8").splitlines()[0])["upload"] is False
