# ZEREF SPARK — Wiring (v0.4, all pins DECIDED)

**DESIGN TARGET — not printed or test-fitted. Not bench-validated.**
Low-voltage prototype electronics only. The MAX30102 optical channel is **not a medical device**.
The crystal station measures light; it makes **no** metaphysical, healing or "energy" claims.

The nervous system is the **Reality Bridge reference probe** (ESP32-S3, RB-001…RB-009).
- **REPO** = unchanged from `NavisWORLD/Reality-bridge-universal-probe-engine-sim-` (`hardware/electronics/pinmap.csv`, `hardware/firmware/src/main.cpp`).
- **DECIDED** = final pin for the Spark, decided by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D3). LED 4, I2S1 15/16/7 and amp mute 6 were also approved by Cory himself. All are implemented in `firmware/zeref_spark_fw/include/spark_pins.h` (zs-0.4.0, compiles; not yet run on a board). Cory's repo is **not** edited.
- Still a CONCEPT DESIGN: no pin has been checked on a powered board.

## 1. Data path (unchanged)
```
sensors (pods, torso, chest, crystal station) → ESP32-S3 → normalized JSON ─┬─ native USB CDC (pedestal tube) ◄── speech PCM + commands
                                                                           └─ WebSocket :81 (Wi-Fi build only; speech in, frames out)
                                                       ↓
                                         Beast Box host (the brain)
```

## 2. Pin map

| Signal | GPIO | Goes to | Where | Status |
|---|---|---|---|---|
| I2C SDA | 8 | ICM-42688-P, BME280, BH1750, MAX30102 | torso sled, right pod, chest | **REPO** |
| I2C SCL | 9 | same | | **REPO** |
| I2S0 BCLK / WS / SD | 12 / 13 / 14 | INMP441 | left ear pod | **REPO** |
| GNSS RX / TX | 17 / 18 | GNSS TX / RX | head (optional) | **REPO** |
| LED DATA | **4** | 74AHCT125 → WS2812 chain | torso → chest → head | **DECIDED** (approved by Cory) |
| I2S1 BCLK | **15** | MAX98357A BCLK | head bulkhead | **DECIDED** (approved by Cory) |
| I2S1 LRC | **16** | MAX98357A LRC | head bulkhead | **DECIDED** (approved by Cory) |
| I2S1 DOUT | **7** | MAX98357A DIN | head bulkhead | **DECIDED** (approved by Cory) |
| AMP SD (mute) | **6** | MAX98357A SD | head bulkhead | **DECIDED** (approved by Cory) |
| BAT SENSE | **5** (ADC1_CH4) | 100 k / 100 k divider from LiPo + | torso harness | **DECIDED** |
| I2C1 SDA (station, 2nd bus) | **10** | AS7341 SDA via pogo | pedestal → shield | **DECIDED** |
| I2C1 SCL (station, 2nd bus) | **11** | AS7341 SCL via pogo | pedestal → shield | **DECIDED** |
| WHITE LED gate | **1** | AO3400A #1 | pedestal driver bay | **DECIDED** |
| UV 365 nm gate | **2** | AO3400A #2 (+ reed interlock in series) | pedestal driver bay | **DECIDED** |
| IR 940 nm gate | **21** | AO3400A #3 (Q3) | pedestal driver bay | **DECIDED** (optional LED) — moved from 42 in v0.3 (GPIO42 = MTMS/JTAG, boot-state risk) |
| AS7341 INT | **41** | AS7341 INT (open-drain, 10 k pull-up) | via spare tube wire | **DECIDED** (optional) |
| SHIELD SENSE | **40** | R23 12k / R24 20k divider from UV_5V (after reed S1) → 3.13 V = HIGH when shield seated | pedestal | **DECIDED** — moved from 47 in v0.3 (GPIO47/48 are 1.8 V on some module variants) |
| 3V3 / GND | | | | REPO |

Avoided on purpose: 0 / 3 / 45 / 46 (strapping), 19 / 20 (USB), 26–37 (flash / PSRAM), **38 and 48** (on-board RGB LED on DevKitC-1 v1.1 / v1.0).
GPIO 39–42 are the JTAG pins (v0.3 uses 40 and 41 as plain inputs, which is allowed once JTAG is on USB; 42 was dropped); they are free while debugging uses the built-in USB-JTAG. **Verify every pin against your exact DevKit revision and module (N8R8 / N16R8 / …).**

