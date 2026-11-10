# ZEREF SPARK — companion robot CAD package v0.2

> **DESIGN TARGET — not printed or test-fitted.**  CONCEPT DESIGN / NOT BUILT HARDWARE.
> All dimensions are CAD **ESTIMATES**. Nothing here has been printed, wired, or bench-tested.
> Public copy uploaded to The-beast-box- at Cory's request (2026-11-10). Pulse = ESTIMATE, non-medical.
> MEASURED / DERIVED / ESTIMATE labels are kept throughout; simulation is not real measurement.


## Beast Spark Robot — start here
Zeref Spark is the Beast Box's connectable body: the host brain in `host/` runs Cory's vendored Beast Box
routing, and the ESP32-S3 firmware in `firmware/` streams on-device features and speech. **CONCEPT DESIGN / NOT BUILT HARDWARE.**

| Read | Link |
|---|---|
| Assembly guide (full, 37 MB) | [docs/Zeref_Spark_Assembly_Guide.pdf](docs/Zeref_Spark_Assembly_Guide.pdf) |
| Assembly guide (compact, 13 MB) | [docs/Zeref_Spark_Assembly_Guide_compact.pdf](docs/Zeref_Spark_Assembly_Guide_compact.pdf) |
| Teacher's guide | [docs/Zeref_Spark_Teachers_Guide.pdf](docs/Zeref_Spark_Teachers_Guide.pdf) |
| Design decisions (D1–D14) | [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) |
| Spec derived from the Beast Box | [docs/SPEC_FROM_BEASTBOX.md](docs/SPEC_FROM_BEASTBOX.md) |
| Brain architecture | [docs/BRAIN_ARCHITECTURE.md](docs/BRAIN_ARCHITECTURE.md) |
| Map of Cory's logic used | [docs/CORY_LOGIC_MAP.md](docs/CORY_LOGIC_MAP.md) |
| Electrical spec | [docs/electrical_spec.md](docs/electrical_spec.md) |
| Wiring / BOM / assembly / fit check | [wiring.md](wiring.md) · [BOM.csv](BOM.csv) · [ASSEMBLY.md](ASSEMBLY.md) · [FIT_CHECK.md](FIT_CHECK.md) |
| Firmware (zs-0.4.0) | [firmware/README.md](firmware/README.md) |
| Host bridge | [host/README.md](host/README.md) |

Status: 3 firmware builds compile (USB, Wi-Fi, kid/no-UV); 58 host tests pass on synthetic data. Nothing has
been flashed or wired yet.

Chibi companion robot whose nervous system is Cory's **Reality Bridge ESP32-S3 probe** (RB-001…RB-009,
pin contract unchanged from `NavisWORLD/Reality-bridge-universal-probe-engine-sim-`), with the brain on the
**Beast Box host** over USB serial / WebSocket :81.

## Contents
| Path | What |
|---|---|
| `ref/brief.md` | Working copy of the brief (**reconstruction** — original attachment was lost; see note inside) |
| `cad/zs_lib.py`, `cad/zs_parts.py` | Parametric CadQuery source. Change `P` in `zs_parts.py` and rebuild |
| `cad/build.py` | Builds every part → STEP + STL, writes `out/parts_meta.json` and the full assembly STEP |
| `cad/check.py` | Interference / clearance check → `out/fit_check.json` |
| `cad/render.py` | PyVista renders → `renders/` |
| `out/step/*.step` | One STEP per custom part, assembly coordinates (`out/step/proxy/` = purchased-part proxies) |
| `out/stl/*.stl` | One printable STL per custom part, seated on Z=0 |
| `out/stl/assembly_coords/` | STLs in assembled position (for viewers / slicer layout checks) |
| `out/ZEREF_SPARK_assembly.step` | Whole robot + proxies, one file |
| `BOM.csv`, `wiring.md`, `ASSEMBLY.md`, `FIT_CHECK.md` | Bill of materials, wiring, assembly steps, fit check |
| `renders/*.png` | Hero, front, side, back, top, exploded, internal views, crystal-station close-up (`10_crystal_station_closeup.png`) |

Rebuild: `python -m venv v && v/bin/pip install cadquery pyvista && v/bin/python cad/build.py && v/bin/python cad/check.py && xvfb-run v/bin/python cad/render.py`

## Architecture in one picture
- **Head** (150 × 128 × 118 mm): front/back shells split at y=0, clamped on a bulkhead by 4 × M3 (RB-008).
  Smoked visor; cyan happy-arc eye light pipes on a face carrier; magenta crown accents; speaker + MAX98357A, optional GNSS and LiPo on the bulkhead.
