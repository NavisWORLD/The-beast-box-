"""Spark -> Beast Box signal bridge.

Label: AI-WRITTEN GLUE that calls CORY ORIGINAL code (vendored unmodified in beastbox_vendor/):
  * private_features.make_source / heart_features / FeatureStore   (beastbox/private_features.py:145-291)
  * routing.route / update_routed  — typed 12D/42D routing with a receipt per slot (beastbox/routing.py:145-197)
  * state_family.StateFamily       — dyn12 / dyn42 / dyn54 / tri3 (beastbox/state_family.py)
  * the PHOS readout  phos = mean(cos(PHI*x)) over dyn12 is Cory's formula from beastbox/cns.py:78 (re-typed here).

Direct plug-in: give `feature_dir` = the Beast Box BEASTBOX_FEATURE_DIR (default ~/.beastbox/features) and run the
Beast Box with BEASTBOX_LIVE_ROUTING=on. His LiveRouter (beastbox/live_routing.py:60-66) loads that FeatureStore
every turn, so the Spark's audio/light/heart features drive HIS StateFamily, not a copy.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Callable

from .beastbox_vendor.hashutil import sha256_obj
from .beastbox_vendor.private_features import FeatureStore, heart_features, make_source
from .beastbox_vendor.routing import ROUTING_SHA256, route, update_routed
from .beastbox_vendor.state_family import StateFamily
from .ppg import PpgWindow
from . import overlay as ov
from .psi import PsiLayer
from . import provenance

PHI = (1.0 + math.sqrt(5.0)) / 2.0


def phos(dyn12: list[float]) -> float:
    """Cory's PHOS reference scalar (beastbox/cns.py:78): a bounded phi-scaffold readout."""
    return sum(math.cos(PHI * x) for x in dyn12) / 12.0


