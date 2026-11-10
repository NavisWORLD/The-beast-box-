# Zeref Spark — design decisions

> **CONCEPT DESIGN / NOT BUILT HARDWARE.** Every decision here is a design decision, not a test result.
> Anything marked **ESTIMATE** still needs a check on real hardware.

On 2026-11-09 Cory delegated every open decision: *"You design it fully I'm giving you that."*
Each entry below is marked **decided by Robot X under Cory's delegation 2026-11-09**. Cory can reverse any of them.
His own code and repos are unchanged: the vendored Beast Box files are byte-identical, and nothing was pushed.

| # | Decision | Where it lives |
|---|---|---|
| D1 | LED brightness cap **8 %** everywhere | `spark_pins.h` (20/255), `docs/electrical_spec.md`, `wiring.md`, guides |
| D2 | Spark **overlay** routing bands for crystal + body, merged at runtime | `host/spark_brain/routing_spark_overlay.json`, `overlay.py` |
| D3 | All pins **DECIDED** | `wiring.md` §2, `spark_pins.h`, electrical spec pin table |
| D4 | Optional **ψ** readout, off by default, DERIVED, drives nothing | `host/spark_brain/psi.py` |
| D5 | Wi-Fi build fixed (`lib_ldf_mode = deep`), no compiled-in password | `firmware/zeref_spark_fw/platformio.ini` |
| D6 | **Streamed speech**: host TTS → PCM lines → I2S1 speaker | `speech_stream.h`, `main.cpp`, `host/spark_brain/speech.py` |
| D7 | ESTIMATE defaults: AS7341 gain/integration, lux map, finger threshold, battery divider | `crystal_cal.h`, `spark_features.h`, `ppg.py`, `spark_pins.h` |
| D8–D14 | The remaining open items from the README | below |

---

### D1 — LED cap 8 % everywhere
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **Change:** the firmware already capped LEDs at 20/255 (7.8 %), but `docs/electrical_spec.md`, `wiring.md`, the BOM note
  and the guides said 10 %. All of them now say **8 %**. The electrical spec has a "Changed 2026-11-09" note.
- **Why:** the boost gives about 1 A. At 10 % the estimated 5V_SYS peak was 1.03 A, which is over the limit. At 8 % it's
  48 × 60 mA × 8 % = 0.23 A for the LEDs, and **0.97 A** peak in total (ESTIMATE). That's still tight, so the
  speech gain is also capped (D6). Low battery (< 3400 mV) drops LEDs to about 4 %.
- **Hardware check:** the Stage 2 brown-out test (LEDs 8 % + speech + Wi-Fi for 60 s, 5V_SYS ≥ 4.9 V).

### D2 — Spark overlay band for crystal scans and body telemetry
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **What:** `routing_spark_overlay.json` adds **band 7 `spark_crystal`** and **band 8 `spark_body`**, 6 features each, on top of
  Cory's 7 bands. His `routing.json` and `routing.py` aren't touched; a test checks their SHA256.
  - Band 7: `t_white_mean`, `t_white_tilt`, `t_clear`, `uv_response`, `t_nir`, `valid_frac`.
    These come from the calibrated T = (S−D)/(W−D). Freshness 900 s, gamma 0.02.
  - Band 8: `tilt`, `motion` (IMU), `temp`, `humidity`, `pressure` (BME280), `battery`. Freshness 5 s, gamma 0.10.
- **Same rules as Cory's router:** every slot is classed real / stale / control / missing. Masked slots are exactly 0.0.
  Each of the 12 slots gets a receipt with hashes, not data. The receipts are merged with his 54 into one 66-slot
  set with one hash.
- **What it doesn't touch:**
  - The overlay has its own 12-value state, so Cory's dyn12/dyn42/dyn54 come out bit-identical with or without it (tested).
  - Overlay sources are never written to his FeatureStore, so his LiveRouter can't trip on unknown sources.
- **Why an overlay:** Cory owns `routing.json`. An overlay can be dropped, or later folded into his file if he wants that.

### D3 — Pins DECIDED
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **Unchanged from Cory's probe v0.2:** I2C0 8/9, mic I2S0 12/13/14, GNSS 17/18.
- **Already approved by Cory:** LED 4, I2S1 15/16/7, amp SD 6.
- **Now DECIDED:**
  - battery 5;
  - station I2C1 10/11, AS7341 INT 41;
  - white / UV / IR LED gates 1 / 2 / 21;
  - shield sense 40 (HIGH = seated).
