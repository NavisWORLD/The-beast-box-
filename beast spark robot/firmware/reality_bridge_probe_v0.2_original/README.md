# Reality Bridge Probe Firmware v0.2

**Software implementation status: implemented; physical hardware validation still pending.**

The reference firmware targets an ESP32-S3 DevKitC-1 class board and publishes normalized telemetry over USB serial and a local WebSocket on port 81.

## Implemented telemetry

- BH1750 ambient light
- BME280 temperature / humidity / pressure
- ICM-42688-P motion/orientation proxy
- MAX30102 red/IR optical waveform, non-medical
- INMP441 I2S microphone RMS
- optional GNSS latitude / longitude / altitude / satellite count
- per-packet sensor-presence flags

## Reference pins

- I2C SDA: GPIO8
- I2C SCL: GPIO9
- INMP441 BCLK: GPIO12
- INMP441 WS: GPIO13
- INMP441 SD: GPIO14
- GNSS RX: GPIO17
- GNSS TX: GPIO18

The INMP441 reference path assumes its L/R select is tied LOW so the firmware reads the left I2S slot.

## Serial commands

At 115200 baud:

- `SELFTEST` - emit a JSON sensor-presence / firmware / heap status record
- `STATUS` - same status snapshot
- `CAL_AUDIO` - measure the current quiet-room/device microphone floor and apply it to RMS normalization
- `HELP` - list commands

## Network

The firmware creates the local access point `RealityBridge-Probe` and serves telemetry via WebSocket port 81. Change the default development password before using the probe outside a controlled lab setup.

## Physical validation boundary

A firmware compile or software test does not prove the electrical assembly is correct. The first physical unit still needs rail checks, sensor-by-sensor bring-up, audio verification, packet-rate/latency measurement, and calibration against reference instruments.
