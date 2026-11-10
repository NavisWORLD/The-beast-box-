# ZEREF SPARK — Assembly guide (v0.2: + LiPo bay, + crystal-reading station)

**DESIGN TARGET — not printed or test-fitted.** Every dimension is a CAD ESTIMATE. Print one test
piece of each joint (leg peg, arm peg, pod peg, neck, a split boss) before printing full shells.

## 0. Key dimensions (ESTIMATE)
- Robot: 182 mm wide across the pod caps, 196 mm across the splayed ear tips, 128 mm deep (head), **314 mm tall** from foot sole to ear tip.
- Head 150 W × 128 D × 118 H mm (≈47 % of height without ears, ≈38 % with ears). Torso egg 88 × 76 × 100 mm.
- Float gap: feet sit **12 mm** above the pedestal top. Pedestal (v0.2, enlarged for the crystal station): hex 190 × 164.5 × 45 mm.
- Height kept at **314 mm** robot (approved).
- Overall with pedestal: ~371 mm tall (pedestal bottom to ear tip).
- Printed robot volume ≈ 490 cm³ solid model → ≈ 450–600 g in PETG (ESTIMATE); pedestal ≈ 250–350 g at 15 % infill.

## 1. Print list (STL in `out/stl/`, already seated on Z=0; rotate for best orientation)
| Part | Material | Orientation / notes |
|---|---|---|
| ZS-101/102 head shells | matte navy PETG, 3–4 walls, 0.2 mm | split face down on bed, tree supports inside |
| ZS-301/302 torso shells | matte navy PETG | split face down |
| ZS-103/303 bulkheads, ZS-304 sled, ZS-105 face carrier | PETG | flat |
| ZS-104 visor | smoked translucent PETG, or vacuum-form 1.5 mm smoked PETG over a printed buck | convex side up, fine layers / sand + clear coat for gloss |
| ZS-106/107 light pipes, ZS-307 lens | clear resin (best) or clear PETG | polish faces |
| ZS-203/306 diffusers | translucent white PETG (violet/cyan come from LEDs) | flat |
| ZS-201/202 pods, ZS-204/205 caps | navy / gloss black PETG | outer face up |
| ZS-206 ears | navy PETG | lying on the back face, inner-face slots up |
| ZS-401 arms, ZS-402 legs | navy PETG | peg up, supports under hands/feet |
| ZS-501 pedestal | dark grey/black PLA 15 % infill | bottom down; optional stone-texture paint |
| ZS-502 tube | buy 12 OD × 8 ID acrylic, cut 75 mm | deburr; see open decision on stiffness |
| ZS-109 battery tray | PETG | lips up |
| ZS-601 station LED plug | white PETG | flange down; line the cavity with PTFE tape or white paint |
| ZS-602 light shield | **opaque** black PETG/PLA, 4 walls, 100 % top | top down; hold a torch inside in a dark room to check pinholes; paint inside matte black |
| ZS-603 sensor mount, ZS-605 dark plug | matte black, 100 % infill | flat |
| ZS-604 driver-bay cover | PLA | flat |

## 2. Pre-assembly
1. Heat-set **8 × M3 inserts** (ZS-F01) into the four bosses of ZS-301 and the four of ZS-101.
2. Clean holes: peg holes 8.8 / 7.8 / 12.8 / 26.8 mm should slide over pegs with ~0.4 mm clearance. Sand, never force.
3. Flash the Reality Bridge firmware (repo `hardware/firmware`) onto the ESP32-S3 and confirm JSON on USB before it goes inside.

