import sys, csv, json, subprocess, re, markdown
sys.path.insert(0, "/workspace/zeref-spark/docs/build")
from partmeta import M
from steps import S
from content_elec import md as elec_md, table
ROOT = "/workspace/zeref-spark"; D = f"{ROOT}/docs"
LABEL = "DESIGN TARGET — not printed or test-fitted · CONCEPT DESIGN / NOT BUILT HARDWARE"
CREDIT = "System logic & concept: Cory Davis (NavisWORLD) · CAD geometry: AI-generated (CadQuery) · PX = third-party module proxy"
A = open(f"{ROOT}/ASSEMBLY.md").read()
def sect(start, end):
    a = A.index(start); b = A.index(end, a + 1) if end else len(A)
    return A[a:b]
def pn(s): return s.split("_")[0] if s.startswith("ZS") else "PX"

CSS = """
@page { size: Letter; margin: 15mm 13mm 17mm 13mm;
  @top-center { content: "%LABEL%"; font: 7.5pt sans-serif; color: #b0006a; }
  @bottom-left { content: "%CREDIT%"; font: 7pt sans-serif; color: #555; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt sans-serif; } }
body { font-family: 'DejaVu Sans', sans-serif; font-size: 9.6pt; line-height: 1.38; color: #111827; }
h1 { color: #101633; border-bottom: 3px solid #ff2d9b; padding-bottom: 3px; page-break-before: always; font-size: 19pt; }
h1.nobreak, .cover h1 { page-break-before: avoid; border: none; }
h2 { color: #1d2a6b; font-size: 13.5pt; margin-top: 16px; } h3 { color: #3b2a6b; font-size: 11pt; }
table { border-collapse: collapse; width: 100%; font-size: 7.8pt; margin: 6px 0 10px; page-break-inside: auto; }
th { background: #101633; color: #e7ecff; text-align: left; padding: 3px 4px; } td { border-bottom: 1px solid #dde1ee; padding: 2.5px 4px; vertical-align: top; }
tr { page-break-inside: avoid; } tr:nth-child(even) td { background: #f6f7fb; }
img { max-width: 100%; } .sch { page-break-inside: avoid; margin: 8px 0; } .sch img { width: 100%; border: 1px solid #ccd; }
.cap { font-size: 8pt; color: #555; text-align: center; margin: 2px 0 8px; }
.step { page-break-before: always; } .step img { width: 100%; border: 1px solid #ccd; }
.box { border-left: 4px solid #ff2d9b; background: #fff3fa; padding: 6px 10px; margin: 8px 0; }
.chk { border-left: 4px solid #0a9d6e; background: #effbf6; padding: 6px 10px; margin: 8px 0; }
.warn { border: 2px solid #d12; background: #fff0f0; padding: 8px 12px; margin: 8px 0; }
.cards { display: grid; grid-template-columns: 1fr; gap: 6px; } .cards img { width: 100%; height: auto; page-break-inside: avoid; border: 1px solid #ddd; }
.cover { text-align: center; } .cover img { width: 82%; } .tag { display: inline-block; background: #101633; color: #7ff6ff; padding: 4px 10px; border-radius: 4px; margin: 3px; font-size: 9pt; }
code { background: #eef; padding: 0 3px; font-size: 8.6pt; } pre { background: #f4f5fa; padding: 6px; font-size: 7.6pt; white-space: pre-wrap; }
""".replace("%LABEL%", LABEL).replace("%CREDIT%", CREDIT)

def to_pdf(md_text, name, title):
    open(f"{D}/{name}.md", "w").write(md_text)
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "md_in_html"])
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>"
    open(f"{D}/{name}.html", "w").write(html)
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={D}/{name}.pdf", f"file://{D}/{name}.html"], check=True, capture_output=True, timeout=300)
    print("pdf", name)

