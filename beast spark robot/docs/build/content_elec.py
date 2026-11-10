"""Electrical Specifications markdown (shared by assembly guide + standalone docs/electrical_spec.md)."""
import csv
ROOT = "/workspace/zeref-spark"
def table(h, rows):
    out = "| " + " | ".join(h) + " |\n|" + "---|" * len(h) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |\n"
    return out + "\n"
def rows():
    return list(csv.reader(open(f"{ROOT}/docs/BOM_electrical.csv")))[1:]
MODS = [
 ["U0 ESP32-S3 DevKitC-1 (RB-001)", "5 V in (on-board LDO → 3V3)", "≈100 mA typ, ≈350 mA Wi-Fi TX peak", "—", "USB (GPIO19/20), GPIO", "[Espressif ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) · [DevKitC-1 guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/)"],
 ["U3 ICM-42688-P (RB-002)", "3.3 V", "≈1 mA", "0x68 (0x69 if AD0 high)", "I2C0", "[TDK ICM-42688-P](https://invensense.tdk.com/products/motion-tracking/6-axis/icm-42688-p/)"],
 ["U4 BME280 (RB-004)", "3.3 V", "≈1 mA peak, µA avg", "0x76 (0x77)", "I2C0", "[Bosch BME280](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/)"],
 ["U5 BH1750 (RB-003)", "3.3 V", "0.12–0.19 mA", "0x23 (ADDR low)", "I2C0", "[ROHM BH1750FVI](https://www.mouser.com/datasheet/2/348/bh1750fvi-e-186247.pdf)"],
 ["U6 MAX30102 (RB-005, opt)", "3.3 V logic (LED 5 V on most breakouts)", "≈0.6 mA + LED pulses up to 50 mA", "0x57", "I2C0", "[ADI MAX30102](https://www.analog.com/en/products/max30102.html)"],
 ["U7 NEO-M9N GNSS (RB-007, opt)", "3.3 V", "≈30–40 mA acquiring", "—", "UART GPIO17/18", "[u-blox NEO-M9N](https://www.u-blox.com/en/product/neo-m9n-module)"],
 ["U8 INMP441 (RB-006)", "3.3 V", "1.4 mA", "—", "I2S0 GPIO12/13/14", "[TDK INMP441](https://invensense.tdk.com/products/digital/inmp441/)"],
 ["U9 MAX98357A (ZS-E05)", "5 V (2.5–5.5 V)", "≈3 mA idle, ≈250 mA at ~1 W/8 Ω (ESTIMATE)", "—", "I2S1 GPIO15/16/7, SD GPIO6", "[ADI MAX98357A](https://www.analog.com/en/products/max98357a.html)"],
 ["U10 AS7341 breakout (ZS-S01)", "VIN 3.3–5 V (on-board regs)", "≈0.3 mA active", "0x39 (fixed)", "I2C1 GPIO10/11, INT GPIO41", "[ams-OSRAM AS7341 DS000504](https://look.ams-osram.com/m/24266a3e584de4db/original/AS7341-DS000504.pdf)"],
 ["LED1–48 WS2812B", "5 V (VIH ≥ 0.7·VDD → needs U2)", "≈1 mA idle, 60 mA max each", "—", "1-wire 800 kHz, GPIO4", "[WS2812B (Adafruit PDF)](https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf)"],
 ["U2 SN74AHCT1G125", "5 V", "< 0.1 mA", "—", "buffer", "[TI SN74AHCT1G125](https://www.ti.com/product/SN74AHCT1G125)"],
 ["U1 PowerBoost 1000C", "in 5 V USB / 3.7 V LiPo; out 5.2 V", "≈1 A out (TPS61090), charge 1 A", "—", "EN, LBO pins", "[Adafruit guide](https://learn.adafruit.com/adafruit-powerboost-1000c-load-share-usb-charge-boost) · [MCP73871](https://cdn-shop.adafruit.com/datasheets/MCP73871.pdf) · [TPS61090](https://www.ti.com/product/TPS61090)"],
 ["Q1–Q3 AO3400A", "Vgs(th) 0.65–1.45 V", "5.7 A max (20 mA used)", "—", "GPIO1/2/21", "[AOS AO3400A](https://www.aosmd.com/res/datasheets/AO3400A.pdf)"],
 ["D1 USBLC6-2SC6 · D3 TPD4E05U06 · D2 SMBJ5.0A", "5 V lines", "—", "—", "protection", "[ST USBLC6-2](https://www.st.com/en/protections-and-emi-filters/usblc6-2.html) · [TI TPD4E05U06](https://www.ti.com/product/TPD4E05U06) · [Littelfuse SMBJ](https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj.aspx)"],
]
def md():
    R = rows()
    res = [r for r in R if r[0].startswith("R")]
    cap = [r for r in R if r[0].startswith("C")]
    oth = [r for r in R if not (r[0].startswith("R") or r[0].startswith("C"))]
    s = "# Electrical Specifications\n\n"
    s += "> **DESIGN TARGET — not built or bench-tested.** Values marked **ESTIMATE** are calculated from datasheet typicals, not measured. **[OB]** = part already on a bought module (do not add). **[ADD]** = part you add. **DNP** = do not populate unless the check says so. Designators match `docs/BOM_electrical.csv` and the schematics.\n\n"
    s += "> **Changed 2026-11-09:** LED brightness cap 10 % → **8 %** everywhere (firmware 20/255), decided by Robot X under Cory's delegation (docs/DESIGN_DECISIONS.md D1). Peak 5V_SYS budget 1.03 A → 0.97 A (ESTIMATE).\n\n"
    s += """## Pin map — DECIDED (Robot X under Cory's delegation, 2026-11-09)

All pins below are **DECIDED** (docs/DESIGN_DECISIONS.md D3). REPO = Cory's Reality Bridge Probe v0.2 pins, unchanged. The firmware (`firmware/zeref_spark_fw/include/spark_pins.h`, zs-0.4.0) uses exactly this table. Not yet checked on a powered board.

| Signal | GPIO | Goes to | Status |
|---|---|---|---|
| I2C0 SDA / SCL | 8 / 9 | ICM-42688-P, BME280, BH1750, MAX30102 | REPO |
| I2S0 BCLK / WS / SD | 12 / 13 / 14 | INMP441 mic | REPO |
| GNSS RX / TX | 17 / 18 | GNSS (unwired by default, `SPARK_GNSS_WIRED=0`) | REPO |
| LED data | 4 | 74AHCT125 → 48 × WS2812B (cap 8 %) | DECIDED (approved by Cory) |
| I2S1 BCLK / LRC / DIN | 15 / 16 / 7 | MAX98357A (tones + streamed speech) | DECIDED (approved by Cory) |
| Amp SD (mute) | 6 | MAX98357A SD, LOW = muted, muted at boot | DECIDED (approved by Cory) |
| Battery sense | 5 (ADC1_CH4) | 100 k / 100 k divider, VBAT = 2 × Vadc | DECIDED |
| I2C1 SDA / SCL | 10 / 11 | AS7341 (0x39) via pogo, 100 kHz | DECIDED |
| AS7341 INT | 41 | AS7341 INT, open drain | DECIDED |
| White / UV 365 / IR 940 gate | 1 / 2 / 21 | AO3400A Q1 / Q2 / Q3 | DECIDED |
| Shield sense | 40 | HIGH = shield seated (after reed S1) | DECIDED |
| USB D+ / D− | 19 / 20 | native USB CDC (host link) | DevKit |

"""
    s += "## Voltage rails\n\n" + table(["Rail", "Range", "Source", "Max load", "Notes"], [
        ["VBUS_IN / VBUS", "4.75–5.25 V", "USB-C J1 → F1 (2 A hold)", "≈1.87 A peak (ESTIMATE)", "Needs a **5 V / 3 A** USB-C supply. A PC USB2 port (0.5 A) is NOT enough."],
        ["VBAT", "3.0–4.2 V (3.7 V nom.)", "BT1 protected LiPo", "≈1.5 A to the boost at 1 A out (ESTIMATE)", "Cell PCM cuts at ≈2.5–3.0 V"],
        ["VS (load-share)", "VBUS or VBAT", "MCP73871 inside U1", "—", "internal to the PowerBoost"],
        ["5V_SYS", "5.2 V ±2%", "U1 TPS61090 boost", "≈1 A", "Peak budget ≈0.97 A with the 8 % LED cap — tight, see power budget"],
        ["3V3", "3.3 V", "DevKit on-board LDO [OB]", "keep external load < 100 mA (ESTIMATE)", "feeds I2C0 sensors, mic, GNSS"],
        ["AS7341 internal", "3.3 V / 1.8 V", "breakout regulators [OB]", "—", "fed from VBUS through the pogo"],
        ["UV_5V", "0 V or VBUS", "reed S1 (shield seated)", "≈21 mA", "hardware UV interlock"]])
    s += "## Power budget (ESTIMATE)\n\n**5V_SYS (boost output, ≈1 A limit)**\n\n" + table(["Load", "Typical", "Peak", "Basis"], [
        ["ESP32-S3 + Wi-Fi", "0.10 A", "0.35 A", "datasheet TX burst"], ["WS2812B quiescent (48 × ≈1 mA)", "0.05 A", "0.05 A", ""],
        ["WS2812B light, 8 % brightness cap (firmware 20/255)", "0.08 A", "0.23 A", "48 × 60 mA × 8 %"], ["MAX98357A + 8 Ω speaker", "0.03 A", "0.25 A", "≈1 W peaks"],
        ["Sensors + mic (via 3V3 LDO)", "0.01 A", "0.05 A", "MAX30102 LED pulses"], ["GNSS (optional)", "0.03 A", "0.04 A", "acquisition"],
        ["**Total 5V_SYS**", "**≈0.30 A**", "**≈0.97 A**", "**tight vs ≈1 A** with the 8 % LED cap (DECIDED, D1); drop GNSS if brown-outs"]])
    s += "**VBUS (USB-C input)**\n\n" + table(["Load", "Typical", "Peak"], [["MCP73871 charger + load-share (input limit)", "0.6 A", "1.8 A"], ["Station LEDs (one at a time, 20 mA)", "0.00 A", "0.02 A (0.06 A if all on)"], ["AS7341 breakout", "<0.01 A", "<0.01 A"], ["**Total VBUS**", "**≈0.6 A**", "**≈1.87 A**"]])
    s += "Battery runtime (ESTIMATE): 1000 mAh × 3.7 V × 0.85 boost efficiency / (5.2 V × 0.30 A) ≈ **2.0 h typical**, ≈0.6 h at sustained peak.\n\n"
    s += "## Resistors (every one)\n\n" + table(["Ref", "Sheet", "Value", "Pkg", "Power", "Tol.", "OB/ADD", "ESTIMATE?", "Calculation / purpose"], [[r[0], r[1], r[2], r[4], r[5], r[6], r[8], r[9], r[11]] for r in res])
    s += "### LED current-limit resistors, worked: R = (V − Vf) / If, P = If² · R\n\n" + table(["LED", "V supply", "Vf (ESTIMATE)", "If target", "R calc", "Chosen (E12)", "Actual If", "P in R"], [
        ["D4 white", "5.0 V", "3.0 V", "20 mA", "(5.0−3.0)/0.020 = 100 Ω", "R20 100 Ω", "20.0 mA", "0.040 W"],
        ["D5 UV 365 nm", "5.0 V", "3.6 V", "20 mA", "(5.0−3.6)/0.020 = 70 Ω", "R21 68 Ω", "20.6 mA", "0.029 W"],
        ["D6 IR 940 nm", "5.0 V", "1.3 V", "20 mA", "(5.0−1.3)/0.020 = 185 Ω", "R22 180 Ω", "20.6 mA", "0.076 W"]])
    s += "Use 0805 0.125 W parts (≥ 1.6× margin). Check your LEDs' real Vf at 20 mA and recompute; AO3400A drop (≈0.7 mV at 20 mA) is negligible.\n\n"
    s += "### Other resistor math\n\n- **Battery sense (R1/R2 100 k / 100 k, C5 100 nF):** Vadc = VBAT × 100k / 200k → 1.50 V (3.0 V) … 2.10 V (4.2 V). Inside the ESP32-S3 ADC 11 dB range (≈0–2.9 V usable, ESTIMATE). Divider current 4.2 V / 200 kΩ = 21 µA (≈0.5 mAh/day). Firmware: VBAT = 2 × Vadc (calibrate with a multimeter once).\n"
    s += "- **I2C0 pull-ups (R3/R4 2.2 kΩ):** rise time tr = 0.847 × R × Cbus = 0.847 × 2.2 kΩ × 100 pF ≈ 186 ns (I2C fast mode limit 300 ns). Most breakouts already carry 10 kΩ (or 4.7 kΩ) each — measure SDA→3V3 with power off: if ≤ 3.3 kΩ already, leave R3/R4 out (DNP).\n"
    s += "- **I2C1 pull-ups (R9/R10 4.7 kΩ ∥ on-board 10 kΩ = 3.2 kΩ):** longer pogo + tube run (≈30 cm, ESTIMATE ≈150 pF): tr ≈ 0.847 × 3.2k × 150 pF ≈ 0.41 µs → run I2C1 at **100 kHz** (limit 1 µs). R11/R12 100 Ω series limit hot-plug current.\n"
    s += "- **MOSFET gates:** R14–R16 100 Ω limit GPIO edge current into the gate; R17–R19 100 kΩ hold the LEDs OFF while the ESP32 boots (pins float).\n"
    s += "- **Shield sense (R23 12 kΩ / R24 20 kΩ):** shield seated → S1 closed → SHIELD_SENSE = 5.0 × 20/(12+20) = 3.13 V (HIGH; 3.28 V at 5.25 V — below 3.6 V abs. max). Shield off → R24 pulls to 0 V (LOW). Current 0.16 mA.\n"
    s += "- **Amp boot-mute (R7 22 kΩ):** with the breakout's 1 MΩ SD pull-up [OB] to VIN: V = 5 × 22k / 1.022M = 0.108 V < 0.16 V shutdown threshold → amp OFF until GPIO6 drives HIGH. ESTIMATE — verify your breakout's pull-up value.\n"
    s += "- **NeoPixel data (R8 330 Ω):** in the 300–500 Ω range; sits at the first LED's DIN to damp ringing on the 3.3→5 V buffered line.\n\n"
    s += "## Capacitors (every one)\n\n" + table(["Ref", "Sheet", "Value", "Type", "Pkg", "Voltage", "Tol.", "OB/ADD", "Location / purpose"], [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[8], r[10] + (" — " + r[11] if r[11] else "")] for r in cap])
    s += "Rule: voltage rating ≥ 2× rail for MLCC (DC-bias derating), ≥ 1.6× for electrolytics/polymer. Watch polarity on C2, C3, C12, C15–C18.\n\n"
    s += "## Diodes, fuses, switches, ICs, connectors\n\n" + table(["Ref", "Sheet", "Part", "Type", "Pkg", "Rating", "OB/ADD", "Note"], [[r[0], r[1], r[2], r[3], r[4], r[5], r[8], r[11]] for r in oth])
    s += "**Flyback diodes:** none needed — there are no motors, relays or other inductive loads; the speaker is driven by a class-D bridge with its own protection. **ESD/TVS:** D1 (USB data), D2 (VBUS surge), D3 (exposed pogo pins). **Fuses:** F1 on VBUS, F2 (optional) on the battery lead, plus the cell's own PCM.\n\n"
    s += "## Connectors and pitches\n\n" + table(["Where", "Connector", "Pitch", "Pins / note"], [
        ["I2C breakouts (U3–U6, U10 side)", "JST-SH (STEMMA QT / Qwiic)", "1.0 mm", "4: GND, 3V3, SDA, SCL"],
        ["Battery BT1 → U1", "JST-PH", "2.0 mm", "2 (check polarity — no standard!)"],
        ["LED rings / eye boards", "JST-PH", "2.0 mm", "3: 5V, DIN/DOUT, GND"],
        ["Head ↔ torso, torso ↔ tube harness joints", "JST-PH (or JST-GH for locking)", "2.0 mm (1.25 mm GH)", "split into ≤ 6-pin groups"],
        ["DevKit headers", "Dupont female", "2.54 mm", "or solder directly"],
        ["Station shield ↔ pedestal J2", "4-pin magnetic pogo", "2.54 mm", "VBUS, GND, SDA1_P, SCL1_P"],
        ["Pedestal power/data in J1", "USB-C receptacle breakout", "—", "5.1 kΩ CC [OB]"],
        ["Speaker", "JST-PH or solder", "2.0 mm", "2"]])
    s += "## Wire gauge per run\n\n" + table(["Run", "Current (peak)", "Wire", "Length (ESTIMATE)"], [
        ["VBUS / GND: J1 → tube → torso → head (U1)", "≤ 1.87 A", "2 × 26 AWG silicone in parallel each (or 1 × 22 AWG if it fits the tube)", "≈30 cm"],
        ["5V_SYS / GND: U1 → torso → LEDs, DevKit", "≤ 1.03 A", "2 × 26 AWG in parallel", "≈15 cm"],
        ["BAT: BT1 → U1", "≤ 1.5 A", "24 AWG", "≤ 75 mm"],
        ["LED ring 5V/GND branches", "≤ 0.15 A each", "26 AWG", "≤ 15 cm"],
        ["Speaker", "≤ 0.4 A", "26 AWG", "≤ 10 cm"],
        ["All signals (I2C, I2S, gates, sense, LED data)", "< 10 mA", "30 AWG silicone", "—"],
        ["USB D+ / D−", "data", "30 AWG twisted pair, ≈ 1 twist/cm", "keep < 30 cm"],
        ["Station LED supply (VBUS in pedestal)", "≤ 60 mA", "28–30 AWG", "≤ 10 cm"]])
    s += "26 AWG silicone ≈ 0.134 Ω/m: 30 cm at 1.87 A on a single wire ≈ 75 mV drop each way — doubled wires halve it.\n\n"
    s += "## Harness: tube (pedestal ↔ torso) — 11 conductors (ESTIMATE fit in 8 mm ID)\n\n" + table(["#", "Signal", "Gauge"], [[1, "VBUS", "26 (×2 if room)"], [2, "GND", "26 (×2 if room)"], [3, "USB D+", "30 twisted"], [4, "USB D−", "30 twisted"], [5, "SDA1", "30"], [6, "SCL1", "30"], [7, "G_WHITE (GPIO1)", "30"], [8, "G_UV (GPIO2)", "30"], [9, "G_IR (GPIO21)", "30"], [10, "AS_INT (GPIO41)", "30"], [11, "SHIELD_SENSE (GPIO40)", "30"]])
    s += "## Per-module specifications\n\n" + table(["Module", "Supply", "Current", "I2C address", "Interface / pins", "Datasheet (verify revision)"], MODS)
    s += "I2C address map: **bus 0** 0x23, 0x57, 0x68, 0x76 — no conflicts; **bus 1** 0x39 alone. All datasheet links were correct when written; always check the current revision.\n\n"
    s += "## Schematics\n\nDrawn in net-label style: **same net name = connected**. [OB] on-board, [ADD] added.\n\n"
    for f, t in [("A_power", "Sheet A — Power"), ("B_i2c0_sensors", "Sheet B — I2C0 sensors + GNSS"), ("C_audio", "Sheet C — Audio"), ("D_led_chain", "Sheet D — LED chain"), ("E_crystal_station", "Sheet E — Crystal station")]:
        s += f'<div class="sch"><img src="schematics/{f}.png"><p class="cap">{t} (SVG: docs/schematics/{f}.svg)</p></div>\n\n'
    return s
if __name__ == "__main__":
    open(f"{ROOT}/docs/electrical_spec.md", "w").write(md().replace('src="schematics/', 'src="schematics/'))
    print("ok")
