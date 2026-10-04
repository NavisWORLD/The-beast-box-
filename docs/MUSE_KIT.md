# Muse kit

Plug-and-play headband input for Beast Box. It reads an Interaxon Muse 2, Muse S, or Muse S Athena when the radio and the open protocol allow it, and it turns one second of EEG into the same focus / calm / spark traits the Cosmic Synapse HANDHELD tab already uses.

These are wellness and game signals. They are not a medical measurement, not a diagnosis, and not a treatment.

## Install

From this repository:

```bash
pip install -e ".[muse]"
```

`bleak` is the direct Bluetooth extra. Reading a stream that another app already owns also needs `pylsl`:

```bash
pip install pylsl
```

You do not need either library to try the synthetic headband.

## Try it before the headband arrives

```bash
beastbox muse simulate --consent --demo
```

`--consent` is required. The demo prints relative band powers, focus / calm / spark, and the 12-channel bio event those powers become. Raw samples are not in that printout.

```bash
beastbox muse status
beastbox muse record --help
```

`record` and `connect` use a live transport. `simulate` is the only way to get synthetic data.

## What it stores

Derived features are the default: relative delta, theta, alpha, beta, and gamma; the three traits; and the bio-input vector. A recording is a local `.jsonl` file.

```bash
beastbox muse simulate --consent --seconds 5 --out muse-session.jsonl
```

Raw EEG is opt-in and local only:

```bash
beastbox muse simulate --consent --out muse-session.jsonl --raw
```

That writes `muse-session.raw.jsonl` beside the derived file. The kit does not upload either file. Passing an `http://` or other remote path is refused.

## Live fallback order

`beastbox muse connect --consent` tries transports in this order and tells you which step failed:

1. **LSL** — an EEG stream already advertised by muselsl, Mind Monitor, or Petal Metrics. Use this when one of those apps already holds the Bluetooth connection.
2. **BLE** — direct connection with bleak. Muse 2 and Muse S use the legacy AF7 characteristic and preset `p21`, the same framing as the HANDHELD page. Muse S Athena uses the published multiplexed characteristics `273e0013` / `273e0014` and preset `p1041`.

The simulator is not a silent fallback. If nothing is found, the command stops and says so.

Force one path with `--source lsl` or `--source ble`. `--model auto` tells legacy and Athena apart from the GATT table after connect. `--model legacy` or `--model athena` skips that guess.

Relative traits do not depend on the absolute microvolt scale. The Athena scale used here is the one published with muse-lsl 2.5 / BrainFlow. This repository's tests replay packet fixtures; they are not a claim that your headband was on the bench.

## Browser

The Cosmic UI has a MUSE view. The same module is `html/muse.js`, and `html/muse.html` is a standalone page.

- Tick consent, then **Simulate headband**. That needs no radio and shows the traits plus the 12 bio features.
- **Connect Muse** uses Web Bluetooth in a desktop Chromium browser (Chrome, Edge, Opera) on a secure page. `http://127.0.0.1` counts as secure.
- **Safari and iOS do not implement Web Bluetooth.** Use the Python kit there, or a desktop Chromium browser.
- Firefox does not expose Web Bluetooth by default.
- **Send derived bio features** posts the 12-vector only. The page does not post raw samples. The runtime still requires the sensors grant before it accepts the event.

## Bluetooth permissions

- **Linux:** BlueZ running, and permission to use the adapter (often membership in the `bluetooth` group). A desktop session can reach the adapter when a shell started from a menu cannot; start the shell from that session or grant the group.
- **macOS:** System Settings → Privacy & Security → Bluetooth, and allow the terminal or the browser. The headband must be awake (power LED blinking) and not already connected to the phone app.
- **Windows:** Settings → Bluetooth, and allow the browser or terminal through Bluetooth privacy prompts. A headband paired only to the Muse phone app will not also stream to the PC until that app disconnects.

Only one Bluetooth central can own the headband. If the official app, Mind Monitor, or muselsl is connected, `connect --source ble` will fail. Leave that app streaming and use `--source lsl` instead.

muselsl 2.5 or newer can publish Muse S Athena. Older muselsl builds cover Muse 2 and Muse S.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `bleak is not installed` | `pip install -e ".[muse]"` |
| `pylsl is not installed` | `pip install pylsl`, then start muselsl, Mind Monitor, or Petal Metrics |
| No advertisement | Wear the band, hold power until it blinks, and move the receiver closer |
| Connected, no samples | The preset did not start. Retry `--model auto`. If it still fails, stream with muselsl or Mind Monitor and use `--source lsl` |
| Athena connects but looks like noise | Confirm muse-lsl is 2.5+ if you are on the LSL path. Direct BLE follows the published multiplexed decoder and is fixture-tested here |
| Browser button does nothing on iPhone or Safari | Expected. Web Bluetooth is not available. Use `beastbox muse` |
| Consent error | Add `--consent` in the terminal, or tick the consent box in the page |

PPG, fNIRS, and heart rate are not interpreted. The kit does not estimate a clinical state from them.