## 3. Head
0. **Battery bay first** (approved addition): screw ZS-109 to the back of ZS-103 (2 × M2 × 6). Screw the PowerBoost 1000C below it (x 12…48, z 158…181; 2 × M2). Fit the slide switch into the slot in ZS-102 (glue) and wire it EN ↔ GND. **Do not plug the LiPo in yet.** Check LiPo JST polarity against the PowerBoost silkscreen, then slide the protected 503450 cell into the tray from the top.
1. Glue/clip the visor ZS-104 onto the ledge inside ZS-101 (clear silicone or thin CA at edges).
2. Push accent pipes ZS-107 up through the two crown holes from inside (flange stops them); place the 2-LED accent board under them.
3. Fit eye pipes ZS-106 onto the eye LED strips on ZS-105 (cyan arcs, curve up). Screw ZS-105 posts to the bulkhead ZS-103 (2 × 2.5 mm PT).
4. On the back of ZS-103: MAX98357A amp, optional GNSS (crown), optional LiPo. Speaker into the ring in ZS-102.
5. Build each pod: sensor (INMP441 left / BH1750 right) at the bottom of the cavity, 12-LED ring above it, rim diffuser ZS-203, then cap ZS-204/205. Screw each ear ZS-206 onto its pod (M3 × 10 from inside the pod — do this **before** the ring and cap go in).
6. Lay ZS-101 face-down. Drop in ZS-103 with face carrier attached; seat both pod flanges and the neck coupler top flange into their half-holes; route the pod and neck harnesses.
7. Close with ZS-102. **4 × M3 × 8 (RB-008)** from the back into the inserts. Pods, ears and neck are now captured.

## 4. Torso
1. Zip-tie the ESP32-S3 DevKit into the rails on the back of ZS-303, USB end **down**.
2. Screw the sensor sled ZS-304 (IMU at chest height, BME280 low behind the vents) to the front of ZS-303 (2 × M2 × 6).
3. Chest core: MAX30102 (optional) behind ZS-305 centre; LED ring over the baffle from the front; diffuser ZS-306; lens ZS-307.
4. Lay ZS-301 face-down. Fit the chest core from inside (flange behind the 41 mm hole). Seat the leg pegs, arm pegs, neck coupler bottom flange and the tube in their half-holes. Drop in ZS-303.
5. Plug the harnesses (neck, chest, USB pigtail from the tube). Close with ZS-302, **4 × M3 × 8 (RB-008)**.

## 5. Pedestal and float
1. USB-C breakout into the back pocket of ZS-501; feed the 4-wire harness through the channel and up the tube.
2. Glue the tube ZS-502 into the pedestal socket (25 mm deep). The robot's torso socket slides onto the top of the tube (13 mm engagement).
3. Felt pads in the three recesses.
4. Plug in **RB-009** USB-C → Beast Box host. Check the JSON stream, then LEDs at ≤ 8 % brightness (the firmware cap).

## 6. Crystal-reading station (pedestal top, front)

**Placement choice: pedestal, not hand or chest.** The pedestal is stable and does not load the floating robot.
It can be made light-tight with a removable shield and a groove light-trap. The LEDs sit under a fixed window, so the
optical path and geometry are the same every time, which is what makes readings repeatable. Power and LED current come
straight from the USB-C input without passing through the boost budget, and there is room for a crystal up to ~25 mm wide.
A mitten hand is too small to shade, and it moves, so its geometry changes with every pose. The chest already holds the
MAX30102 window and the LED ring, which would leak light into the sensor.

Geometry (ESTIMATE): cup Ø26 × 12 mm deep at (0, −46) on a flat Ø74 "altar". Borosilicate window Ø29.6 × 2 at z −14…−12.
LED board 20 × 20 under the window. Sensor chip ~33 mm above the window, so a crystal can be up to ~32 mm tall, including the
12 mm in the cup. The shield (Ø50 body, Ø72 flange, skirt in a Ø47–51 groove) lifts 5 mm, then slides forward; the
removal path is checked with 4.2 mm clearance to the torso.

Build:
1. LED board (white, 365 nm UV, optional 940 nm IR) into the ZS-601 pocket, LEDs up. Wires go down the centre hole and out of the side hole.
2. Window ZS-S02 goes into its seat from **below** (the Ø26 cup lip holds it from above). Push ZS-601 up behind it and fix it with 2 × M3 × 8 self-tap.
3. Fit the pogo receptacle into the pocket at x 29…34 and the reed switch into its slot at x −36…−28. Route both through the channels at z −30 to the tube.
4. Put the driver board (3 × AO3400A) in the bottom bay. Wire the **reed switch S1 in series with the UV LED supply** (VBUS → S1 → UV_5V → D5 → R21 → Q2; hardware interlock; v0.3, see docs/schematics/E_crystal_station.png), then fit cover ZS-604.
5. Shield: AS7341 breakout onto ZS-603 (chip looking down through the 12 mm aperture). Fit the optional UV-cut filter in the recess and glue ZS-603 into the shield top. Feed the 4 wires down the rib bore to the pogo pads in the flange pocket, then glue the Ø6 × 2 magnet into its pocket (it must sit over the reed).
6. Seat the shield. The I2C scan on bus 1 must show 0x39 and GPIO 40 must read HIGH (reed closed → divider ≈ 3.1 V; v0.3 pin). Lift the shield and both must go away.