class SparkBridge:
    def __init__(self, *, feature_dir: str | Path | None = None, receipts_path: str | Path | None = None,
                 clock: Callable[[], float] = time.time, sim_drive: bool = False, psi: bool = False):
        self.clock = clock
        # Frames flagged "simulated" are routed as kind=control (masked to 0.0 by Cory's router) unless sim_drive is
        # set for a demo/test; then they drive the state but every receipt says simulated_input=1.
        self.sim_drive = sim_drive
        self.saw_simulated = False
        self.store = FeatureStore(feature_dir) if feature_dir is not None else None
        self.receipts_path = Path(receipts_path) if receipts_path else None
        self.family = StateFamily()
        self.sources: dict[str, dict[str, Any]] = {}
        self.ppg = PpgWindow()
        self.heart_status: dict[str, Any] = {"valid": False, "reason": "no_ppg_yet", "label": provenance.PULSE}
        self.body: dict[str, Any] | None = None
        self.last_step: dict[str, Any] | None = None
        self.dropped = 0
        # Spark overlay bands (routing_spark_overlay.json): kept apart from Cory's sources and FeatureStore.
        self.overlay_sources: dict[str, dict[str, Any]] = {}
        self.overlay_x = [0.0] * ov.N_SLOTS
        # Optional CST psi readout (DERIVED, off by default, never drives hardware).
        self.psi = PsiLayer() if psi else None

    # ---- ingest ----
    def _put(self, name: str, source: dict[str, Any], simulated: bool = False) -> None:
        if simulated:
            self.saw_simulated = True
            source["provenance"]["simulated_input"] = 1
            if not self.sim_drive:
                source["kind"] = "control"
        if name in ov.SOURCES:
            self.overlay_sources[name] = source  # overlay only: never in Cory's route() input or FeatureStore
            return
        self.sources[name] = source
        if self.store is not None:
            self.store.put(name, source)  # Cory's FeatureStore re-checks the routing contract (_check_private)

    def put_crystal(self, T: dict[str, list[float | None]], now: float | None = None, simulated: bool = False) -> bool:
        feats = ov.crystal_features(T)
        if not feats:
            return False
        now = self.clock() if now is None else float(now)
        self._put("spark_crystal", ov.make_overlay_source("spark_crystal", feats, now, sensor="AS7341"), simulated)
        return True

    def handle(self, frame: dict[str, Any], now: float | None = None) -> str | None:
        """Take one validated Spark frame. Returns the source name it updated, if any."""
        now = self.clock() if now is None else float(now)
        ftype = frame.get("type")
        sim = frame.get("simulated") is True
        if ftype == "features":
            meta = {k: frame[k] for k in ("n", "rate") if isinstance(frame.get(k), (int, float))}
            src = make_source(frame["src"], frame["features"], site="on-device", captured_at=now, **meta)
            self._put(frame["src"], src, sim)
            return frame["src"]
        if ftype == "ppg":
            self.ppg.push(frame)
            result = self.ppg.analyse()
            self.heart_status = {k: v for k, v in result.items() if k != "ibis_ms"}
            self.heart_status["label"] = provenance.PULSE
            if result["valid"]:
                try:
                    feats = heart_features(result["ibis_ms"])
                except ValueError as exc:
                    self.heart_status.update(valid=False, reason=f"heart_features: {exc}")
                    return None
                self._put("heart", make_source("heart", feats, site="on-box", captured_at=now,
                                               sqi=float(result["sqi"]), beats=int(result["beats"])), sim)
                return "heart"
            return None  # invalid window: the heart band simply goes stale/missing, nothing is invented
        if ftype == "body":
            self.body = dict(frame)
            feats = ov.body_features(frame)
            if feats:
                self._put("spark_body", ov.make_overlay_source("spark_body", feats, now), sim)
                return "spark_body"
        return None

    # ---- one brain step ----
    def step(self, now: float | None = None) -> dict[str, Any]:
        now = self.clock() if now is None else float(now)
        routed = route(self.sources, now=now)
        states = update_routed(self.family, routed)
        d12 = states["dyn12"]
        over = ov.route_overlay(self.overlay_sources, now)
        self.overlay_x = ov.overlay_step(self.overlay_x, over["d"])
        merged = ov.merge(routed, over)
        summary = {
            "schema": "zeref-spark-step-v1", "at": round(now, 3), "routing_sha256": ROUTING_SHA256,
            "receipt_sha256": routed["receipt_sha256"], "tally": routed["tally"],
            "mask12": routed["mask12"], "mask42": routed["mask42"], "d12": routed["d12"],
            "dyn12": d12, "phos": phos(d12), "family_step": self.family.step,
            "state_sha256": sha256_obj(states["dyn54"]),
            "heart": self.heart_status, "label": f"{provenance.DERIVED} software state; {provenance.CONCEPT}",
            "simulated_inputs": self.saw_simulated,
            "overlay": {"schema": ov.OVERLAY["schema"], "overlay_sha256": ov.OVERLAY_SHA256, "d": over["d"],
                        "mask": over["mask"], "x": list(self.overlay_x), "receipts": over["receipts"]},
            "merged": merged,
            **({"simulation": provenance.SIMULATION} if self.saw_simulated else {}),
        }
        if self.psi is not None:
            summary["psi"] = self.psi.update(d12, routed["d12"], routed["mask12"])
        if self.receipts_path is not None:  # hashes and counts only, like beastbox/live_routing.py
            line = {k: summary[k] for k in ("schema", "at", "routing_sha256", "receipt_sha256", "tally", "state_sha256")}
            line["merged"] = {k: merged[k] for k in ("receipt_sha256", "overlay_sha256", "slots", "tally")}
            line["inputs"] = {n: {"feature_sha256": s["provenance"]["feature_sha256"], "kind": s["kind"]}
                              for n, s in sorted({**self.sources, **self.overlay_sources}.items())}
            self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
            with self.receipts_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, sort_keys=True) + "\n")
        self.last_step = summary
        return summary