- **Why these pins:** they avoid the strapping pins (0/3/45/46), USB (19/20), flash/PSRAM (26–37), the on-board RGB LED
  (38/48) and the 1.8 V GPIO 47. GPIO 42 (JTAG MTMS) was already dropped in v0.3.
- **Updated:** `wiring.md` §2, `spark_pins.h`, the electrical spec's new pin table, the schematic titles and the guides.
- **Hardware check:** confirm on your exact DevKit revision (N8R8 / N16R8).

### D4 — Optional ψ layer
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **Source:** the ψ formula quoted in the brief, ψ = ∫(φ√(m²c²+c⁴)+λΔx)dt, is in none of Cory's repos in that form. The
  closest real form is the one written for a 12D adaptive state:
  `The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.20/README.md:78` (commit `5b6e010a253c`):
  `ψᵢ = (φ·Eᶜᵢ)/(c²m₀) + λᵢ/E_ref + ∫|dx₁₂ᵢ/dt|dt + (Ωᵢ·Eᶜᵢ)/E_ref + U_grav/E_ref`.
  It has a φ-energy term, a λ term and an integrated-displacement term, the same three ingredients as the quoted one.
- **How it maps onto the Spark** (DESIGN CHOICES, in natural units c = m₀ = E_ref = 1):
  - Eᶜ = mean(x²) of dyn12;
  - λ = smoothed log ratio of successive step sizes (a Lyapunov-style ESTIMATE);
  - path = Σ|Δx|;
  - Ω = (D11 + 1)/2, or 0 when D11 is masked;
  - U_grav = 0, because there are no masses.
- **Off by default:** turn it on with `SparkBrain(psi=True)` or `--psi`. It's labelled **DERIVED** and carries `drives_hardware: false`.
- **Tested:** the LED commands and Beast Box state are identical with ψ on and off.

### D5 — Wi-Fi build fixed
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **Cause:** with `lib_ldf_mode = deep+` (or `chain+`), PlatformIO's library finder evaluated the platform `#if`s in
  WebSockets.h and never added the framework's WiFi library, so the build failed on `WiFi.h`.
- **Fix:** `lib_ldf_mode = deep` in the Wi-Fi env, with its build flags written out in full. Both builds now compile.
- **AP password:** Cory's v0.2 had a placeholder password; none is compiled in now. Build with
  `SPARK_AP_PASS='8+ chars' pio run -e zeref-spark-wifi`. If it's empty, the AP stays off and the Spark reports `AP_OFF_NO_PASSWORD`.
- **Over Wi-Fi,** the Spark sends frames (never raw PPG) and **accepts speech lines only**. UV, SCAN, LED and calibration
  commands are USB-only.

### D6 — Streamed speech
*Decided by Robot X under Cory's delegation 2026-11-09.*
- **Pipeline:**
  1. The approved mouth's reply is sanitized: control characters and newlines are removed, and it's capped at 400 chars.
  2. Local TTS turns it into audio, then it's resampled to **16 kHz mono s16le**.
  3. The host sends `SAY_BEGIN id 16000 n`, then `PCM id seq <base64 of ≤256 samples>` lines, then `SAY_END id`
     (`SAY_STOP` aborts).
  4. The Spark fills a 16384-sample ring (about 1 s), applies gain 0.5 and writes to I2S1 (MAX98357A).
  5. It unmutes GPIO6 only while playing, and only if the owner hasn't forced mute (`MUTE 1` is the boot state).
     It mutes again about 60 ms after the end.
- **Flow control:** the Spark sends `speech` frames every 100 ms with `free`, `received`, `played` and `underruns`. The host never
  sends more samples than `free` allows. If no data arrives for 2 s mid-stream, the stream is aborted and the amp muted.
- **Link:** the DevKit's **native USB** (USB CDC, `ARDUINO_USB_CDC_ON_BOOT=1`). Speech needs about 43 kB/s, which a 115200
  UART can't carry. Over UART, tones still work. The Wi-Fi build takes the same lines as WebSocket text.
- **TTS:**
  - **piper** (third-party, MIT), run locally in `~/.zeref-spark/ttsv` with the voice
    `~/.zeref-spark/voices/en_US-lessac-low.onnx` (16 kHz). It's installed on this box and tested.
  - If piper is missing, a **StubTTS** makes deterministic tone "syllables", labelled "STUB TONES — not speech".