- **Ear pods**: left = INMP441 mic (RB-006), right = BH1750 light (RB-003); each with a 12-LED ring behind a violet rim diffuser. Rabbit ears screw onto the pods.
- **Torso** (88 × 76 × 100 mm egg): shells split at y=0 on a bulkhead that is the ESP32-S3 cradle (RB-001, back) and carries the sensor sled (IMU RB-002 + BME280 RB-004, front). 4 × M3 (RB-008).
  Chest core: cyan LED ring + diffuser, magenta/violet centre lens that is also the optional MAX30102 (RB-005) window.
- **Limbs**: static arms with mitten hands and stubby legs; every appendage has a flanged peg captured by the split shells (no glue, no visible screws).
- **Pedestal**: faceted hex "rock" (190 × 164.5 × 45 mm); a clear 12 mm tube floats the robot 12 mm up and carries the USB + station harness (RB-009) to the DevKit.
- **Battery bay (v0.2, approved)**: protected 1S 503450 LiPo in ZS-109 on the head bulkhead + PowerBoost 1000C (MCP73871 load-sharing charger + 5.2 V boost) + EN slide switch; battery sense on GPIO 5.
- **Crystal-reading station (v0.2)**: in the pedestal front. Crystal in a light-tight Ø26 cup over a borosilicate window; white / 365 nm UV / 940 nm IR LEDs below (MOSFETs on GPIO 1 / 2 / 21); AS7341 11-channel sensor looking down from the removable shield ZS-602 (I2C1 on GPIO 10 / 11, 0x39, pogo connector); reed-switch UV interlock (GPIO 40 sense, HIGH = seated); dark plug ZS-605 + PTFE white reference for calibration. Raw counts = MEASURED, ratios = DERIVED, crystal-type labels = ESTIMATE, no metaphysical claims.

## Decided (Cory, 2026-11-09)
- Height stays at 314 mm. LiPo bay with charger + protection + boost: designed. New pins LED 4, I2S1 15/16/7, amp mute 6: added to wiring.md as approved additions (his repo is not edited).

## Decisions (all made 2026-11-09)
Cory delegated every open decision ("You design it fully, I'm giving you that"). They are all in
[`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md), each marked "decided by Robot X under Cory's delegation 2026-11-09":
LED cap 8 %, Spark overlay routing band, all pins DECIDED, optional ψ layer, Wi-Fi build fixed, streamed speech, ESTIMATE
defaults for AS7341 / lux / finger / battery, dedicated station I2C, AS7341 kept, 1 A boost kept, wired dock kept,
child build without UV, 420 nm longpass glass, metal float tube. One item can't be decided by anyone but Cory:
the original brief is still missing (`ref/brief.md` stays a reconstruction).

## v0.3 docs (assembly guide, teacher's guide, electrical spec)
- `docs/Zeref_Spark_Assembly_Guide.pdf` (+ `.md` / `.html` source) — safety, tools, full BOM, print plan, parts catalog (every part labeled and shown), sub-assemblies, 16 numbered steps with highlighted images, fasteners, wiring and checks, Electrical Specifications, Stage 0–3 gates (PROPOSED), firmware bring-up, calibration, troubleshooting.
- `docs/Zeref_Spark_Teachers_Guide.pdf` (+ `.md` / `.html`).
- `docs/BOM_electrical.csv` — every R / C / D / F / Q / U / J / S with value, rating, tolerance, package, OB/ADD and ESTIMATE flags; also appended to `BOM.csv`.
- `docs/electrical_spec.md`, `docs/schematics/A–E` (.png + .svg), `docs/parts/` (70 part cards), `docs/img/` (exploded, sub-assemblies, steps).
- Build scripts: `docs/build/` (run with the CadQuery venv; renders need `xvfb-run`).
- v0.3 pin moves: IR gate GPIO42 → 21, shield sense GPIO47 → 40 (HIGH = shield seated).

## Brain, firmware and logic map (added 2026-11-09)
- [`docs/SPEC_FROM_BEASTBOX.md`](docs/SPEC_FROM_BEASTBOX.md): Spark spec derived from the Beast Box signal pipeline and learning rules
- [`docs/BRAIN_ARCHITECTURE.md`](docs/BRAIN_ARCHITECTURE.md): host brain diagram and who wrote what
- [`docs/CORY_LOGIC_MAP.md`](docs/CORY_LOGIC_MAP.md): every NavisWORLD repo and its core logic, with citations
- [`firmware/README.md`](firmware/README.md): Spark firmware zs-0.3.0 (built on Cory's probe v0.2, original kept intact)
- [`host/README.md`](host/README.md): `spark_brain` host bridge and tests