# ------------------------------------------------------------------ ASSEMBLY GUIDE
bom = list(csv.reader(open(f"{ROOT}/BOM.csv")))
legend = json.load(open(f"{D}/img/exploded_legend.json"))
g = []
g.append(f"""<div class="cover" markdown="1">
<h1 class="nobreak">ZEREF SPARK — Assembly Guide</h1>

**Chibi companion robot on a floating pedestal with a crystal-reading station · v0.4 (all decisions made, firmware zs-0.4.0)**

<span class="tag">DESIGN TARGET — not printed or test-fitted</span> <span class="tag">CONCEPT DESIGN / NOT BUILT HARDWARE</span>

<img src="../renders/01_hero_three_quarter.png">

**System logic, architecture and concept: Cory Davis (NavisWORLD)** — Reality Bridge / Beast Box (“the brain lives on the host; models are mouths”).
CAD geometry, renders and this guide were **AI-generated** from Cory's logic (CadQuery). Parts marked **PX** are **third-party modules** shown as simplified proxy shapes — measure your purchased boards.
Height target 314 mm (robot) · ≈371 mm with pedestal. Every dimension and electrical value marked ESTIMATE is unverified.
</div>
""")
g.append("""# 1. Safety — read before you start

<div class="warn" markdown="1">

**Adult supervision is required for every soldering, LiPo, heat-set and UV step.**
</div>

## LiPo battery (BT1)
- Use only a **protected** 1S cell (PCM board under the wrap). Never puncture, bend, crush or screw into it; mount with foam tape only.
- Charge only through the PowerBoost (U1) — never a bare supply. Never charge unattended or on a flammable surface; a LiPo-safe bag is recommended for first charges.
- Check polarity of the JST-PH lead before connecting (no industry standard). A reversed cell can destroy U1 instantly.
- Swollen, hot, hissing or smelling cell → disconnect (if safe), move outside onto sand/concrete, do not reuse.
- Keep F2 (optional) and the cell PCM in place; never bypass them.

## UV-A 365 nm (D5)
""" + sect("- 365 nm is barely visible", "### Calibration procedure") + """
## Soldering
- Ventilate / use a fume extractor; lead-free solder recommended; wash hands after.
- Iron rests in its stand; the tip is ~350 °C. Wear eye protection when clipping leads.
- Never solder on a powered circuit or with the LiPo connected.

## Heat-set inserts
- Insert tip ≈ 220 °C (PLA) / 245 °C (PETG). The brass stays hot for over a minute — use tweezers, never fingers.
- Push straight; if an insert tilts, reheat and correct immediately.

## Electrical
- USB-C supply: 5 V / 3 A. Do not connect the DevKit's own USB 5 V to the robot while 5V_SYS is powered (back-feed). The USB pigtail carries D+/D−/GND only.
- Before first power-on of each stage, measure 5V↔GND and 3V3↔GND resistance: > 1 kΩ (after caps charge).
""")
g.append("""# 2. Tools and consumables

| Tool | Used for |
|---|---|
| FDM printer (≥ 200 × 200 mm bed), PETG + PLA (+ clear resin optional) | all printed parts |
| Temperature-controlled soldering iron, fine tip, lead-free solder, flux, desoldering braid | wiring, passives |
| Heat-set insert tip for M3 | ZS-F01 inserts |
| Multimeter (V, Ω, continuity, diode test) | every check |
| Hex/Phillips drivers (M2, M2.5, M3), small pliers, flush cutters | fasteners |
| Wire strippers 22–30 AWG, crimp tool for JST-PH / JST-SH (or pre-crimped leads) | harness |
| Heat-shrink 1.5–6 mm, Kapton tape, foam tape, hot-glue gun, CA glue, clear silicone | insulation, mounting |
| Hobby knife, files, 400–1000 grit paper, isopropyl alcohol | cleanup, window cleaning |
| UV-blocking safety glasses (UV400, EN 166 / ANSI Z87) | any bench UV work |
| LiPo-safe bag, fume extractor | safety |
| Computer with VS Code + PlatformIO, USB-C data cable (RB-009), 5 V / 3 A USB-C supply | firmware, power |
| PTFE white reference disc (ZS-S12) and dark plug ZS-605 | calibration |
""")
g.append("# 3. Bill of materials (complete)\n\nMechanical, module and printed rows first, then every electrical/passive part (v0.3). Full electrical detail: `docs/BOM_electrical.csv`.\n\n" + table(bom[0], bom[1:]))
g.append("# 4. Print plan\n\n" + sect("| Part | Material | Orientation / notes |", "## 2. Pre-assembly") + "\n### Per-part settings (from the parts catalog)\n\n" +
         table(["Part", "Name", "Material / colour", "Orientation / settings", "Qty"], [[pn(s), M[s][0], M[s][1], M[s][2], M[s][3]] for s in M if s.startswith("ZS")]) +
         "Test-print first: one leg peg + socket, one pod peg, one split boss with insert, the neck coupler and the shield-groove ring. Adjust clearances before printing full shells.\n")
g.append("# 5. Parts catalog — every part labeled and shown\n\n## Exploded view, every part numbered\n\n<img src='img/exploded_numbered.png'>\n\n" +
         table(["#", "Part no.", "Name", "Type"], [[n, pn(s), nm, "printed (AI-generated CAD)" if s.startswith("ZS") else "third-party module proxy"] for n, s, nm in legend]) +
         "\n## Part cards\n\nEach card shows part number, name, material, print orientation, quantity, fasteners and sub-assembly. Printed parts = AI-generated CAD; PX = third-party module proxy (envelope ESTIMATE).\n\n" +
         "<div class='cards'>" + "".join(f"<img src='parts/{s}.png'>" for s in sorted(M, key=lambda s: (s[:2] != 'ZS', s))) + "</div>\n")
