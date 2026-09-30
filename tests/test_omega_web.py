"""OMEGA web routes expose real telemetry (no fake activity)."""

from beastbox.cosmic_web import CosmicApp


def test_omega_routes(tmp_path):
    app = CosmicApp(tmp_path / "cosmic")
    try:
        status, body = app.dispatch("GET", "/api/omega/recovery")
        assert status == 200
        assert body["schema"] == "omega-recovery-map-v1"
        status, body = app.dispatch(
            "POST", "/api/omega/step", {"text": "Remember the sunflower code is marigold"}
        )
        assert status == 200
        assert [s["stage"] for s in body["stages"]][:3] == ["sensors", "cns7", "state_12d"]
        status, body = app.dispatch("GET", "/api/omega/experiments")
        assert status == 200
        assert set(body) == {"h1", "h2", "h3"}
    finally:
        pass