- **Authority:** model text only ever reaches the TTS. The device lines are built from integers and base64, so
  "UV 2000" or "\nSCAN" in a reply can't become commands (tested). `link.command()` refuses speech ops. Speech is
  off unless the owner turns it on (`speech=True` / `--speak`).
- **Tested:** the C++ parser and ring buffer, compiled on the host from the same header, play back bit-exact samples, and reject
  bad rate, length, sequence, id, base64 and overflow.

### D7 — Defaults pending a hardware check (all ESTIMATE)
*Decided by Robot X under Cory's delegation 2026-11-09.*

| Setting | Default | Reason | How to check |
|---|---|---|---|
| AS7341 integration | ATIME 29, ASTEP 599 → ~50 ms, full scale 18000 | Fast enough for a 4-mode scan (< 1 s) with headroom | PTFE white under each LED should sit at 20–60 % of full scale |
| AS7341 gain per mode | off 64×, white 16×, UV 64×, IR 64× | The white LED through the cup is bright; dark, UV-visible and NIR are weak. Dark, white and sample of the same mode always share a gain, so T stays valid | Lower the gain if any `sat` flag is true on white; raise it if counts are < 5 % |
| Saturation | ≥ 90 % of full scale → that channel's T is invalid (firmware and host) | A clipped reading can't be divided honestly | Check the `sat` arrays |
| Lux → brightness | `log10(1+lux)/log10(65536)` | A log scale over the BH1750 range lets a dim room and daylight both move the band | Compare dark room / desk lamp / window |
| Finger present (PPG) | IR DC ≥ 50 000 counts (LED 60, ADC 4096, 411 µs) | SparkFun example heuristic (third-party) | Log IR DC with and without a finger |
| Battery | VBAT = 2 × Vadc × BAT_CAL, BAT_CAL = 1.0; low battery < 3400 mV | 100 k/100 k divider; ESP32 ADC error is ±a few % | One meter reading: BAT_CAL = meter_mV / reported_mV |

### D8 — Station I2C stays on its own bus (GPIO 10/11, 100 kHz)
*Decided by Robot X under Cory's delegation 2026-11-09.*
The shield hot-plugs through pogo pins, so a glitch must not hang the IMU/BME/BH1750 bus. The firmware already uses Wire1.

### D9 — Sensor stays AS7341
*Decided by Robot X under Cory's delegation 2026-11-09.*
The AS7341 is designed in, has a registry driver (Adafruit AS7341 1.4.1) and compiles. The AS7343 would need a new driver and checks.

### D10 — Keep the 1 A boost for v0.4
*Decided by Robot X under Cory's delegation 2026-11-09.*
With the 8 % LED cap and 0.5 speech gain the estimated peak is 0.97 A. If the Stage 2 brown-out test fails, the upgrade is a
2 A boost or a separate LED rail. Neither is drawn yet.

### D11 — Stay wired to the pedestal tube (no detachable dock in v0.4)
*Decided by Robot X under Cory's delegation 2026-11-09.*
The battery covers short unplugs. A magnetic dock would change the CAD and harness, so it's left for a later version.

### D12 — Child build without UV
*Decided by Robot X under Cory's delegation 2026-11-09.*
Firmware env `zeref-spark-kid` (`-DSPARK_UV_ENABLED=0`) never drives the UV LED: `UV` replies `UV_DISABLED_BUILD`, and scans
skip the UV mode. It compiles. For a child's robot, also leave the UV LED unpopulated. The shield stays lift-off with the
reed interlock; no CAD change was made in this pass.

### D13 — UV-cut window: ~420 nm longpass glass
*Decided by Robot X under Cory's delegation 2026-11-09.*
Eye safety matters more than cost here; glass has a defined cut-off. UV-blocking acrylic is the fallback only if its datasheet
shows < 1 % transmission at 365 nm.

### D14 — Float tube: metal 12 × 2 mm (12 OD / 8 ID)
*Decided by Robot X under Cory's delegation 2026-11-09.*
Brass or stainless at the same OD/ID as the acrylic tube in the CAD, so no geometry change. It's stiffer than acrylic, which is
unverified for 11 conductors plus the robot's weight. Deburr the ends and sleeve the harness.

### Not decidable here
- **The original brief** is still missing, so `ref/brief.md` stays a reconstruction. Only Cory can re-attach it.