g.append("# 6. Sub-assemblies\n\n" + "".join(f"## {t}\n\n<img src='img/{f}.png'>\n\n" for f, t in [("sub_head", "Head (incl. power bay)"), ("sub_ear_pods", "Ear pods"), ("sub_torso_chest", "Torso / chest"), ("sub_limbs", "Limbs"), ("sub_pedestal_station", "Pedestal + crystal station"), ("sub_power", "Power")]))
st = "# 7. Assembly steps\n\nEach step: image (highlighted = new parts), fasteners, actions, wiring for that step (with its schematic sheet), and a check you must pass before moving on.\n\n"
sheetmap = {1: None, 2: "D_led_chain", 3: "D_led_chain", 4: "A_power", 5: "C_audio", 6: "B_i2c0_sensors", 7: None, 8: "A_power", 9: "B_i2c0_sensors", 10: "D_led_chain", 11: None, 12: "A_power", 13: "E_crystal_station", 14: "E_crystal_station", 15: "E_crystal_station", 16: None}
for i, s in enumerate(S, 1):
    st += f"<div class='step' markdown='1'>\n\n## Step {i} — {s['t']}\n\n<img src='img/step_{i:02d}.png'>\n\n**Parts added:** " + ", ".join(f"{pn(n)} {M[n][0]}" for n in s["new"]) + "\n\n"
    st += f"**Fasteners:** {s['fas']}\n\n**Do:**\n\n" + "".join(f"{k}. {a}\n" for k, a in enumerate(s["act"], 1))
    st += f"\n**Wiring:** {s['wire']}\n\n"
    if sheetmap[i]: st += f"<div class='sch'><img src='schematics/{sheetmap[i]}.png'><p class='cap'>Wiring for this step: docs/schematics/{sheetmap[i]} (pin labels = ESP32-S3 GPIO numbers)</p></div>\n\n"
    st += f"<div class='chk' markdown='1'>**CHECK before moving on:** {s['chk']}</div>\n\n</div>\n\n"
