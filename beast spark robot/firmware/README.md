# Zeref Spark firmware

> **CONCEPT DESIGN / NOT BUILT HARDWARE.** It compiles. It has never run on a real board.
> Decisions: `../docs/DESIGN_DECISIONS.md` (decided by Robot X under Cory's delegation 2026-11-09).

| Folder | What |
|---|---|
| `reality_bridge_probe_v0.2_original/` | Cory's Reality Bridge Probe v0.2, **copied unchanged** from `NavisWORLD/Reality-bridge-universal-probe-engine-sim-` @ `13a4ee7` (`hardware/firmware/`) |
| `zeref_spark_fw/` | Spark firmware **zs-0.4.0**, built on v0.2. It keeps his pins, 16 kHz I2S mic, `CAL_AUDIO`, `SELFTEST` and the 100 ms `probe` packet with his field names |
| `build_logs/` | Real compiler output for every env, plus `probe_v0.2_to_spark_*.diff` (original vs Spark) |

## Build status (PlatformIO 6.2.0, espressif32 7.0.1, arduino-esp32 2.0.17), 2026-11-09
| Env | What | Result |
|---|---|---|
| `zeref-spark` (default) | native USB CDC link | **SUCCESS** — RAM 24.1 % (78 948 B), Flash 12.3 % |
| `zeref-spark-wifi` | + Wi-Fi AP / WebSocket :81 (fixed with `lib_ldf_mode = deep`, D5) | **SUCCESS** — RAM 32.4 % (106 012 B), Flash 25.5 % |
| `zeref-spark-kid` | USB build with UV never driven (D12) | **SUCCESS** — RAM 24.1 %, Flash 12.3 % |
| Cory's original v0.2 | as published | **FAILS**: `adafruit/Adafruit ICM42688` isn't in the registry. The Spark uses `finani/ICM42688@1.1.0`; the original folder isn't touched |

RAM went up from 14 % to 24 % because of the 32 KB speech ring buffer.

```
cd zeref_spark_fw
pio run -e zeref-spark -t upload                         # USB (use the DevKit port labelled "USB")
SPARK_AP_PASS='8+ chars' pio run -e zeref-spark-wifi     # optional Wi-Fi; no password is compiled in by default
```

## Pins — all DECIDED (D3; `include/spark_pins.h`)
- **Cory's v0.2 pins:** I2C0 8/9, mic I2S0 12/13/14, GNSS 17/18 (unwired by default).
- **LEDs:** 48 NeoPixels on GPIO4 (chest 0–11, eyes 12–21, pods 22–45, crown 46–47). Cap 20/255 (8 %), or 10/255 on low battery.
- **Speaker:** MAX98357A on I2S1, 15/16/7. Amp mute on 6, muted at boot.
- **Battery:** GPIO5, VBAT = 2 × Vadc × BAT_CAL.
- **Crystal station:**
  - AS7341 on I2C1 10/11, INT on 41;
  - LED gates: white 1, UV 2, IR 21;
  - shield sense 40 (HIGH = seated).

## Safety
- **UV:** at most 2 s on, then at least 5 s off. It only lights when:
  - the shield is seated;
  - the AS7341 answers on I2C1;
  - the battery isn't low.

  It turns off the instant the shield lifts. This sits on top of the reed switch in series with the UV supply. The host
  also requires owner confirmation, and the kid build never drives UV.
- **Raw PPG** goes over USB only, never Wi-Fi. The pulse is an **ESTIMATE, non-medical**, worked out on the host.
- **Wi-Fi** accepts speech lines only. UV, SCAN, LED and calibration commands are USB-only.

## Speech (D6; `include/speech_stream.h`)
- **Host sends:**
  - `SAY_BEGIN <id> 16000 <n>` (n ≤ 30 s);
  - `PCM <id> <seq> <base64 s16le, ≤256 samples>`;
  - `SAY_END <id>`, or `SAY_STOP` to abort.
- **On the Spark:**
  - a 16384-sample ring (about 1 s) and gain 0.5;
  - amp unmuted only while playing, and only if not forced muted (`MUTE 0` first);
  - aborts and mutes if no data arrives for 2 s.
- **Spark replies** with `speech` frames every 100 ms: `free`, `received`, `played`, `underruns`. The host paces on `free`.
- **Speed:** needs native USB CDC (~43 kB/s). A 115200 UART bridge can't carry it; tones still work there.

## Crystal scan defaults (D7, ESTIMATE pending hardware check)
- About 50 ms integration (ATIME 29, ASTEP 599), full scale 18000.
- Gain per mode: off 64×, white 16×, UV 64×, IR 64×.
- Any count at or above 90 % of full scale is flagged `sat`, and that channel's T is marked invalid.

## Frames (Spark → host) and commands
- **Frames:**
  - `features` (audio/light, 1 Hz, on-device);
  - `ppg` (25 IR samples per second);
  - `body` (1 Hz, now with `env` temp/humidity/pressure);
  - `crystal`, `speech`, `selftest`, `ack`, `calibration`;
  - `probe` (100 ms legacy).
- **Commands:**
  - `SELFTEST`, `STATUS`, `CAL_AUDIO`, `PING`;
  - `EXPR <region> r g b`, `BRIGHT n`, `LEDS_OFF`;
  - `TONE f0 f1 ms`, `MUTE 0|1`;
  - `SCAN`, `CAL_DARK`, `CAL_WHITE`, `UV ms`;
  - `SAY_BEGIN`, `PCM`, `SAY_END`, `SAY_STOP`;
  - `HELP`.

## Still needs real hardware
- Flashing, the pin check on your DevKit revision and the brown-out test (LEDs 8 % + speech + Wi-Fi).
- Tuning the AS7341 gains, the finger threshold and BAT_CAL.
- Speech underruns on a real USB link.