### I2C address check (7-bit, typical — confirm on your breakouts with an I2C scan)
| Device | Address | Bus |
|---|---|---|
| BH1750 | 0x23 (ADDR low) / 0x5C | I2C0 (8/9) |
| AS7341 | **0x39** (fixed, DS000504 §9.1) | I2C1 (10/11) |
| MAX30102 | 0x57 | I2C0 |
| ICM-42688-P | 0x68 / 0x69 | I2C0 |
| BME280 | 0x76 / 0x77 | I2C0 |

**No address conflict**, so a TCA9548A mux is **not** needed. The AS7341 could share 8/9 electrically. I still put it on a
**second I2C bus (GPIO 10/11, ESP32-S3 I2C1)** for two reasons: (1) the shield is removable and hot-plugs through pogo
pins, and a glitch while seating it must not hang the robot's IMU/BME/BH1750 bus; (2) the station run is ~25 cm
(pedestal → tube → torso), so it gets its own pull-ups and can run at 100 kHz while I2C0 stays at 400 kHz.
DECIDED: dedicated I2C1 on 10/11 (D8). The fallback (sharing 8/9 at 100 kHz) stays possible because there is no address conflict.

## 3. LED chain (WS2812B, 5 V, GPIO 4 via 74AHCT125) — DECIDED
`GPIO4 → AHCT125 → chest ring (12) → eye L (5) → eye R (5) → pod ring L (12) → pod ring R (12) → crown (2)` = 48 LEDs.
330 Ω series at first DIN; 470–1000 µF across 5 V at the chest ring.

## 4. Speaker — DECIDED
MAX98357A on I2S1: BCLK 15, LRC 16, DIN 7, SD 6 (low = mute/shutdown; firmware holds it low at boot). GAIN pin left floating (9 dB) — set lower if it clips on battery.
Plays tones and **streamed speech**: host TTS → 16 kHz mono s16 PCM → `SAY_BEGIN / PCM / SAY_END` lines → 1 s ring buffer → I2S1, digital gain 0.5 (D6).

## 5. Power with the LiPo bay (DECIDED: charger + protection + boost)

```
Pedestal USB-C (5 V, CC 5.1 k) ──VBUS──► PowerBoost 1000C "USB" pad (charger in)          ┌─► ESP32-S3 DevKit 5V pin
          │                               MCP73871 load-share ─► TPS61090 boost ─► 5.2 V ─┼─► LED chain 5 V
          │                               BAT ◄──► protected 503450 LiPo (PCM)            └─► MAX98357A VIN
          ├──D+/D− (twisted)──► USB-C pigtail into DevKit (VBUS NOT connected in the pigtail)
          └──5 V ──► crystal-station LED drivers + AS7341 VIN (station only works when docked)
EN ◄── slide switch to GND (OFF)      LiPo + ──100k──┬──100k── GND ;  midpoint ─► GPIO 5
```

- **Protection**: the PowerBoost has charge control (CC/CV, thermal regulation, timer, reverse-discharge, UVLO) but **no cell protection** — the cell **must** have its own PCM (over-charge, over-discharge, over-current, short). Check JST polarity: LiPo vendors differ.
- **Why the pigtail has no VBUS**: the DevKit is powered from its 5V pin by the boost; feeding USB VBUS in as well would back-feed. **Check your DevKit schematic** (5V pin vs. VBUS diode) before first power-up. USB data works without VBUS on the native USB port; for the USB-UART port, confirm the bridge chip still enumerates.
- **Budget (ESTIMATE)**: the boost output is limited to **~1 A** whether docked or not. ESP32-S3 ≤ 0.35 A peak + LEDs capped at **8 %** (≈ 0.23 A for 48 LEDs; changed from 10 % on 2026-11-09, D1) + amp ≤ 0.3 A ≈ 0.9 A. Firmware enforces both (LED cap 20/255, speech gain 0.5). If the brown-out test fails, the fix is a 2 A boost or a separate LED rail (D10).
- **Runtime (ESTIMATE)**: 1000 mAh × 3.7 V × ~85 % ÷ (5 V × ~0.3 A average) ≈ 2 h.
- Battery is in the **head**; BAT wires to the PowerBoost stay < 75 mm (Adafruit guidance). Five power conductors (VS/5V, GND ×2, BAT sense, EN) join the neck harness.

## 6. Crystal-reading station (pedestal)