### UV-A (365 nm) eye and skin safety, required
- 365 nm is barely visible, so your eyes don't blink or look away from it. **Never look at the UV LED, lit or not,** and never run it with the shield off. The reed interlock cuts its current in hardware, and firmware also requires shield sense + AS7341 ACK.
- Firmware limits: UV on ≤ 2 s per reading, ≥ 5 s off between readings, a watchdog forces it off, and it stays off at boot.
- For bench work with the shield off, power the UV LED **only** through a current-limited supply ≤ 20 mA, wear UV-blocking safety glasses (EN 166 / ANSI Z87 + UV400), and keep skin out of the beam.
- Check the LED's datasheet photobiological risk group (IEC 62471). Use a low-power 20 mA part, not a high-power "UV torch" LED.
- Keep the station out of reach of young children. Cory's family: Caleb should not be able to open the shield while the robot is powered. Use a screw-retained shield if needed (open decision).
- Fluorescence work is low-power only. Don't use the station to cure resin or sterilise anything.

### Calibration procedure (do it at power-up, after any LED or shield change, and at least monthly)
Fix the settings first and record them with every reading: gain (start at 64×), ATIME/ASTEP (start at ~50 ms), LED warm-up 2 s, and a temperature log (BME280 / internal).
1. **Warm-up**: robot on for ≥ 10 min, shield on.
2. **Dark reference D**: ZS-605 dark plug in the cup, shield on, **all LEDs off**. Take 10 readings and store the mean and standard deviation for each channel. This is sensor offset plus any ambient leak.
3. **Stray-light check**: dark plug still in, each LED on in turn. The counts must stay within ~3 standard deviations of D. If they don't, light is leaking around the plug or the shield (fix with paint or tape before going further).
4. **Ambient leak check**: empty cup, shield on, LEDs off, room lights switched on and off. Any change of more than ~3 standard deviations means the shield or groove leaks.
5. **White reference W** (per LED mode): PTFE disc ZS-S12 in the cup, shield on, LED on. Take 10 readings. Adjust gain so the highest channel is 30–80 % of full scale (no saturation; full scale is set by ATIME/ASTEP, max 65535). Store W for each mode.
6. **Empty-cup reference E** (optional): window only, for absolute transmission.
7. **Crystal reading S**: same mode, gain and timing. Take 5 readings and keep the raw counts (**MEASURED**).
8. **Derived values**: `T_ch = (S − D) / (W − D)` for transmission vs PTFE. In fluorescence mode (UV on, UV-cut filter in), `F_ch = (S − D) / (W_white − D)` is a **relative** emission index only. Both are **DERIVED**.
9. **Repeatability gate**: remove and re-seat the crystal 3 times. If any T_ch changes by more than ~5 %, flag the reading "unrepeatable" (placement, chips and surface dirt all matter).
10. Any "looks like amethyst / clear quartz / …" label is an **ESTIMATE** from nearest-match against samples Cory has labelled himself. Show it with its confidence and the raw data, and never call it MEASURED. No energy or metaphysical claims are made.

## 7. Verification still to do (none of this has happened)
Print + test-fit, measure actual purchased module sizes against the proxies, bench-test power draw, check
the tube's stiffness with the real robot weight, check BH1750 light leak and BME280 self-heating,
measure the battery runtime and 1 A boost headroom, confirm the shield is light-tight, confirm the 365 nm interlock
cuts current with the shield removed, and confirm the AS7341 counts are repeatable with the calibration above.