g.append(st)
g.append(elec_md().replace("# Electrical Specifications", "# 8. Electrical Specifications", 1))
g.append("""# 9. Stage gates 0–3 (PROPOSED — reconstructed)

<div class="box">The original brief's Stage 0–3 text was not available to this build; these gates are a <b>reconstruction</b> from the system logic and must be confirmed by Cory.</div>

| Stage | Build state | Gate (all must pass) |
|---|---|---|
| **0 — bare DevKit** | ESP32-S3 on USB only, no wiring | Firmware flashes; native USB prints the boot line + self-test JSON; host `spark_brain` receives frames (Wi-Fi build only: softAP visible when SPARK_AP_PASS is set, WebSocket :81 streams JSON) |
| **1 — sensor bench harness** | U3–U8 on a breadboard / JST-SH chain | I2C0 scan = 0x23, 0x57, 0x68, 0x76 (present ones); every sensor value plausible and labelled MEASURED; mic RMS rises when you speak; GNSS NMEA (if fitted) |
| **2 — power + LEDs + audio in the body** | Steps 1–11 | SW1 OFF → 5V_SYS < 0.3 V; ON → 5.1–5.25 V; battery reading within 0.05 V of a meter; 48 LEDs light in order at ≤ 8 % (firmware cap); amp silent at boot, tone plays when unmuted; no brown-out during LED + audio + Wi-Fi together (log min 5V_SYS) |
| **3 — full assembly + station** | Steps 12–16 | Shield interlock: shield off → UV_5V = 0 V and SHIELD_SENSE LOW; shield on → 0x39 on I2C1 + HIGH; dark/white calibration passes repeatability (§11); robot height 314 mm ±2 |
""")
g.append("""# 10. Firmware flash and bring-up tests

Spark firmware **zs-0.4.0** is in this package at `firmware/zeref_spark_fw/` (PlatformIO, Arduino framework). It is built on Cory's Reality Bridge Probe v0.2, which is kept unchanged in `firmware/reality_bridge_probe_v0.2_original/` (his repo is not edited). It covers every DECIDED pin: LEDs (GPIO4, cap 8 %), amp I2S1 15/16/7 + mute 6 (tones and streamed speech), battery GPIO5, station I2C1 10/11 + INT 41, gates 1/2/21, shield sense 40, UV guard. Compile status: USB build and Wi-Fi build both **compile**; **never run on a board yet**.

1. Install VS Code + PlatformIO. Open `firmware/zeref_spark_fw`.
2. Connect the DevKit's **USB** (native) port — the firmware talks over native USB CDC (needed for speech audio). If upload fails: hold BOOT, tap RESET, release BOOT.
3. `pio run -e zeref-spark -t upload` then `pio device monitor`. Expect the line `Zeref Spark zs-0.4.0 (Reality Bridge Probe 0.2.0 base)` and a self-test JSON.
4. On the host: `cd host && python -m spark_brain serial /dev/ttyACM0` (the brain lives there — the robot is the nervous system). Optional Wi-Fi: build with `SPARK_AP_PASS='8+ chars' pio run -e zeref-spark-wifi` (Wi-Fi accepts speech lines only; UV/SCAN stay USB-only).

""")
g.append("""| Test | How | Pass |
|---|---|---|
| I2C0 scan | scanner sketch / firmware self-test | expected addresses only |
| I2C1 scan | `Wire1.begin(10, 11, 100000)` | 0x39 only when shield seated |
| Battery | read GPIO5 ×2, compare to meter | ±0.05 V |
| LEDs | chain test at 4 % then 8 % (`BRIGHT 10`, then `BRIGHT 20`) | 48 LEDs, correct order: chest → eyes → pods → crown |
| Amp mute | boot, measure SPK1 | silent until GPIO6 HIGH |
| Speech | host: `python -m spark_brain serial PORT --speak --say 'hello'` after sending `MUTE 0` | clear speech (local piper TTS, or labelled stub tones); amp mutes about 60 ms after the end; `speech` frames show no underruns |
| Gates | toggle GPIO1/2/21 with shield seated | each LED alone; UV never with shield off |
| Shield sense | lift / seat | GPIO40 LOW / HIGH |
| Brown-out | LEDs 8 % + speech audio + Wi-Fi TX for 60 s | no reset; 5V_SYS ≥ 4.9 V |

Firmware honesty labels: raw counts **MEASURED**, ratios **DERIVED**, any classification **ESTIMATE** (with confidence). No metaphysical claims.
""")
g.append("# 11. Crystal station calibration\n\n" + sect("Fix the settings first", "## 7. Verification") )
g.append("""# 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing powers with SW1 ON | EN shorted / switch wired inverted; cell PCM tripped | check SW1 (closed = OFF); plug USB to reset PCM |
| Resets when LEDs flash or audio plays | 5V_SYS peak ≈ 1 A limit; missing C3/C15 | cap LEDs at 8 %, lower volume, check bulk caps, check 2× 26 AWG power wires |
| First LED flickers / random colours | no level shift, R8 missing, GND not shared | fit U2 + R8, run GND alongside data |
| I2C0 device missing | wrong address jumper, swapped SDA/SCL, no pull-ups | scan, check ADDR pins, measure pull-up resistance |
| I2C bus hangs | too-strong pull-ups stacked (< 1 kΩ) | remove R3/R4 or breakout pull-ups |
| AS7341 not found | shield not seated; pogo dirty; I2C1 too fast | reseat, clean pads, run at 100 kHz |
| UV never lights | reed open (magnet misplaced) — this is the interlock working | check SHIELD_SENSE ≈ 3.1 V with shield on |
| UV lights with shield OFF | **STOP** — interlock wiring wrong | power off; S1 must be in series with the UV supply |
| Station readings drift | warm-up, ambient leak, temperature | 10 min warm-up, repaint shield inside, log temperature |
| Hum / hiss in speaker | ground loop / I2S edges | shorten wires, fit R5/R6, star ground at U1 |
| Battery % jumps | ADC noise / no C5 | fit C5, average 16 samples, calibrate |
| Brown-out from PC USB | PC port 0.5 A | use a 5 V / 3 A USB-C supply |

## Known gaps (honest list)
- Nothing has been printed, test-fitted, powered or measured. All ESTIMATE values need bench confirmation.
- PX proxies are simplified envelopes — measure your boards.
- Stage 0–3 gates and the brief are reconstructions.
- All pins are DECIDED (Robot X under Cory's delegation, 2026-11-09), incl. IR gate 21 and shield sense 40 (HIGH = seated) — still unverified on a powered board.
- 5V_SYS peak ≈ 0.97 A vs ≈ 1 A boost limit with the 8 % LED cap — tight.
- Firmware zs-0.4.0 (LEDs, amp + streamed speech, battery, station, UV guard) compiles (USB and Wi-Fi builds) but has never run on a board.
- AS7341 gains, lux map, finger threshold and battery calibration are ESTIMATE defaults until checked on hardware.
""")
to_pdf("\n\n".join(g), "Zeref_Spark_Assembly_Guide", "ZEREF SPARK Assembly Guide")