| Item | Detail |
|---|---|
| Sensor | **AS7341** (ams-OSRAM datasheet DS000504): 8 visible channels F1 415, F2 445, F3 480, F4 515, F5 555, F6 590, F7 630, F8 680 nm (typ. centre), + Clear + NIR (~910 nm) + flicker; I2C 0x39; 6 ADCs with SMUX, so F1–F4 and F5–F8 are read in two passes. |
| Bus | I2C1 on GPIO 10 / 11 through 4-pin magnetic pogo (VIN 5 V from pedestal, GND, SDA, SCL). Breakout's own regulator + pull-ups. |
| White LED | GPIO 1 → 100 Ω → AO3400A gate (100 k to GND); LED + 100 Ω (ESTIMATE ~20 mA) from pedestal 5 V |
| UV 365 nm | GPIO 2 → AO3400A; LED + 68 Ω (ESTIMATE ~20 mA) **in series with the reed switch** — no shield, no UV, even if firmware fails |
| IR 940 nm (opt.) | GPIO 21 → 100 Ω → AO3400A (Q3); LED + 180 Ω (ESTIMATE ~20 mA) |
| Shield sense | reed S1 in the UV supply; UV_5V → 12k/20k divider → GPIO 40 reads HIGH when seated (v0.3) **and** AS7341 ACK on I2C1 — both must be true before any LED fires |
| Harness | pedestal channels → ZS-502 tube → torso: VBUS, GND, D+, D−, SDA1, SCL1, G_WHITE, G_UV, G_IR, INT, SENSE = **11 conductors** (30 AWG silicone, ESTIMATE fit in 8 mm ID) |

### Data labels the firmware emits (honesty rule) — actual zs-0.4.0 `crystal` frame
```json
{"schema":"zeref-spark-v1","type":"crystal","kind":"sample","sensor":"AS7341","atime":29,"astep":599,"full_scale":18000,
 "settings":"ESTIMATE defaults pending hardware check (DESIGN_DECISIONS.md D7)",
 "label":"MEASURED counts; T=(S-D)/(W-D) is DERIVED relative transmission, not a certified spectrum",
 "modes":{"off":{"gain_x":64,"counts":[...10...],"sat":[...],"T":[...],"T_valid":[...]},
          "white":{"gain_x":16,...},"uv365":{"gain_x":64,...},"ir940":{"gain_x":64,...}},
 "ok":true,"channels":["F1_415","F2_445","F3_480","F4_515","F5_555","F6_590","F7_630","F8_680","CLEAR","NIR_910"]}
```
- Raw channel counts → **MEASURED**. Dark-subtracted / reference-normalised ratios → **DERIVED**.
- Any crystal-type guess → **ESTIMATE**, always with low confidence and never shown without the raw data.
- **No "energy", vibration, healing or metaphysical output is produced or implied.** An 11-channel filter sensor cannot identify minerals reliably; at most it can tell "this sample transmits/fluoresces like the last sample you labelled".

## 7. Harness routes (updated)
| Run | Path | Conductors |
|---|---|---|
| Pedestal → torso | ZS-501 channels → ZS-502 tube (8 mm ID) | 11 (§6) |
| Torso → head | ZS-108 neck bore (14 mm) | ~19: v0.1 set + 5V boost out, GND, BAT sense, EN, VBUS-to-charger |
| Head → pods | 7 mm pod peg bores | unchanged |
| Pedestal internal | pogo, reed and LED-plug channels at z −30 to the tube; driver bay via 6 mm hole to USB channel | |


## v0.4 changes (2026-11-09, all decisions made — docs/DESIGN_DECISIONS.md)
- Every pin is **DECIDED** (D3); LED brightness cap **8 %** everywhere (D1, was 10 % in the power text).
- Host link is the DevKit's **native USB** port (USB CDC) — needed for streamed speech (D6). Wi-Fi build accepts speech only.
- AS7341 gain per mode: off 64×, white 16×, UV 64×, IR 64×; ~50 ms integration; ≥ 90 % of full scale = saturated → T invalid (D7, ESTIMATE).
- Battery: VBAT = 2 × Vadc × BAT_CAL (BAT_CAL = 1.0 until one meter reading; D7, ESTIMATE).
- Child build `zeref-spark-kid`: UV LED never driven (D12).

## v0.3 changes (electrical spec pass)
- IR gate GPIO 42 → **21**; shield sense GPIO 47 → **40**, logic inverted to HIGH = seated (reed now feeds a divider from the switched UV supply).
- Every resistor/capacitor/protection part now has a designator (R1…R24, C1…C21, D1…D6, F1/F2, Q1…Q3, U0…U10, J1/J2, S1, SW1) — see `docs/BOM_electrical.csv` and the schematics in `docs/schematics/`.
- Supply requirement: a **5 V / 3 A USB-C** adapter (ESTIMATE peak VBUS ≈ 1.9 A). A PC USB2 port (0.5 A) is not enough.
