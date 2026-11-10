# ZEREF SPARK — robot build breakdown (working copy of the brief)

> **Provenance note (read first).** Cory's original attachment
> (`ZEREF SPARK robot build breakdown`, 5.4 KB markdown, plus a concept PNG) was
> removed from the box before this CAD pass ran, and the verbatim text was **not**
> available to the CAD agent. This file is a **reconstruction** from the parent
> conversation's summary of that brief plus the concept-art description relayed by
> the parent agent. Where wording below differs from Cory's original, **Cory's
> original wins** — drop the real file in here to replace this one.

## Intent (from Cory)
"Fully build piece by piece a 3D CAD design, fully built and for assembly, the robot
by design and by my logic using my tech."

## Architecture (from the brief, as relayed)
- The **ESP32-S3 Reality Bridge probe is the nervous system** of the robot.
- The **Reality Bridge reference parts RB-001 … RB-009 are designed in**
  (source: `NavisWORLD/Reality-bridge-universal-probe-engine-sim-`, `hardware/BOM.csv`):
  - RB-001 ESP32-S3 DevKitC-1 (MCU / Wi-Fi / USB) — required
  - RB-002 ICM-42688-P (6-axis IMU) — required
  - RB-003 BH1750 (ambient light) — required
  - RB-004 BME280 (temp / humidity / pressure) — required
  - RB-005 MAX30102 (optical waveform, non-medical) — optional
  - RB-006 INMP441 (I²S microphone) — required
  - RB-007 NEO-M9N-class GNSS — optional
  - RB-008 M3 × 8 mm screws ×8
  - RB-009 USB-C data/power cable
- **The brain stays on the Beast Box host**: the robot streams normalized sensor JSON
  (USB serial and local WebSocket :81, per the repo firmware) and receives
  expression / light / voice commands back. No onboard "AI".
- Pin contract follows the repo pinmap (I²C SDA 8 / SCL 9; I²S mic BCLK 12 / WS 13 /
  SD 14; GNSS RX 17 / TX 18).

## Parts called out in the brief (as relayed)
- Head shells
- Ear pods for the mic and the light sensor
- Chest core and LED diffuser
- Body shells with ESP32, speaker and battery bays
- Sensor sled
- Limbs (arms, legs) and the pedestal

## Deliverables requested
Parametric per-part CAD (STEP + printable STL), renders, BOM, wiring guide,
assembly guide, interference / fit check. Everything labelled
**"DESIGN TARGET — not printed or test-fitted"**. Nothing published.

## Concept look (relayed description of the concept PNG)
Chibi companion robot. Matte dark navy/black body with glossy panels; large rounded
helmet-like head (~45 % of total height, wider than the body). Wide black visor face
with two glowing cyan happy-closed-eye arcs; small magenta accent lights at the top
of the head. Two tall upright rabbit-like ears, rounded tips, a row of small
holes/slots on their inner faces. Round side "headphone" pods where the ears meet
the head, with violet rim light. Small rounded egg-shaped torso with a circular chest
core: glowing cyan ring, magenta/violet centre. Stubby rounded arms with small mitten
hands; short stubby legs with rounded feet. Floats slightly above a dark rocky
hexagonal-ish stone pedestal. Palette: midnight with cyan + violet accents. Labelled
"CONCEPT DESIGN / NOT BUILT HARDWARE".
