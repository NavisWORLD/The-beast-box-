<div class="cover" markdown="1">
<h1 class="nobreak">ZEREF SPARK — Assembly Guide</h1>

**Chibi companion robot on a floating pedestal with a crystal-reading station · v0.4 (all decisions made, firmware zs-0.4.0)**

<span class="tag">DESIGN TARGET — not printed or test-fitted</span> <span class="tag">CONCEPT DESIGN / NOT BUILT HARDWARE</span>

<img src="../renders/01_hero_three_quarter.png">

**System logic, architecture and concept: Cory Davis (NavisWORLD)** — Reality Bridge / Beast Box (“the brain lives on the host; models are mouths”).
CAD geometry, renders and this guide were **AI-generated** from Cory's logic (CadQuery). Parts marked **PX** are **third-party modules** shown as simplified proxy shapes — measure your purchased boards.
Height target 314 mm (robot) · ≈371 mm with pedestal. Every dimension and electrical value marked ESTIMATE is unverified.
</div>


# 1. Safety — read before you start

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
- 365 nm is barely visible, so your eyes don't blink or look away from it. **Never look at the UV LED, lit or not,** and never run it with the shield off. The reed interlock cuts its current in hardware, and firmware also requires shield sense + AS7341 ACK.
- Firmware limits: UV on ≤ 2 s per reading, ≥ 5 s off between readings, a watchdog forces it off, and it stays off at boot.
- For bench work with the shield off, power the UV LED **only** through a current-limited supply ≤ 20 mA, wear UV-blocking safety glasses (EN 166 / ANSI Z87 + UV400), and keep skin out of the beam.
- Check the LED's datasheet photobiological risk group (IEC 62471). Use a low-power 20 mA part, not a high-power "UV torch" LED.
- Keep the station out of reach of young children. Cory's family: Caleb should not be able to open the shield while the robot is powered. Use a screw-retained shield if needed (open decision).
- Fluorescence work is low-power only. Don't use the station to cure resin or sterilise anything.


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


# 2. Tools and consumables

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


# 3. Bill of materials (complete)

Mechanical, module and printed rows first, then every electrical/passive part (v0.3). Full electrical detail: `docs/BOM_electrical.csv`.

| ID | Part | Qty | Type | Material / source | Location in robot | Function | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| RB-001 | ESP32-S3 DevKitC-1 or compatible | 1 | Purchased (Reality Bridge) | Espressif or compatible | Torso – back face of ZS-303 cradle (USB end down) | MCU / Wi-Fi / USB – the nervous system | Required | Proxy 26x14x69 mm ESTIMATE incl. headers; verify the purchased board. Retained by rails + 2 zip ties |
| RB-002 | ICM-42688-P breakout | 1 | Purchased (Reality Bridge) | breakout | Torso – ZS-304 sensor sled (z~100 near body centre) | 6-axis IMU (motion / tilt / tap) | Required | Proxy 23x18x4 ESTIMATE |
| RB-003 | BH1750 breakout | 1 | Purchased (Reality Bridge) | breakout | Right ear pod (ZS-202) behind 8 mm window in ZS-205 | Ambient light | Required | Proxy 18x16x4 ESTIMATE; LED-ring light leak – firmware must sample with pod LEDs off |
| RB-004 | BME280 breakout | 1 | Purchased (Reality Bridge) | breakout | Torso – lower sensor sled behind front belly vents | Temp / humidity / pressure | Required | Kept away from ESP32 heat; readings will still be biased by internal heat (ESTIMATE) |
| RB-005 | MAX30102 breakout | 1 | Purchased (Reality Bridge) | breakout | Torso – behind chest core centre (looks out through ZS-307) | Optical waveform – NOT MEDICAL | Optional | Proxy 22x18x5 ESTIMATE; 11 mm light pipe may be too long for a usable signal – open decision |
| RB-006 | INMP441 breakout | 1 | Purchased (Reality Bridge) | breakout | Left ear pod (ZS-201) behind mic holes in ZS-204 | I2S microphone | Required | Proxy 23x15x4 ESTIMATE; L/R pin to GND |
| RB-007 | NEO-M9N-class GNSS breakout | 1 | Purchased (Reality Bridge) | breakout | Head – back face of ZS-103 near crown | GNSS | Optional | Proxy 30x25x6 ESTIMATE; indoor reception will be poor |
| RB-008 | M3 x 8 mm screws | 8 | Fastener (Reality Bridge) | steel | 4 torso split bosses + 4 head split bosses | Close shells (clamp bulkheads + captured pegs) | Reference | Used through back-half clearance bosses into front-half heat-set inserts |
| RB-009 | USB-C data/power cable | 1 | Purchased (Reality Bridge) |  | Pedestal USB-C port to host / 5 V supply | Power + data to Beast Box host | Required | Use a 5 V / 3 A capable cable + supply |
| ZS-101 | Head shell front | 1 | Printed | PETG or PLA matte navy | Head | Helmet front + visor ledge + accent-pipe holes | Design target | 4 x M3 heat-set inserts |
| ZS-102 | Head shell back | 1 | Printed | PETG or PLA matte navy | Head | Helmet back + speaker grille/ring | Design target |  |
| ZS-103 | Head bulkhead | 1 | Printed | PETG | Head split plane | Mount plate: face carrier / amp / GNSS / optional LiPo | Design target | Clamped between head shells |
| ZS-104 | Visor | 1 | Printed or thermoformed | smoked translucent PETG (or 1.5 mm smoked PETG sheet vacuum-formed) | Head front | Black glossy face; eyes glow through | Design target | Glue / silicone onto ZS-101 ledge |
| ZS-105 | Face carrier | 1 | Printed | PETG black | Behind visor | Holds eye LED strips + light pipes | Design target | 2 x 2.5 mm PT screws into ZS-103 |
| ZS-106 | Eye light pipe (happy arc) | 2 | Printed | clear PETG / clear resin | Behind visor | Cyan happy-closed-eye arcs | Design target |  |
| ZS-107 | Accent light pipe | 2 | Printed | clear resin | Top of head | Magenta accent lights | Design target | Flange retained inside head |
| ZS-108 | Neck coupler | 1 | Printed | PETG | Neck | Captured between both shell pairs; 14 mm harness bore | Design target |  |
| ZS-201 | Ear pod L (mic) | 1 | Printed | PETG matte navy | Left side of head | Houses INMP441 + LED ring; flanged peg captured by head split | Design target |  |
| ZS-202 | Ear pod R (light) | 1 | Printed | PETG matte navy | Right side of head | Houses BH1750 + LED ring | Design target |  |
| ZS-203 | Pod rim diffuser | 2 | Printed | translucent white/violet PETG | Pod outer rim | Violet rim light | Design target |  |
| ZS-204 | Pod cap L (mic holes) | 1 | Printed | PETG gloss black | Left pod face | Mic port array | Design target | Snap/glue into rim |
| ZS-205 | Pod cap R (light window) | 1 | Printed | PETG gloss black + clear window | Right pod face | BH1750 window | Design target |  |
| ZS-206 | Ear (rabbit) | 2 | Printed | PETG matte navy | On top of pods | Tall ears with inner-face slot row | Design target | 1 x M3 x 10 self-tap each from inside pod |
| ZS-301 | Torso shell front | 1 | Printed | PETG matte navy | Torso | Egg front + chest hole + BME vents | Design target | 4 x M3 heat-set inserts |
| ZS-302 | Torso shell back | 1 | Printed | PETG matte navy | Torso | Egg back + ESP32 vents | Design target |  |
| ZS-303 | Torso bulkhead / ESP32 cradle | 1 | Printed | PETG | Torso split plane | ESP32 rails on back; sensor sled on front | Design target |  |
| ZS-304 | Sensor sled | 1 | Printed | PETG | Torso front of bulkhead | IMU + BME280 carrier | Design target | 2 x M2 x 6 self-tap |
| ZS-305 | Chest core housing | 1 | Printed | PETG black | Chest | Cup + optical baffle; LED ring and diffuser load from front | Design target |  |
| ZS-306 | Chest ring diffuser | 1 | Printed | translucent white PETG | Chest | Cyan ring glow | Design target | Press/glue |
| ZS-307 | Chest centre lens | 1 | Printed | clear (if MAX30102) or violet translucent | Chest centre | Magenta/violet centre / optical window | Design target |  |
| ZS-401 | Arm | 2 | Printed | PETG matte navy | Shoulders | Stubby arm + mitten hand; flanged peg captured by torso split | Design target | Static (no servo) in this revision |
| ZS-402 | Leg | 2 | Printed | PETG matte navy | Hips | Stubby leg + rounded foot; flanged peg captured | Design target | Static |
| ZS-501 | Pedestal (rock hex) v0.2 | 1 | Printed | PLA dark grey/black 15% infill (station walls 100%) | Base | Floating base + crystal station cup / window seat / groove / pogo + reed pockets / driver bay / harness channels | Design target | Now 190 x 164.5 x 45 mm (ESTIMATE); 3 x 16 mm felt pads |
| ZS-502 | Support tube | 1 | Purchased + cut | clear acrylic tube 12 OD x 8 ID x 75 mm | Pedestal to torso | Floating support + 4-wire USB harness | Design target | Stiffness unverified – see open decisions |
| ZS-E01 | WS2812B 12-LED ring (~37 mm OD) | 3 | Purchased |  | Chest + both pods | Cyan chest ring / violet pod rims | Proposed | OD 37 / ID 23 ESTIMATE – verify ring you buy |
| ZS-E02 | WS2812B strip segment (5 LEDs) | 2 | Purchased |  | Face carrier behind eye pipes | Eye glow | Proposed |  |
| ZS-E03 | WS2812B 2-LED accent board | 1 | Purchased/custom |  | Head crown inside | Magenta accents | Proposed |  |
| ZS-E04 | 74AHCT125 (or SN74AHCT1G125) level shifter | 1 | Purchased |  | Torso harness | 3.3 V -> 5 V LED data | Proposed |  |
| ZS-E05 | MAX98357A I2S amp breakout | 1 | Purchased |  | Head bulkhead back | Speaker amp | Proposed | Needs firmware addition (I2S1) |
| ZS-E06 | 28 mm 8 ohm ~1 W speaker | 1 | Purchased |  | Head back shell ring | Voice / sounds from Beast Box host | Proposed | 28 x 6 mm ESTIMATE |
| ZS-E07 | USB-C receptacle breakout (with 5.1 k CC pull-downs) | 1 | Purchased |  | Pedestal back pocket | Power + data entry | Proposed |  |
| ZS-F01 | M3 heat-set insert (short) | 8 | Fastener | brass | Front shell bosses |  | Proposed | 4.0 mm pilot ESTIMATE – match your insert |
| ZS-F02 | M3 x 10 self-tapping (plastic) | 2 | Fastener |  | Ears to pods |  | Proposed |  |
| ZS-F03 | M2 x 6 self-tapping | 2 | Fastener |  | Sensor sled |  | Proposed |  |
| ZS-F04 | 2.5 mm PT screw x 12 | 2 | Fastener |  | Face carrier posts |  | Proposed |  |
| ZS-F05 | Zip tie 2.5 mm | 2 | Fastener |  | ESP32 cradle |  | Proposed |  |
| ZS-W01 | Silicone wire 28 AWG assorted + JST-SH/PH connectors | 1 set | Wiring |  | Neck + pods + tube | Harness | Proposed | ~14 conductors through 14 mm neck bore |
| ZS-109 | Battery tray | 1 | Printed | PETG | Head bulkhead back | Holds 503450 LiPo (slides in from top) | Design target | 2 x M2 x 6 into ZS-103 |
| ZS-B01 | 1S LiPo 503450 ~1000 mAh WITH protection PCM (DW01-class) | 1 | Purchased |  | ZS-109 tray | Untethered power | Approved | 503450 = 5.0 x 34 x 50 mm nominal; must have built-in protection (over-charge / over-discharge / over-current / short); JST-PH 2-pin matching PowerBoost polarity – CHECK polarity |
| ZS-B02 | Adafruit PowerBoost 1000C (MCP73871 charger + load-sharing power path + TPS61090 5.2 V boost) | 1 | Purchased | Adafruit #2465 | Head bulkhead back (x 12..48 z 158..181) | Charge + power path + 5 V boost | Approved | ~36 x 23 x 5 mm without USB-A (ESTIMATE; Adafruit lists 23 x 45 x 10 with USB-A); 1 A boost output limit; MCP73871 datasheet DS20002090; 2 x M2.5/M2 screws |
| ZS-B03 | SS12D00-class slide switch | 1 | Purchased |  | Head back shell slot (x~30 z~176) | PowerBoost EN to GND = OFF | Approved | Signal-level switch only (EN pin) |
| ZS-B04 | Resistors 100 k + 100 k (0.1%) + 100 nF | 1 set | Purchased |  | Torso harness | Battery voltage divider to GPIO5 (ADC1_CH4) | Approved |  |
| ZS-601 | Station LED plug | 1 | Printed | white PETG (mixing cavity white or PTFE-tape lined) | Pedestal underside at station | Holds white / 365 nm / 940 nm LED board under window | Design target | 2 x M3 x 8 self-tap |
| ZS-602 | Light shield (removable) | 1 | Printed | opaque black PETG or PLA (check with torch for pinholes; paint inside matte black) | Over crystal cup | Ambient shade + carries AS7341; skirt in groove = light trap | Design target | Lift 5 mm then slide forward (removal path checked: 4.2 mm to torso) |
| ZS-603 | Sensor mount disc | 1 | Printed | matte black PETG | Inside shield top | AS7341 board + 12 mm aperture + optional 20 mm UV-cut filter recess | Design target | 2 x M2 x 5 |
| ZS-604 | Driver bay cover | 1 | Printed | PLA | Pedestal bottom | Closes MOSFET driver bay | Design target | 2 x M2 x 6 self-tap |
| ZS-605 | Dark-reference plug | 1 | Printed | opaque black PLA (100% infill) | Crystal cup (instead of crystal) | Stray-light / dark-reference check | Design target |  |
| ZS-S01 | AS7341 11-channel spectral sensor breakout (Adafruit #4698 or equivalent) | 1 | Purchased | ams-OSRAM AS7341 datasheet DS000504 | ZS-603 in shield looking down | Crystal transmission / fluorescence raw channel counts F1-F8 (415-680 nm) + Clear + NIR (910 nm) + flicker | Approved | I2C 0x39 (fixed); board ~25.6 x 17.8 mm ESTIMATE; alternative AS7343 (14 ch) – verify its address and register map in its own ams-OSRAM datasheet before swapping |
| ZS-S02 | Borosilicate (or fused-silica) window disc 29.6 x 2 mm | 1 | Purchased |  | Cup bottom window seat | Passes 365 nm UV + visible + 940 nm | Approved | Do NOT use standard acrylic – it absorbs much of 365 nm |
| ZS-S03 | UV-cut longpass filter disc 20 x 2 mm (e.g. ~420 nm longpass or UV-blocking acrylic) | 1 | Purchased |  | ZS-603 recess | Blocks 365 nm leak into sensor in fluorescence mode | Optional | Remove for transmission mode |
| ZS-S04 | White LED 3.5 x 3.5 mm (high-CRI preferred) | 1 | Purchased |  | Station LED board | Transmission source | Approved | ~20 mA (ESTIMATE – set by resistor) |
| ZS-S05 | 365 nm UV-A LED 3.5 x 3.5 mm low-power (~20 mA) | 1 | Purchased |  | Station LED board | Fluorescence excitation | Approved | Check LED datasheet photobiological risk group (IEC 62471); see UV safety in ASSEMBLY.md |
| ZS-S06 | 940 nm IR LED 3.5 x 3.5 mm | 1 | Purchased |  | Station LED board | NIR transmission | Optional |  |
| ZS-S07 | Station LED board 20 x 20 mm (perfboard or custom) | 1 | Purchased/custom |  | ZS-601 pocket | Carries ZS-S04/05/06 | Proposed |  |
| ZS-S08 | Driver board: 3 x AO3400A logic-level N-MOSFET + 3 x 100 R gate + 3 x 100 k pull-down + LED resistors (white 100 R / UV 68 R / IR 180 R at 5 V ESTIMATE) | 1 | Purchased/custom |  | Pedestal driver bay | Low-side LED switches from GPIO 1 / 2 / 21 (v0.3) | Approved | Recompute resistors from the real LED Vf |
| ZS-S09 | Glass reed switch ~12 mm (normally open) | 1 | Purchased |  | Pedestal reed slot (x -32) | UV HARDWARE interlock (in series with UV LED) + shield sense | Approved | Glass – handle carefully |
| ZS-S10 | Neodymium magnet 6 x 2 mm | 1 | Purchased |  | Shield flange pocket above reed | Closes reed only when shield is seated | Approved |  |
| ZS-S11 | 4-pin magnetic pogo connector pair (receptacle + pads) | 1 | Purchased |  | Pedestal pocket (x 29..34) / shield flange | AS7341 VIN GND SDA SCL to removable shield | Approved | ~2.54 mm pitch ESTIMATE – pocket sized 5 x 8 mm |
| ZS-S12 | PTFE white reference disc 25.4 x 3 mm (virgin PTFE sheet) | 1 | Purchased |  | Crystal cup (calibration only) | White / diffuse-transmission reference | Approved | Keep clean; store in bag |
| ZS-W02 | 30 AWG silicone wire (11 conductors through tube) + twisted D+/D- pair | 1 set | Wiring |  | ZS-502 tube | USB + station harness | Proposed |  |
| J1 | USB-C 16-pin receptacle breakout (5.1k CC pull-downs on board) | 1 | Electrical / passive (v0.3 electrical) | Connector breakout 5 V / 3 A — | Pedestal rear | CC 5.1k = [OB]; only VBUS/GND/D+/D− used | ADD (module) | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| D1 | USBLC6-2SC6 | 1 | Electrical / passive (v0.3 electrical) | ESD array SOT-23-6 5.25 V working — | Pedestal, next to J1 | on D+/D−; VBUS pin to VBUS | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| D2 | SMBJ5.0A | 1 | Electrical / passive (v0.3 electrical) | TVS diode SMB (DO-214AA) 5.0 V standoff, 600 W pk — | Pedestal, after J1 | clamps hot-plug spikes on VBUS | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| F1 | PTC resettable fuse 2.0 A hold / ~4 A trip | 1 | Electrical / passive (v0.3 electrical) | Polyfuse 1812 6 V — | Pedestal | VBUS peak ≈1.87 A (charger limit 1.8 A + station LEDs 60 mA) | ADD · ESTIMATE | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C1 | 10 µF | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | Pedestal after F1 | VBUS local decoupling | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C2 | 47 µF | 1 | Electrical / passive (v0.3 electrical) | Polymer / low-ESR electrolytic radial 6.3 mm 10 V ±20% | Head, at U1 USB pad | absorbs cable inductance at charger input | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| F2 | PTC 2.0 A hold | 1 | Electrical / passive (v0.3 electrical) | Polyfuse 1812 6 V — | Battery lead | backup to cell PCM | ADD (optional) · ESTIMATE | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| SW1 | SS12D00 SPDT slide switch | 1 | Electrical / passive (v0.3 electrical) | Switch through-hole 2.54 mm 50 V / 0.5 A — | Head rear | EN to GND = OFF (switch closed = OFF). Charging still works when OFF. | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C3 | 220 µF | 1 | Electrical / passive (v0.3 electrical) | Polymer / low-ESR electrolytic radial 6.3 mm 10 V ±20% | At U1 5V out | boost output reservoir for LED + amp peaks | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C4 | 100 nF | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | At U1 5V out | HF decoupling | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C6 | 10 µF | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | At U0 5V pin | DevKit input decoupling | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| R1 | 100 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Torso harness | divider top: VBAT → VBAT_SENSE | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| R2 | 100 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Torso harness | Vadc = VBAT·R2/(R1+R2) = VBAT/2 → 1.50–2.10 V; I = 4.2/200k = 21 µA | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| C5 | 100 nF | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | At GPIO5 | ADC sample-hold reservoir; τ = 50k·100n = 5 ms | ADD | Sheet A — see docs/BOM_electrical.csv & docs/schematics/ |
| R3 | 2.2 kΩ (DNP if breakouts' parallel pull-ups ≤ 3.3 kΩ) | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Torso sled | SDA0 pull-up; tr = 0.847·R·C = 0.847·2.2k·100pF = 186 ns ≤ 300 ns (400 kHz) | ADD / DNP | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| R4 | 2.2 kΩ (DNP rule as R3) | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Torso sled | SCL0 pull-up; sink current 3.3/2.2k = 1.5 mA ≤ 3 mA | ADD / DNP | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| C7 | 100 nF at U3 IMU | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | U3 | add only if breakout lacks it | OB (usually) / ADD | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| C8 | 100 nF at U4 BME280 | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | U4 |  | OB / ADD | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| C9 | 100 nF at U5 BH1750 | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | U5 |  | OB / ADD | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| C10 | 100 nF at U6 MAX30102 | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | U6 | MAX30102 LED pulses need local cap | OB / ADD | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| C11 | 10 µF at U7 GNSS | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | U7 | GNSS acquisition current bursts | ADD (optional) | Sheet B — see docs/BOM_electrical.csv & docs/schematics/ |
| R5 | 33 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Near U0 | I2S0 BCLK series damping (long pod run) | ADD (optional) | Sheet C — see docs/BOM_electrical.csv & docs/schematics/ |
| R6 | 33 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Near U0 | I2S0 WS series damping | ADD (optional) | Sheet C — see docs/BOM_electrical.csv & docs/schematics/ |
| R7 | 22 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | At U9 SD | boot-mute pull-down: V = 5·22k/(1M+22k) = 0.108 V below 0.16 V shutdown threshold (assumes 1M [OB] pull-up — verify on your board) | ADD · ESTIMATE | Sheet C — see docs/BOM_electrical.csv & docs/schematics/ |
| C12 | 100 µF | 1 | Electrical / passive (v0.3 electrical) | Aluminium electrolytic radial 5 mm 10 V ±20% | At U9 VIN | class-D supply reservoir | ADD | Sheet C — see docs/BOM_electrical.csv & docs/schematics/ |
| C13 | 10 µF | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | At U9 VIN |  | ADD | Sheet C — see docs/BOM_electrical.csv & docs/schematics/ |
| U2 | SN74AHCT1G125 (or 1 gate of 74AHCT125) | 1 | Electrical / passive (v0.3 electrical) | Logic buffer SOT-23-5 / DIP-14 VCC 5 V — | Torso | 3.3 V → 5 V level shift (VIH = 2.0 V at 5 V) | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| C14 | 100 nF | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | At U2 |  | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| R8 | 330 Ω (300–500 Ω range) | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | At first LED DIN | damps ringing / protects first WS2812 input | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| C15 | 1000 µF | 1 | Electrical / passive (v0.3 electrical) | Aluminium electrolytic radial 8 mm 10 V ±20% | Chest ring 5V/GND | LED bulk — inrush & surge protection | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| C16 | 100 µF | 1 | Electrical / passive (v0.3 electrical) | Aluminium electrolytic radial 5 mm 10 V ±20% | Pod ring L |  | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| C17 | 100 µF | 1 | Electrical / passive (v0.3 electrical) | Aluminium electrolytic radial 5 mm 10 V ±20% | Pod ring R |  | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| C18 | 100 µF | 1 | Electrical / passive (v0.3 electrical) | Aluminium electrolytic radial 5 mm 10 V ±20% | Eye boards |  | ADD | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| LED1–48 | WS2812B (100 nF per LED on ring PCBs) | 48 | Electrical / passive (v0.3 electrical) | Smart LED 5050 5 V, 60 mA max each — | Chest 12, eyes 2×5, pods 2×12, crown 2 | 48·60 mA·8% brightness cap = 0.23 A peak (cap 10→8 % on 2026-11-09 |  D1) | OB (ring modules) · ESTIMATE | Sheet D — see docs/BOM_electrical.csv & docs/schematics/ |
| J2 | 4-pin magnetic pogo pair | 1 | Electrical / passive (v0.3 electrical) | Connector 2.54 mm pitch 2 A per pin (typ.) — | Pedestal ↔ shield | VBUS, GND, SDA1_P, SCL1_P | ADD · ESTIMATE | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R9 | 4.7 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Pedestal driver bay | SDA1 pull-up; in parallel with [OB] 10k → 3.2k | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R10 | 4.7 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Pedestal driver bay | SCL1 pull-up | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R11 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Pedestal | SDA1 series (hot-plug current limit) | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R12 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Pedestal | SCL1 series | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R13 | 10 kΩ (DNP if board has INT pull-up) | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Pedestal | AS_INT open-drain pull-up | ADD / DNP | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| D3 | TPD4E05U06 | 1 | Electrical / passive (v0.3 electrical) | ESD array USON-10 / SOT 5.5 V working — | At J2 | ESD on exposed pogo pins | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| C19 | 10 µF | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | At J2 (pedestal) | pogo VIN bulk | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| C20 | 100 nF | 1 | Electrical / passive (v0.3 electrical) | MLCC X7R 0603 16 V ±10% | At J2 |  | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| Q1 | AO3400A (white) | 1 | Electrical / passive (v0.3 electrical) | N-MOSFET logic level SOT-23 30 V, 5.7 A, Rds 33 mΩ @ 4.5 V — | Driver board ZS-S08 | Vgs(th) ≤ 1.45 V → fully on at 3.3 V for 20 mA | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| Q2 | AO3400A (UV) | 1 | Electrical / passive (v0.3 electrical) | N-MOSFET SOT-23 30 V — | Driver board |  | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| Q3 | AO3400A (IR, optional) | 1 | Electrical / passive (v0.3 electrical) | N-MOSFET SOT-23 30 V — | Driver board | gate on GPIO21 (v0.3) | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R14 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q1 gate series | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R15 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q2 gate series | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R16 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q3 gate series | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R17 | 100 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q1 gate pull-down (LED OFF at boot / floating) | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R18 | 100 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q2 gate pull-down | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R19 | 100 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | Q3 gate pull-down | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| D4 | White LED 3 mm / 3528 (ZS-S04) | 1 | Electrical / passive (v0.3 electrical) | LED 3 mm Vf ≈3.0 V @ 20 mA — | Station LED board |  | ADD · ESTIMATE Vf | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| D5 | 365 nm UV-A LED (ZS-S05) | 1 | Electrical / passive (v0.3 electrical) | LED 3535 Vf ≈3.6 V @ 20 mA — | Station LED board | check IEC 62471 risk group | ADD · ESTIMATE Vf | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| D6 | 940 nm IR LED (ZS-S06, optional) | 1 | Electrical / passive (v0.3 electrical) | LED 3 mm Vf ≈1.3 V @ 20 mA — | Station LED board |  | ADD (optional) · ESTIMATE Vf | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R20 | 100 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0805 0.125 W ±1% | LED board | (5.0−3.0)/0.020 = 100 Ω → 20 mA; P = 0.02²·100 = 0.04 W | ADD · ESTIMATE | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R21 | 68 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0805 0.125 W ±1% | LED board | (5.0−3.6)/0.020 = 70 Ω → E12 68 Ω → 20.6 mA; P = 0.029 W | ADD · ESTIMATE | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R22 | 180 Ω | 1 | Electrical / passive (v0.3 electrical) | Thick film 0805 0.125 W ±1% | LED board | (5.0−1.3)/0.020 = 185 Ω → 180 Ω → 20.6 mA; P = 0.076 W | ADD · ESTIMATE | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| S1 | Glass reed switch NO ~12 mm (ZS-S09) | 1 | Electrical / passive (v0.3 electrical) | Reed switch axial ≥100 V / 0.5 A — | Pedestal reed slot | in SERIES with UV LED supply: VBUS → S1 → UV_5V (hardware interlock) | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R23 | 12 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | SHIELD_SENSE = 5·20k/32k = 3.13 V (HIGH) when S1 closed; I = 0.16 mA | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| R24 | 20 kΩ | 1 | Electrical / passive (v0.3 electrical) | Thick film 0603 0.1 W ±1% | Driver board | pulls SHIELD_SENSE to 0 V when S1 open. If VBUS = 5.25 V → 3.28 V (≤ 3.6 V abs max OK) | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |
| C21 | 10 µF | 1 | Electrical / passive (v0.3 electrical) | MLCC X5R 0805 10 V ±10% | LED board | LED switching decoupling | ADD | Sheet E — see docs/BOM_electrical.csv & docs/schematics/ |



# 4. Print plan

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


### Per-part settings (from the parts catalog)

| Part | Name | Material / colour | Orientation / settings | Qty |
|---|---|---|---|---|
| ZS-101 | Head shell, front | PETG matte navy #161C33 | Split face down; 0.2 mm, 4 walls, 20% gyroid, tree supports inside | 1 |
| ZS-102 | Head shell, back | PETG matte navy #161C33 | Split face down; 0.2 mm, 4 walls, 20%, tree supports | 1 |
| ZS-103 | Head bulkhead (mount plate) | PETG grey | Flat; 0.2 mm, 3 walls, 30% | 1 |
| ZS-104 | Visor | Smoked translucent PETG (or vacuum-formed 1.5 mm sheet) | Convex side up; 0.12 mm, 100%, sand + clear coat | 1 |
| ZS-105 | Face carrier (eye LEDs) | PETG black | Plate down; 0.2 mm, 3 walls | 1 |
| ZS-106 | Eye light pipe, left (happy arc) | Clear resin or clear PETG | Flat face down; resin 0.05 mm or PETG 100% | 1 |
| ZS-106 | Eye light pipe, right (happy arc) | Clear resin or clear PETG | Flat face down; resin 0.05 mm or PETG 100% | 1 |
| ZS-107 | Crown accent light pipe, left | Clear resin | Flange down; 100% | 1 |
| ZS-107 | Crown accent light pipe, right | Clear resin | Flange down; 100% | 1 |
| ZS-108 | Neck coupler | PETG black | Upright; 0.2 mm, 100% | 1 |
| ZS-109 | Battery tray | PETG grey | Back down, lips up; 0.2 mm, 3 walls | 1 |
| ZS-201 | Ear pod, left (mic) | PETG matte navy #161C33 | Outer face up; 0.2 mm, 4 walls, supports under peg | 1 |
| ZS-202 | Ear pod, right (light) | PETG matte navy #161C33 | Outer face up; 0.2 mm, 4 walls | 1 |
| ZS-203 | Pod rim diffuser, left | Translucent white PETG (violet from LEDs) | Flat; 0.2 mm, 100% | 1 |
| ZS-203 | Pod rim diffuser, right | Translucent white PETG | Flat; 0.2 mm, 100% | 1 |
| ZS-204 | Pod cap, left (mic holes) | PETG gloss black | Outer face up; 0.12 mm | 1 |
| ZS-205 | Pod cap, right (light window) | PETG gloss black + clear window | Outer face up; 0.12 mm | 1 |
| ZS-206 | Rabbit ear, left | PETG matte navy #161C33 | Lying on back face, slots up; 0.16 mm, 4 walls | 1 |
| ZS-206 | Rabbit ear, right | PETG matte navy #161C33 | Lying on back face, slots up; 0.16 mm | 1 |
| ZS-301 | Torso shell, front | PETG matte navy #161C33 | Split face down; 0.2 mm, 4 walls, supports | 1 |
| ZS-302 | Torso shell, back | PETG matte navy #161C33 | Split face down; 0.2 mm, 4 walls | 1 |
| ZS-303 | Torso bulkhead / ESP32 cradle | PETG grey | Flat, rails up; 0.2 mm, 30% | 1 |
| ZS-304 | Sensor sled (IMU + BME280) | PETG grey | Flat; 0.2 mm | 1 |
| ZS-305 | Chest core housing | PETG black | Flange down; 0.16 mm, 100% | 1 |
| ZS-306 | Chest ring diffuser | Translucent white PETG (cyan from LEDs) | Flat; 100% | 1 |
| ZS-307 | Chest centre lens | Clear (if MAX30102) or violet translucent | Dome up; resin or PETG 100% | 1 |
| ZS-401 | Arm + mitten hand, left | PETG matte navy #161C33 | Peg up; 0.16 mm, supports under hand | 1 |
| ZS-401 | Arm + mitten hand, right | PETG matte navy #161C33 | Peg up; 0.16 mm | 1 |
| ZS-402 | Leg + foot, left | PETG matte navy #161C33 | Peg up; 0.16 mm, supports under foot | 1 |
| ZS-402 | Leg + foot, right | PETG matte navy #161C33 | Peg up; 0.16 mm | 1 |
| ZS-501 | Pedestal (rock hex) + station body | PLA dark grey/black; 15% infill, station walls 100% | Bottom down; 0.28 mm, 3 walls | 1 |
| ZS-502 | Support tube (bought, cut) | Clear acrylic tube 12 OD x 8 ID x 75 | Cut + deburr (not printed) | 1 |
| ZS-601 | Station LED plug | White PETG; cavity PTFE-tape lined | Flange down; 0.2 mm, 100% | 1 |
| ZS-602 | Light shield (removable) | Opaque black PETG/PLA; inside matte black | Top down; 4 walls, 100% top | 1 |
| ZS-603 | Sensor mount disc (AS7341) | Matte black PETG | Flat; 100% | 1 |
| ZS-604 | Driver bay cover | PLA black | Flat; 0.2 mm | 1 |
| ZS-605 | Dark-reference plug | Opaque black PLA 100% | Knob up; 100% | 1 |

Test-print first: one leg peg + socket, one pod peg, one split boss with insert, the neck coupler and the shield-groove ring. Adjust clearances before printing full shells.


# 5. Parts catalog — every part labeled and shown

## Exploded view, every part numbered

<img src='img/exploded_numbered.png'>

| # | Part no. | Name | Type |
|---|---|---|---|
| 1 | ZS-101 | Head shell, front | printed (AI-generated CAD) |
| 2 | ZS-102 | Head shell, back | printed (AI-generated CAD) |
| 3 | ZS-103 | Head bulkhead (mount plate) | printed (AI-generated CAD) |
| 4 | ZS-104 | Visor | printed (AI-generated CAD) |
| 5 | ZS-105 | Face carrier (eye LEDs) | printed (AI-generated CAD) |
| 6 | ZS-106 | Eye light pipe, left (happy arc) | printed (AI-generated CAD) |
| 7 | ZS-106 | Eye light pipe, right (happy arc) | printed (AI-generated CAD) |
| 8 | ZS-107 | Crown accent light pipe, left | printed (AI-generated CAD) |
| 9 | ZS-107 | Crown accent light pipe, right | printed (AI-generated CAD) |
| 10 | ZS-108 | Neck coupler | printed (AI-generated CAD) |
| 11 | ZS-109 | Battery tray | printed (AI-generated CAD) |
| 12 | ZS-201 | Ear pod, left (mic) | printed (AI-generated CAD) |
| 13 | ZS-202 | Ear pod, right (light) | printed (AI-generated CAD) |
| 14 | ZS-203 | Pod rim diffuser, left | printed (AI-generated CAD) |
| 15 | ZS-203 | Pod rim diffuser, right | printed (AI-generated CAD) |
| 16 | ZS-204 | Pod cap, left (mic holes) | printed (AI-generated CAD) |
| 17 | ZS-205 | Pod cap, right (light window) | printed (AI-generated CAD) |
| 18 | ZS-206 | Rabbit ear, left | printed (AI-generated CAD) |
| 19 | ZS-206 | Rabbit ear, right | printed (AI-generated CAD) |
| 20 | ZS-301 | Torso shell, front | printed (AI-generated CAD) |
| 21 | ZS-302 | Torso shell, back | printed (AI-generated CAD) |
| 22 | ZS-303 | Torso bulkhead / ESP32 cradle | printed (AI-generated CAD) |
| 23 | ZS-304 | Sensor sled (IMU + BME280) | printed (AI-generated CAD) |
| 24 | ZS-305 | Chest core housing | printed (AI-generated CAD) |
| 25 | ZS-306 | Chest ring diffuser | printed (AI-generated CAD) |
| 26 | ZS-307 | Chest centre lens | printed (AI-generated CAD) |
| 27 | ZS-401 | Arm + mitten hand, left | printed (AI-generated CAD) |
| 28 | ZS-401 | Arm + mitten hand, right | printed (AI-generated CAD) |
| 29 | ZS-402 | Leg + foot, left | printed (AI-generated CAD) |
| 30 | ZS-402 | Leg + foot, right | printed (AI-generated CAD) |
| 31 | ZS-501 | Pedestal (rock hex) + station body | printed (AI-generated CAD) |
| 32 | ZS-502 | Support tube (bought, cut) | printed (AI-generated CAD) |
| 33 | ZS-601 | Station LED plug | printed (AI-generated CAD) |
| 34 | ZS-602 | Light shield (removable) | printed (AI-generated CAD) |
| 35 | ZS-603 | Sensor mount disc (AS7341) | printed (AI-generated CAD) |
| 36 | ZS-604 | Driver bay cover | printed (AI-generated CAD) |
| 37 | PX | AS7341 11-ch spectral breakout (ZS-S01) | third-party module proxy |
| 38 | PX | ESP32-S3 DevKitC-1 (RB-001) | third-party module proxy |
| 39 | PX | ICM-42688-P IMU breakout (RB-002) | third-party module proxy |
| 40 | PX | BH1750 light breakout (RB-003) | third-party module proxy |
| 41 | PX | BME280 breakout (RB-004) | third-party module proxy |
| 42 | PX | MAX30102 breakout (RB-005, optional, non-medical) | third-party module proxy |
| 43 | PX | INMP441 I2S mic breakout (RB-006) | third-party module proxy |
| 44 | PX | NEO-M9N-class GNSS (RB-007, optional) | third-party module proxy |
| 45 | PX | Crystal sample (example only) | third-party module proxy |
| 46 | PX | Window disc 29.6 x 2 (ZS-S02) | third-party module proxy |
| 47 | PX | Crown accent LED board, 2x WS2812B (ZS-E03) | third-party module proxy |
| 48 | PX | Eye LED strip L, 5x WS2812B (ZS-E02) | third-party module proxy |
| 49 | PX | Eye LED strip R, 5x WS2812B (ZS-E02) | third-party module proxy |
| 50 | PX | 940 nm IR LED (ZS-S06, optional) | third-party module proxy |
| 51 | PX | WS2812B 12-LED ring, chest (ZS-E01) | third-party module proxy |
| 52 | PX | WS2812B 12-LED ring, left pod (ZS-E01) | third-party module proxy |
| 53 | PX | WS2812B 12-LED ring, right pod (ZS-E01) | third-party module proxy |
| 54 | PX | 365 nm UV-A LED (ZS-S05) — EYE HAZARD | third-party module proxy |
| 55 | PX | White LED (ZS-S04) | third-party module proxy |
| 56 | PX | 1S LiPo 503450 ~1000 mAh, protected (ZS-B01) | third-party module proxy |
| 57 | PX | Magnet 6 x 2 mm (ZS-S10) | third-party module proxy |
| 58 | PX | MAX98357A I2S amp breakout (ZS-E05) | third-party module proxy |
| 59 | PX | Pogo pads 4-pin (ZS-S11) | third-party module proxy |
| 60 | PX | Pogo receptacle 4-pin (ZS-S11) | third-party module proxy |
| 61 | PX | Adafruit PowerBoost 1000C (ZS-B02) | third-party module proxy |
| 62 | PX | Reed switch (ZS-S09) — UV interlock | third-party module proxy |
| 63 | PX | Slide switch EN (ZS-B03) | third-party module proxy |
| 64 | PX | 28 mm 8 ohm speaker (ZS-E06) | third-party module proxy |
| 65 | PX | Station driver board, Q1-Q3 (ZS-S08) | third-party module proxy |
| 66 | PX | Station LED board 20x20 (ZS-S07) | third-party module proxy |
| 67 | PX | USB-C receptacle breakout (ZS-E07) | third-party module proxy |
| 68 | PX | UV-cut filter 20 x 2 (ZS-S03, optional) | third-party module proxy |


## Part cards

Each card shows part number, name, material, print orientation, quantity, fasteners and sub-assembly. Printed parts = AI-generated CAD; PX = third-party module proxy (envelope ESTIMATE).

<div class='cards'><img src='parts/ZS-101_head_shell_front.png'><img src='parts/ZS-102_head_shell_back.png'><img src='parts/ZS-103_head_bulkhead.png'><img src='parts/ZS-104_visor.png'><img src='parts/ZS-105_face_carrier.png'><img src='parts/ZS-106_eye_lightpipe_L.png'><img src='parts/ZS-106_eye_lightpipe_R.png'><img src='parts/ZS-107_accent_lightpipe_L.png'><img src='parts/ZS-107_accent_lightpipe_R.png'><img src='parts/ZS-108_neck_coupler.png'><img src='parts/ZS-109_battery_tray.png'><img src='parts/ZS-201_ear_pod_L_mic.png'><img src='parts/ZS-202_ear_pod_R_light.png'><img src='parts/ZS-203_pod_rim_diffuser_L.png'><img src='parts/ZS-203_pod_rim_diffuser_R.png'><img src='parts/ZS-204_pod_cap_L_mic.png'><img src='parts/ZS-205_pod_cap_R_light.png'><img src='parts/ZS-206_ear_L.png'><img src='parts/ZS-206_ear_R.png'><img src='parts/ZS-301_torso_shell_front.png'><img src='parts/ZS-302_torso_shell_back.png'><img src='parts/ZS-303_torso_bulkhead_esp32_cradle.png'><img src='parts/ZS-304_sensor_sled.png'><img src='parts/ZS-305_chest_core_housing.png'><img src='parts/ZS-306_chest_ring_diffuser.png'><img src='parts/ZS-307_chest_center_lens.png'><img src='parts/ZS-401_arm_L.png'><img src='parts/ZS-401_arm_R.png'><img src='parts/ZS-402_leg_L.png'><img src='parts/ZS-402_leg_R.png'><img src='parts/ZS-501_pedestal.png'><img src='parts/ZS-502_support_tube_acrylic.png'><img src='parts/ZS-601_station_led_plug.png'><img src='parts/ZS-602_light_shield.png'><img src='parts/ZS-603_sensor_mount.png'><img src='parts/ZS-604_driver_bay_cover.png'><img src='parts/ZS-605_dark_reference_plug.png'><img src='parts/PX_AS7341_breakout.png'><img src='parts/PX_RB-001_esp32s3_devkitc1.png'><img src='parts/PX_RB-002_icm42688_imu.png'><img src='parts/PX_RB-003_bh1750_podR.png'><img src='parts/PX_RB-004_bme280.png'><img src='parts/PX_RB-005_max30102.png'><img src='parts/PX_RB-006_inmp441_podL.png'><img src='parts/PX_RB-007_gnss_head.png'><img src='parts/PX_crystal_sample.png'><img src='parts/PX_crystal_window_borosilicate.png'><img src='parts/PX_led_accent_pcb.png'><img src='parts/PX_led_eyeL.png'><img src='parts/PX_led_eyeR.png'><img src='parts/PX_led_ir940.png'><img src='parts/PX_led_ring12_chest.png'><img src='parts/PX_led_ring12_podL.png'><img src='parts/PX_led_ring12_podR.png'><img src='parts/PX_led_uv365.png'><img src='parts/PX_led_white.png'><img src='parts/PX_lipo_503450_protected.png'><img src='parts/PX_magnet_6x2.png'><img src='parts/PX_max98357a_amp.png'><img src='parts/PX_pogo_pads_4p.png'><img src='parts/PX_pogo_receptacle_4p.png'><img src='parts/PX_powerboost_1000c.png'><img src='parts/PX_ptfe_white_reference_25x3.png'><img src='parts/PX_reed_switch.png'><img src='parts/PX_slide_switch_EN.png'><img src='parts/PX_speaker28.png'><img src='parts/PX_station_driver_board.png'><img src='parts/PX_station_led_board.png'><img src='parts/PX_usbc_breakout_pedestal.png'><img src='parts/PX_uv_cut_filter_optional.png'></div>


# 6. Sub-assemblies

## Head (incl. power bay)

<img src='img/sub_head.png'>

## Ear pods

<img src='img/sub_ear_pods.png'>

## Torso / chest

<img src='img/sub_torso_chest.png'>

## Limbs

<img src='img/sub_limbs.png'>

## Pedestal + crystal station

<img src='img/sub_pedestal_station.png'>

## Power

<img src='img/sub_power.png'>



# 7. Assembly steps

Each step: image (highlighted = new parts), fasteners, actions, wiring for that step (with its schematic sheet), and a check you must pass before moving on.

<div class='step' markdown='1'>

## Step 1 — Heat-set inserts in all shell halves

<img src='img/step_01.png'>

**Parts added:** ZS-101 Head shell, front, ZS-301 Torso shell, front

**Fasteners:** 8 × ZS-F01 M3 heat-set inserts (short, brass): 4 in the ZS-101 head front bosses, 4 in the ZS-301 torso front bosses. Pilot 4.0 mm (ESTIMATE — match your insert).

**Do:**

1. Iron at ~220 °C (PLA) / ~245 °C (PETG). Push each insert straight down with the insert tip; stop 0.2 mm proud and flatten with a flat block while warm.
2. Let cool 1 min before handling. Clear any plastic that squeezed into the thread with an M3 screw.

**Wiring:** None.

<div class='chk' markdown='1'>**CHECK before moving on:** An M3 screw threads fully into every insert by hand; no insert spins or tilts.</div>

</div>

<div class='step' markdown='1'>

## Step 2 — Visor and accent light-pipes into the front head shell

<img src='img/step_02.png'>

**Parts added:** ZS-104 Visor, ZS-107 Crown accent light pipe, left, ZS-107 Crown accent light pipe, right, PX Crown accent LED board, 2x WS2812B (ZS-E03)

**Fasteners:** Visor: clear silicone or CA onto the ZS-101 ledge. Accent pipes: press-fit.

**Do:**

1. Insert the visor from the inside of ZS-101 so the lip sits on the inner ledge.
2. Press both accent pipes into their slots; the flat faces point inward to the accent LED PCB.
3. Seat the accent PCB (crown pair, last 2 LEDs in the chain) behind the pipes.

**Wiring:** Accent PCB: 5V_SYS / GND / DIN from eye R DOUT (26 AWG power, 30 AWG data). See Sheet D.

<div class='sch'><img src='schematics/D_led_chain.png'><p class='cap'>Wiring for this step: docs/schematics/D_led_chain (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Visor sits flush with no light gap; pipes do not rattle.</div>

</div>

<div class='step' markdown='1'>

## Step 3 — Face carrier, eye light-pipes and eye LED boards

<img src='img/step_03.png'>

**Parts added:** ZS-105 Face carrier (eye LEDs), ZS-106 Eye light pipe, left (happy arc), ZS-106 Eye light pipe, right (happy arc), PX Eye LED strip L, 5x WS2812B (ZS-E02), PX Eye LED strip R, 5x WS2812B (ZS-E02)

**Fasteners:** Face carrier: 2 × 2.5 mm PT × 12 (ZS-F04) into ZS-103 posts. Eye boards: hot glue or M2 × 4 (ESTIMATE).

**Do:**

1. Press the eye pipes into the face carrier.
2. Mount eye L and eye R LED boards (5 LEDs each) against the pipe ends.
3. Fit C18 (100 µF 10 V) across 5V/GND at the eye boards.

**Wiring:** Chain: chest ring DOUT → eye L DIN → eye L DOUT → eye R DIN → … (Sheet D). C18 at eyes.

<div class='sch'><img src='schematics/D_led_chain.png'><p class='cap'>Wiring for this step: docs/schematics/D_led_chain (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Pipes aligned with LEDs; continuity 5V_SYS ↔ every eye LED 5V pin; no short 5V↔GND (> 1 kΩ).</div>

</div>

<div class='step' markdown='1'>

## Step 4 — Power bay: battery tray, protected LiPo, PowerBoost 1000C, EN switch

<img src='img/step_04.png'>

**Parts added:** ZS-109 Battery tray, PX 1S LiPo 503450 ~1000 mAh, protected (ZS-B01), PX Adafruit PowerBoost 1000C (ZS-B02), PX Slide switch EN (ZS-B03)

**Fasteners:** Battery tray: 2 × M2 × 6 into ZS-103. PowerBoost: 2 × M2 to ZS-103. Cell: foam tape only — never screws or clamps on the cell.

**Do:**

1. ADULT step. Check the cell is a PROTECTED cell (PCM board under the yellow tape) and reads 3.6–4.2 V before installing.
2. Fit SW1 so OFF = EN tied to GND. Solder F2 (optional) in the battery + lead, then BT1 to U1 BAT via JST-PH 2.0.
3. Solder C2 (47 µF) at U1 USB input, C3 (220 µF) + C4 (100 nF) at U1 5V output.

**Wiring:** Sheet A. BAT: 24 AWG ≤ 75 mm. 5V_SYS and VBUS: 2 × 26 AWG in parallel. EN: 30 AWG.

<div class='sch'><img src='schematics/A_power.png'><p class='cap'>Wiring for this step: docs/schematics/A_power (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** SW1 OFF: U1 5V output < 0.3 V. SW1 ON (no USB): 5.1–5.25 V, blue LED on. Plug USB: charge LED on, 5V stays up.</div>

</div>

<div class='step' markdown='1'>

## Step 5 — Head bulkhead: amplifier, speaker, GNSS

<img src='img/step_05.png'>

**Parts added:** ZS-103 Head bulkhead (mount plate), PX MAX98357A I2S amp breakout (ZS-E05), PX 28 mm 8 ohm speaker (ZS-E06), PX NEO-M9N-class GNSS (RB-007, optional)

**Fasteners:** Bulkhead ZS-103 is clamped later by the 4 × RB-008 shell screws. Amp + GNSS: M2 × 4 or VHB tape (ESTIMATE). Speaker: hot glue ring.

**Do:**

1. Fix the bulkhead into the back head shell.
2. Mount U9 MAX98357A; fit R7 22 kΩ SD → GND, C12 100 µF + C13 10 µF at VIN.
3. Mount speaker SPK1; mount optional U7 GNSS with antenna side up, C11 10 µF at its VIN.

**Wiring:** Sheet C (I2S1 GPIO15/16/7, SD GPIO6) and Sheet B (GNSS UART GPIO17/18). Speaker 26 AWG.

<div class='sch'><img src='schematics/C_audio.png'><p class='cap'>Wiring for this step: docs/schematics/C_audio (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** R7 measured 21.8–22.2 kΩ to GND; 8 Ω ±2 across SPK1; no short on 5V_SYS.</div>

</div>

<div class='step' markdown='1'>

## Step 6 — Ear pods: mic, light sensor, LED rings, caps and ears

<img src='img/step_06.png'>

**Parts added:** ZS-201 Ear pod, left (mic), ZS-202 Ear pod, right (light), ZS-203 Pod rim diffuser, left, ZS-203 Pod rim diffuser, right, ZS-204 Pod cap, left (mic holes), ZS-205 Pod cap, right (light window), ZS-206 Rabbit ear, left, ZS-206 Rabbit ear, right, PX BH1750 light breakout (RB-003), PX INMP441 I2S mic breakout (RB-006), PX WS2812B 12-LED ring, left pod (ZS-E01), PX WS2812B 12-LED ring, right pod (ZS-E01)

**Fasteners:** Ears to pods: 2 × ZS-F02 M3 × 10 self-tapping. Pod caps: snap / glue into the rims.

**Do:**

1. Left pod: INMP441 (U8) with its port facing the cap hole, L/R tied to GND.
2. Right pod: BH1750 (U5) behind the window, ADDR → GND for 0x23.
3. Mount both 12-LED rings behind the rim diffusers; C16/C17 100 µF on each ring.

**Wiring:** Sheet B (BH1750 on I2C0), Sheet C (INMP441 on I2S0 12/13/14), Sheet D (rings). 30 AWG signals, 26 AWG ring power.

<div class='sch'><img src='schematics/B_i2c0_sensors.png'><p class='cap'>Wiring for this step: docs/schematics/B_i2c0_sensors (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Continuity per pin from the pod connector to the module; mic port unobstructed; window clean.</div>

</div>

<div class='step' markdown='1'>

## Step 7 — Close the head

<img src='img/step_07.png'>

**Parts added:** ZS-102 Head shell, back, ZS-108 Neck coupler

**Fasteners:** 4 × RB-008 M3 × 8 through the back-shell clearance bosses into the ZS-F01 inserts. Neck coupler ZS-108 is captured by both shell pairs (no screws).

**Do:**

1. Route the head harness through the neck coupler first.
2. Close the back shell onto the front shell, pod pegs captured by the split.
3. Tighten diagonally, snug only (PLA cracks).

**Wiring:** Head harness exits the neck: 5V_SYS, GND, VBUS, D+, D−, LED DIN, I2S0 ×3, I2S1 ×3, AMP_SD, SDA0, SCL0, GNSS ×2, VBAT_SENSE (ESTIMATE 17 conductors).

<div class='chk' markdown='1'>**CHECK before moving on:** No pinched wire visible at the seam; the head harness pulls freely 5 mm.</div>

</div>

<div class='step' markdown='1'>

## Step 8 — ESP32-S3 DevKitC-1 into the torso cradle

<img src='img/step_08.png'>

**Parts added:** ZS-303 Torso bulkhead / ESP32 cradle, PX ESP32-S3 DevKitC-1 (RB-001)

**Fasteners:** DevKit: 2 × ZS-F05 2.5 mm zip ties in the cradle rails. Cradle ZS-303 is clamped later by the torso RB-008 screws.

**Do:**

1. Fit C6 10 µF across the DevKit 5V/GND pins.
2. Fit the level-shifter U2 + C14 and R8 330 Ω on the LED data line.
3. Fit R1/R2 100 kΩ + C5 100 nF battery divider at GPIO5.

**Wiring:** Sheets A + D. Use the USB-C port marked USB (native, GPIO19/20) for the pigtail: D+/D−/GND only — do NOT connect pigtail VBUS.

<div class='sch'><img src='schematics/A_power.png'><p class='cap'>Wiring for this step: docs/schematics/A_power (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** DevKit powers from 5V_SYS only; GPIO5 reads VBAT/2 (1.5–2.1 V) with a multimeter.</div>

</div>

<div class='step' markdown='1'>

## Step 9 — Sensor sled: IMU + BME280

<img src='img/step_09.png'>

**Parts added:** ZS-304 Sensor sled (IMU + BME280), PX ICM-42688-P IMU breakout (RB-002), PX BME280 breakout (RB-004)

**Fasteners:** Sled: 2 × M2 × 6 PT (ZS-F03) into ZS-303. Breakouts: M2 × 4 or nylon standoffs (ESTIMATE).

**Do:**

1. Mount U3 ICM-42688-P flat, axis arrows recorded in your notes (needed for firmware).
2. Mount U4 BME280 near the vent slot, away from the ESP32 (self-heating).
3. Daisy-chain STEMMA-QT / Qwiic cables; fit R3/R4 2.2 kΩ only if needed (see Electrical).

**Wiring:** Sheet B: I2C0 SDA GPIO8 / SCL GPIO9, 3V3, GND. JST-SH 1.0 mm.

<div class='sch'><img src='schematics/B_i2c0_sensors.png'><p class='cap'>Wiring for this step: docs/schematics/B_i2c0_sensors (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** I2C scan on bus 0 shows 0x68 (or 0x69) and 0x76 (or 0x77).</div>

</div>

<div class='step' markdown='1'>

## Step 10 — Chest core: LED ring, diffuser, lens, MAX30102

<img src='img/step_10.png'>

**Parts added:** ZS-305 Chest core housing, ZS-306 Chest ring diffuser, ZS-307 Chest centre lens, PX WS2812B 12-LED ring, chest (ZS-E01), PX MAX30102 breakout (RB-005, optional, non-medical)

**Fasteners:** Chest core flange is captured behind the torso front shell (no screws). Diffuser + lens: press-fit.

**Do:**

1. Seat the 12-LED chest ring; solder C15 1000 µF 10 V across its 5V/GND input (watch polarity).
2. Fit MAX30102 (optional) behind the lens with its window touching the lens.
3. Press in diffuser and lens.

**Wiring:** Sheet D (chest ring = first LED, DIN from R8). Sheet B (MAX30102 0x57).

<div class='sch'><img src='schematics/D_led_chain.png'><p class='cap'>Wiring for this step: docs/schematics/D_led_chain (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** C15 polarity checked twice; 5V↔GND > 1 kΩ after the cap charges.</div>

</div>

<div class='step' markdown='1'>

## Step 11 — Close the torso, capturing arms and legs

<img src='img/step_11.png'>

**Parts added:** ZS-401 Arm + mitten hand, left, ZS-401 Arm + mitten hand, right, ZS-402 Leg + foot, left, ZS-402 Leg + foot, right, ZS-302 Torso shell, back

**Fasteners:** 4 × RB-008 M3 × 8 into the torso ZS-F01 inserts. Limbs are captured by their flanged pegs — no screws.

**Do:**

1. Place all four limb pegs into the front shell sockets.
2. Join head harness to torso harness at the JST-PH joints.
3. Close the back shell; tighten diagonally.

**Wiring:** Harness table in the Electrical Specifications section: torso ↔ head and torso ↔ tube.

<div class='chk' markdown='1'>**CHECK before moving on:** Each limb rotates with light friction and does not fall out.</div>

</div>

<div class='step' markdown='1'>

## Step 12 — Pedestal: USB-C entry and support tube

<img src='img/step_12.png'>

**Parts added:** ZS-501 Pedestal (rock hex) + station body, PX USB-C receptacle breakout (ZS-E07), ZS-502 Support tube (bought, cut)

**Fasteners:** USB-C breakout: glued in the pedestal back pocket. Tube ZS-502: glued into the pedestal; slip fit into the torso.

**Do:**

1. Mount J1, then F1, D2, C1 and D1 right behind it.
2. Feed the 11-conductor station/robot harness up the tube.
3. Press the tube into the pedestal socket.

**Wiring:** Sheet A (VBUS_IN → F1 → VBUS). VBUS/GND 2 × 26 AWG; D+/D− twisted 30 AWG.

<div class='sch'><img src='schematics/A_power.png'><p class='cap'>Wiring for this step: docs/schematics/A_power (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** With a 5 V/3 A adapter: VBUS 4.75–5.25 V at the tube top; VBUS↔GND not shorted.</div>

</div>

<div class='step' markdown='1'>

## Step 13 — Crystal station: LED plug, window

<img src='img/step_13.png'>

**Parts added:** ZS-601 Station LED plug, PX Station LED board 20x20 (ZS-S07), PX White LED (ZS-S04), PX 365 nm UV-A LED (ZS-S05) — EYE HAZARD, PX 940 nm IR LED (ZS-S06, optional), PX Window disc 29.6 x 2 (ZS-S02)

**Fasteners:** LED plug ZS-601: 2 × M3 × 8 PT into the pedestal. Window: inserted from BELOW into its seat (the cup lip holds it from above); no glue on the optical faces.

**Do:**

1. Solder D4 white + R20 100 Ω, D5 UV + R21 68 Ω, D6 IR + R22 180 Ω (optional), C21 10 µF on the LED board.
2. Clean the borosilicate window with isopropyl alcohol and insert it from below into its seat.
3. Push ZS-601 up behind the window and fix it.

**Wiring:** Sheet E (anodes to VBUS; UV anode to UV_5V after S1).

<div class='sch'><img src='schematics/E_crystal_station.png'><p class='cap'>Wiring for this step: docs/schematics/E_crystal_station (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Diode-test each LED (white/UV glow faintly; IR seen through a phone camera). Do not look at the UV LED.</div>

</div>

<div class='step' markdown='1'>

## Step 14 — Station: pogo receptacle, reed switch, driver board, cover

<img src='img/step_14.png'>

**Parts added:** PX Pogo receptacle 4-pin (ZS-S11), PX Reed switch (ZS-S09) — UV interlock, PX Station driver board, Q1-Q3 (ZS-S08), ZS-604 Driver bay cover

**Fasteners:** Driver board sits in the bay under ZS-604; cover: 2 × M2 × 6 PT. Reed: hot glue in its slot (glass — no pressure). Pogo receptacle: pocket at x 29…34, glue.

**Do:**

1. Build the driver board: Q1–Q3 AO3400A, R14–R16 100 Ω, R17–R19 100 kΩ, R23 12 kΩ / R24 20 kΩ, R9/R10 4.7 kΩ, R11/R12 100 Ω.
2. Mount J2 pogo receptacle + D3 + C19/C20.
3. Reed S1 in SERIES with the UV LED supply.

**Wiring:** Sheet E. Gates GPIO1 / GPIO2 / GPIO21; SHIELD_SENSE GPIO40; I2C1 GPIO10/11; INT GPIO41.

<div class='sch'><img src='schematics/E_crystal_station.png'><p class='cap'>Wiring for this step: docs/schematics/E_crystal_station (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Shield off: SHIELD_SENSE 0 V and UV_5V 0 V. Magnet held at the reed: SHIELD_SENSE ≈ 3.1 V.</div>

</div>

<div class='step' markdown='1'>

## Step 15 — Light shield and sensor mount (AS7341)

<img src='img/step_15.png'>

**Parts added:** ZS-602 Light shield (removable), ZS-603 Sensor mount disc (AS7341), PX AS7341 11-ch spectral breakout (ZS-S01), PX Pogo pads 4-pin (ZS-S11), PX Magnet 6 x 2 mm (ZS-S10), PX UV-cut filter 20 x 2 (ZS-S03, optional)

**Fasteners:** AS7341 board: 2 × M2 × 5 to ZS-603; ZS-603 glued into the shield top. Magnet Ø6 × 2: glued into the flange pocket above the reed.

**Do:**

1. Mount the AS7341 breakout in ZS-603, sensor facing down through the aperture.
2. Insert the optional UV-cut filter for fluorescence mode only.
3. Press the magnet into the shield flange above the reed position.

**Wiring:** Sheet E (pogo: VBUS, GND, SDA1_P, SCL1_P).

<div class='sch'><img src='schematics/E_crystal_station.png'><p class='cap'>Wiring for this step: docs/schematics/E_crystal_station (pin labels = ESP32-S3 GPIO numbers)</p></div>

<div class='chk' markdown='1'>**CHECK before moving on:** Seat the shield: I2C scan on bus 1 shows 0x39 AND GPIO40 reads HIGH. Lift it: both go away.</div>

</div>

<div class='step' markdown='1'>

## Step 16 — Mount the robot on the pedestal

<img src='img/step_16.png'>

**Parts added:** ZS-108 Neck coupler, ZS-502 Support tube (bought, cut)

**Fasteners:** Robot slides onto the tube (slip fit, no screws). Optionally 1 drop of removable adhesive (ESTIMATE).

**Do:**

1. Join the tube harness to the torso harness.
2. Lower the robot onto the tube, front facing the station.
3. Final dress of wires; nothing touching the station window.

**Wiring:** All sheets. Final continuity check per the harness table.

<div class='chk' markdown='1'>**CHECK before moving on:** Robot stands without wobble; total height 314 mm ±2 (DESIGN TARGET).</div>

</div>



# 8. Electrical Specifications

> **DESIGN TARGET — not built or bench-tested.** Values marked **ESTIMATE** are calculated from datasheet typicals, not measured. **[OB]** = part already on a bought module (do not add). **[ADD]** = part you add. **DNP** = do not populate unless the check says so. Designators match `docs/BOM_electrical.csv` and the schematics.

> **Changed 2026-11-09:** LED brightness cap 10 % → **8 %** everywhere (firmware 20/255), decided by Robot X under Cory's delegation (docs/DESIGN_DECISIONS.md D1). Peak 5V_SYS budget 1.03 A → 0.97 A (ESTIMATE).

## Pin map — DECIDED (Robot X under Cory's delegation, 2026-11-09)

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

## Voltage rails

| Rail | Range | Source | Max load | Notes |
|---|---|---|---|---|
| VBUS_IN / VBUS | 4.75–5.25 V | USB-C J1 → F1 (2 A hold) | ≈1.87 A peak (ESTIMATE) | Needs a **5 V / 3 A** USB-C supply. A PC USB2 port (0.5 A) is NOT enough. |
| VBAT | 3.0–4.2 V (3.7 V nom.) | BT1 protected LiPo | ≈1.5 A to the boost at 1 A out (ESTIMATE) | Cell PCM cuts at ≈2.5–3.0 V |
| VS (load-share) | VBUS or VBAT | MCP73871 inside U1 | — | internal to the PowerBoost |
| 5V_SYS | 5.2 V ±2% | U1 TPS61090 boost | ≈1 A | Peak budget ≈0.97 A with the 8 % LED cap — tight, see power budget |
| 3V3 | 3.3 V | DevKit on-board LDO [OB] | keep external load < 100 mA (ESTIMATE) | feeds I2C0 sensors, mic, GNSS |
| AS7341 internal | 3.3 V / 1.8 V | breakout regulators [OB] | — | fed from VBUS through the pogo |
| UV_5V | 0 V or VBUS | reed S1 (shield seated) | ≈21 mA | hardware UV interlock |

## Power budget (ESTIMATE)

**5V_SYS (boost output, ≈1 A limit)**

| Load | Typical | Peak | Basis |
|---|---|---|---|
| ESP32-S3 + Wi-Fi | 0.10 A | 0.35 A | datasheet TX burst |
| WS2812B quiescent (48 × ≈1 mA) | 0.05 A | 0.05 A |  |
| WS2812B light, 8 % brightness cap (firmware 20/255) | 0.08 A | 0.23 A | 48 × 60 mA × 8 % |
| MAX98357A + 8 Ω speaker | 0.03 A | 0.25 A | ≈1 W peaks |
| Sensors + mic (via 3V3 LDO) | 0.01 A | 0.05 A | MAX30102 LED pulses |
| GNSS (optional) | 0.03 A | 0.04 A | acquisition |
| **Total 5V_SYS** | **≈0.30 A** | **≈0.97 A** | **tight vs ≈1 A** with the 8 % LED cap (DECIDED, D1); drop GNSS if brown-outs |

**VBUS (USB-C input)**

| Load | Typical | Peak |
|---|---|---|
| MCP73871 charger + load-share (input limit) | 0.6 A | 1.8 A |
| Station LEDs (one at a time, 20 mA) | 0.00 A | 0.02 A (0.06 A if all on) |
| AS7341 breakout | <0.01 A | <0.01 A |
| **Total VBUS** | **≈0.6 A** | **≈1.87 A** |

Battery runtime (ESTIMATE): 1000 mAh × 3.7 V × 0.85 boost efficiency / (5.2 V × 0.30 A) ≈ **2.0 h typical**, ≈0.6 h at sustained peak.

## Resistors (every one)

| Ref | Sheet | Value | Pkg | Power | Tol. | OB/ADD | ESTIMATE? | Calculation / purpose |
|---|---|---|---|---|---|---|---|---|
| R1 | A | 100 kΩ | 0603 | 0.1 W | ±1% | ADD |  | divider top: VBAT → VBAT_SENSE |
| R2 | A | 100 kΩ | 0603 | 0.1 W | ±1% | ADD |  | Vadc = VBAT·R2/(R1+R2) = VBAT/2 → 1.50–2.10 V; I = 4.2/200k = 21 µA |
| R3 | B | 2.2 kΩ (DNP if breakouts' parallel pull-ups ≤ 3.3 kΩ) | 0603 | 0.1 W | ±1% | ADD / DNP |  | SDA0 pull-up; tr = 0.847·R·C = 0.847·2.2k·100pF = 186 ns ≤ 300 ns (400 kHz) |
| R4 | B | 2.2 kΩ (DNP rule as R3) | 0603 | 0.1 W | ±1% | ADD / DNP |  | SCL0 pull-up; sink current 3.3/2.2k = 1.5 mA ≤ 3 mA |
| R5 | C | 33 Ω | 0603 | 0.1 W | ±1% | ADD (optional) |  | I2S0 BCLK series damping (long pod run) |
| R6 | C | 33 Ω | 0603 | 0.1 W | ±1% | ADD (optional) |  | I2S0 WS series damping |
| R7 | C | 22 kΩ | 0603 | 0.1 W | ±1% | ADD | ESTIMATE | boot-mute pull-down: V = 5·22k/(1M+22k) = 0.108 V below 0.16 V shutdown threshold (assumes 1M [OB] pull-up — verify on your board) |
| R8 | D | 330 Ω (300–500 Ω range) | 0603 | 0.1 W | ±1% | ADD |  | damps ringing / protects first WS2812 input |
| R9 | E | 4.7 kΩ | 0603 | 0.1 W | ±1% | ADD |  | SDA1 pull-up; in parallel with [OB] 10k → 3.2k |
| R10 | E | 4.7 kΩ | 0603 | 0.1 W | ±1% | ADD |  | SCL1 pull-up |
| R11 | E | 100 Ω | 0603 | 0.1 W | ±1% | ADD |  | SDA1 series (hot-plug current limit) |
| R12 | E | 100 Ω | 0603 | 0.1 W | ±1% | ADD |  | SCL1 series |
| R13 | E | 10 kΩ (DNP if board has INT pull-up) | 0603 | 0.1 W | ±1% | ADD / DNP |  | AS_INT open-drain pull-up |
| R14 | E | 100 Ω | 0603 | 0.1 W | ±1% | ADD |  | Q1 gate series |
| R15 | E | 100 Ω | 0603 | 0.1 W | ±1% | ADD |  | Q2 gate series |
| R16 | E | 100 Ω | 0603 | 0.1 W | ±1% | ADD |  | Q3 gate series |
| R17 | E | 100 kΩ | 0603 | 0.1 W | ±1% | ADD |  | Q1 gate pull-down (LED OFF at boot / floating) |
| R18 | E | 100 kΩ | 0603 | 0.1 W | ±1% | ADD |  | Q2 gate pull-down |
| R19 | E | 100 kΩ | 0603 | 0.1 W | ±1% | ADD |  | Q3 gate pull-down |
| R20 | E | 100 Ω | 0805 | 0.125 W | ±1% | ADD | ESTIMATE | (5.0−3.0)/0.020 = 100 Ω → 20 mA; P = 0.02²·100 = 0.04 W |
| R21 | E | 68 Ω | 0805 | 0.125 W | ±1% | ADD | ESTIMATE | (5.0−3.6)/0.020 = 70 Ω → E12 68 Ω → 20.6 mA; P = 0.029 W |
| R22 | E | 180 Ω | 0805 | 0.125 W | ±1% | ADD | ESTIMATE | (5.0−1.3)/0.020 = 185 Ω → 180 Ω → 20.6 mA; P = 0.076 W |
| R23 | E | 12 kΩ | 0603 | 0.1 W | ±1% | ADD |  | SHIELD_SENSE = 5·20k/32k = 3.13 V (HIGH) when S1 closed; I = 0.16 mA |
| R24 | E | 20 kΩ | 0603 | 0.1 W | ±1% | ADD |  | pulls SHIELD_SENSE to 0 V when S1 open. If VBUS = 5.25 V → 3.28 V (≤ 3.6 V abs max OK) |

### LED current-limit resistors, worked: R = (V − Vf) / If, P = If² · R

| LED | V supply | Vf (ESTIMATE) | If target | R calc | Chosen (E12) | Actual If | P in R |
|---|---|---|---|---|---|---|---|
| D4 white | 5.0 V | 3.0 V | 20 mA | (5.0−3.0)/0.020 = 100 Ω | R20 100 Ω | 20.0 mA | 0.040 W |
| D5 UV 365 nm | 5.0 V | 3.6 V | 20 mA | (5.0−3.6)/0.020 = 70 Ω | R21 68 Ω | 20.6 mA | 0.029 W |
| D6 IR 940 nm | 5.0 V | 1.3 V | 20 mA | (5.0−1.3)/0.020 = 185 Ω | R22 180 Ω | 20.6 mA | 0.076 W |

Use 0805 0.125 W parts (≥ 1.6× margin). Check your LEDs' real Vf at 20 mA and recompute; AO3400A drop (≈0.7 mV at 20 mA) is negligible.

### Other resistor math

- **Battery sense (R1/R2 100 k / 100 k, C5 100 nF):** Vadc = VBAT × 100k / 200k → 1.50 V (3.0 V) … 2.10 V (4.2 V). Inside the ESP32-S3 ADC 11 dB range (≈0–2.9 V usable, ESTIMATE). Divider current 4.2 V / 200 kΩ = 21 µA (≈0.5 mAh/day). Firmware: VBAT = 2 × Vadc (calibrate with a multimeter once).
- **I2C0 pull-ups (R3/R4 2.2 kΩ):** rise time tr = 0.847 × R × Cbus = 0.847 × 2.2 kΩ × 100 pF ≈ 186 ns (I2C fast mode limit 300 ns). Most breakouts already carry 10 kΩ (or 4.7 kΩ) each — measure SDA→3V3 with power off: if ≤ 3.3 kΩ already, leave R3/R4 out (DNP).
- **I2C1 pull-ups (R9/R10 4.7 kΩ ∥ on-board 10 kΩ = 3.2 kΩ):** longer pogo + tube run (≈30 cm, ESTIMATE ≈150 pF): tr ≈ 0.847 × 3.2k × 150 pF ≈ 0.41 µs → run I2C1 at **100 kHz** (limit 1 µs). R11/R12 100 Ω series limit hot-plug current.
- **MOSFET gates:** R14–R16 100 Ω limit GPIO edge current into the gate; R17–R19 100 kΩ hold the LEDs OFF while the ESP32 boots (pins float).
- **Shield sense (R23 12 kΩ / R24 20 kΩ):** shield seated → S1 closed → SHIELD_SENSE = 5.0 × 20/(12+20) = 3.13 V (HIGH; 3.28 V at 5.25 V — below 3.6 V abs. max). Shield off → R24 pulls to 0 V (LOW). Current 0.16 mA.
- **Amp boot-mute (R7 22 kΩ):** with the breakout's 1 MΩ SD pull-up [OB] to VIN: V = 5 × 22k / 1.022M = 0.108 V < 0.16 V shutdown threshold → amp OFF until GPIO6 drives HIGH. ESTIMATE — verify your breakout's pull-up value.
- **NeoPixel data (R8 330 Ω):** in the 300–500 Ω range; sits at the first LED's DIN to damp ringing on the 3.3→5 V buffered line.

## Capacitors (every one)

| Ref | Sheet | Value | Type | Pkg | Voltage | Tol. | OB/ADD | Location / purpose |
|---|---|---|---|---|---|---|---|---|
| C1 | A | 10 µF | MLCC X5R | 0805 | 10 V | ±10% | ADD | Pedestal after F1 — VBUS local decoupling |
| C2 | A | 47 µF | Polymer / low-ESR electrolytic | radial 6.3 mm | 10 V | ±20% | ADD | Head, at U1 USB pad — absorbs cable inductance at charger input |
| C3 | A | 220 µF | Polymer / low-ESR electrolytic | radial 6.3 mm | 10 V | ±20% | ADD | At U1 5V out — boost output reservoir for LED + amp peaks |
| C4 | A | 100 nF | MLCC X7R | 0603 | 16 V | ±10% | ADD | At U1 5V out — HF decoupling |
| C6 | A | 10 µF | MLCC X5R | 0805 | 10 V | ±10% | ADD | At U0 5V pin — DevKit input decoupling |
| C5 | A | 100 nF | MLCC X7R | 0603 | 16 V | ±10% | ADD | At GPIO5 — ADC sample-hold reservoir; τ = 50k·100n = 5 ms |
| C7 | B | 100 nF at U3 IMU | MLCC X7R | 0603 | 16 V | ±10% | OB (usually) / ADD | U3 — add only if breakout lacks it |
| C8 | B | 100 nF at U4 BME280 | MLCC X7R | 0603 | 16 V | ±10% | OB / ADD | U4 |
| C9 | B | 100 nF at U5 BH1750 | MLCC X7R | 0603 | 16 V | ±10% | OB / ADD | U5 |
| C10 | B | 100 nF at U6 MAX30102 | MLCC X7R | 0603 | 16 V | ±10% | OB / ADD | U6 — MAX30102 LED pulses need local cap |
| C11 | B | 10 µF at U7 GNSS | MLCC X5R | 0805 | 10 V | ±10% | ADD (optional) | U7 — GNSS acquisition current bursts |
| C12 | C | 100 µF | Aluminium electrolytic | radial 5 mm | 10 V | ±20% | ADD | At U9 VIN — class-D supply reservoir |
| C13 | C | 10 µF | MLCC X5R | 0805 | 10 V | ±10% | ADD | At U9 VIN |
| C14 | D | 100 nF | MLCC X7R | 0603 | 16 V | ±10% | ADD | At U2 |
| C15 | D | 1000 µF | Aluminium electrolytic | radial 8 mm | 10 V | ±20% | ADD | Chest ring 5V/GND — LED bulk — inrush & surge protection |
| C16 | D | 100 µF | Aluminium electrolytic | radial 5 mm | 10 V | ±20% | ADD | Pod ring L |
| C17 | D | 100 µF | Aluminium electrolytic | radial 5 mm | 10 V | ±20% | ADD | Pod ring R |
| C18 | D | 100 µF | Aluminium electrolytic | radial 5 mm | 10 V | ±20% | ADD | Eye boards |
| C19 | E | 10 µF | MLCC X5R | 0805 | 10 V | ±10% | ADD | At J2 (pedestal) — pogo VIN bulk |
| C20 | E | 100 nF | MLCC X7R | 0603 | 16 V | ±10% | ADD | At J2 |
| C21 | E | 10 µF | MLCC X5R | 0805 | 10 V | ±10% | ADD | LED board — LED switching decoupling |

Rule: voltage rating ≥ 2× rail for MLCC (DC-bias derating), ≥ 1.6× for electrolytics/polymer. Watch polarity on C2, C3, C12, C15–C18.

## Diodes, fuses, switches, ICs, connectors

| Ref | Sheet | Part | Type | Pkg | Rating | OB/ADD | Note |
|---|---|---|---|---|---|---|---|
| J1 | A | USB-C 16-pin receptacle breakout (5.1k CC pull-downs on board) | Connector | breakout | 5 V / 3 A | ADD (module) | CC 5.1k = [OB]; only VBUS/GND/D+/D− used |
| D1 | A | USBLC6-2SC6 | ESD array | SOT-23-6 | 5.25 V working | ADD | on D+/D−; VBUS pin to VBUS |
| D2 | A | SMBJ5.0A | TVS diode | SMB (DO-214AA) | 5.0 V standoff, 600 W pk | ADD | clamps hot-plug spikes on VBUS |
| F1 | A | PTC resettable fuse 2.0 A hold / ~4 A trip | Polyfuse | 1812 | 6 V | ADD | VBUS peak ≈1.87 A (charger limit 1.8 A + station LEDs 60 mA) |
| U1 | A | Adafruit PowerBoost 1000C (ZS-B02) | Module | PCB 36×23 mm | in 5 V, out 5.2 V ≈1 A | ADD (module) | MCP73871 + TPS61090; on-board caps, EN & LBO pull-ups [OB] |
| BT1 | A | 1S LiPo 503450 ≈1000 mAh, with PCM (ZS-B01) | Battery | 50×34×5 mm | 3.0–4.2 V | ADD | PCM (over-charge/discharge/short) is [OB] in the cell |
| F2 | A | PTC 2.0 A hold | Polyfuse | 1812 | 6 V | ADD (optional) | backup to cell PCM |
| SW1 | A | SS12D00 SPDT slide switch | Switch | through-hole 2.54 mm | 50 V / 0.5 A | ADD | EN to GND = OFF (switch closed = OFF). Charging still works when OFF. |
| U2 | D | SN74AHCT1G125 (or 1 gate of 74AHCT125) | Logic buffer | SOT-23-5 / DIP-14 | VCC 5 V | ADD | 3.3 V → 5 V level shift (VIH = 2.0 V at 5 V) |
| LED1–48 | D | WS2812B (100 nF per LED on ring PCBs) | Smart LED | 5050 | 5 V, 60 mA max each | OB (ring modules) | 48·60 mA·8% brightness cap = 0.23 A peak (cap 10→8 % on 2026-11-09 |
| U10 | E | AS7341 breakout (ZS-S01) | Sensor module | breakout | VIN 3.3–5 V (on-board LDO) | ADD (module) | I2C 0x39 fixed; on-board 10k pull-ups and 1.8 V/3.3 V regs [OB] |
| J2 | E | 4-pin magnetic pogo pair | Connector | 2.54 mm pitch | 2 A per pin (typ.) | ADD | VBUS, GND, SDA1_P, SCL1_P |
| D3 | E | TPD4E05U06 | ESD array | USON-10 / SOT | 5.5 V working | ADD | ESD on exposed pogo pins |
| Q1 | E | AO3400A (white) | N-MOSFET logic level | SOT-23 | 30 V, 5.7 A, Rds 33 mΩ @ 4.5 V | ADD | Vgs(th) ≤ 1.45 V → fully on at 3.3 V for 20 mA |
| Q2 | E | AO3400A (UV) | N-MOSFET | SOT-23 | 30 V | ADD |  |
| Q3 | E | AO3400A (IR, optional) | N-MOSFET | SOT-23 | 30 V | ADD | gate on GPIO21 (v0.3) |
| D4 | E | White LED 3 mm / 3528 (ZS-S04) | LED | 3 mm | Vf ≈3.0 V @ 20 mA | ADD |  |
| D5 | E | 365 nm UV-A LED (ZS-S05) | LED | 3535 | Vf ≈3.6 V @ 20 mA | ADD | check IEC 62471 risk group |
| D6 | E | 940 nm IR LED (ZS-S06, optional) | LED | 3 mm | Vf ≈1.3 V @ 20 mA | ADD (optional) |  |
| S1 | E | Glass reed switch NO ~12 mm (ZS-S09) | Reed switch | axial | ≥100 V / 0.5 A | ADD | in SERIES with UV LED supply: VBUS → S1 → UV_5V (hardware interlock) |

**Flyback diodes:** none needed — there are no motors, relays or other inductive loads; the speaker is driven by a class-D bridge with its own protection. **ESD/TVS:** D1 (USB data), D2 (VBUS surge), D3 (exposed pogo pins). **Fuses:** F1 on VBUS, F2 (optional) on the battery lead, plus the cell's own PCM.

## Connectors and pitches

| Where | Connector | Pitch | Pins / note |
|---|---|---|---|
| I2C breakouts (U3–U6, U10 side) | JST-SH (STEMMA QT / Qwiic) | 1.0 mm | 4: GND, 3V3, SDA, SCL |
| Battery BT1 → U1 | JST-PH | 2.0 mm | 2 (check polarity — no standard!) |
| LED rings / eye boards | JST-PH | 2.0 mm | 3: 5V, DIN/DOUT, GND |
| Head ↔ torso, torso ↔ tube harness joints | JST-PH (or JST-GH for locking) | 2.0 mm (1.25 mm GH) | split into ≤ 6-pin groups |
| DevKit headers | Dupont female | 2.54 mm | or solder directly |
| Station shield ↔ pedestal J2 | 4-pin magnetic pogo | 2.54 mm | VBUS, GND, SDA1_P, SCL1_P |
| Pedestal power/data in J1 | USB-C receptacle breakout | — | 5.1 kΩ CC [OB] |
| Speaker | JST-PH or solder | 2.0 mm | 2 |

## Wire gauge per run

| Run | Current (peak) | Wire | Length (ESTIMATE) |
|---|---|---|---|
| VBUS / GND: J1 → tube → torso → head (U1) | ≤ 1.87 A | 2 × 26 AWG silicone in parallel each (or 1 × 22 AWG if it fits the tube) | ≈30 cm |
| 5V_SYS / GND: U1 → torso → LEDs, DevKit | ≤ 1.03 A | 2 × 26 AWG in parallel | ≈15 cm |
| BAT: BT1 → U1 | ≤ 1.5 A | 24 AWG | ≤ 75 mm |
| LED ring 5V/GND branches | ≤ 0.15 A each | 26 AWG | ≤ 15 cm |
| Speaker | ≤ 0.4 A | 26 AWG | ≤ 10 cm |
| All signals (I2C, I2S, gates, sense, LED data) | < 10 mA | 30 AWG silicone | — |
| USB D+ / D− | data | 30 AWG twisted pair, ≈ 1 twist/cm | keep < 30 cm |
| Station LED supply (VBUS in pedestal) | ≤ 60 mA | 28–30 AWG | ≤ 10 cm |

26 AWG silicone ≈ 0.134 Ω/m: 30 cm at 1.87 A on a single wire ≈ 75 mV drop each way — doubled wires halve it.

## Harness: tube (pedestal ↔ torso) — 11 conductors (ESTIMATE fit in 8 mm ID)

| # | Signal | Gauge |
|---|---|---|
| 1 | VBUS | 26 (×2 if room) |
| 2 | GND | 26 (×2 if room) |
| 3 | USB D+ | 30 twisted |
| 4 | USB D− | 30 twisted |
| 5 | SDA1 | 30 |
| 6 | SCL1 | 30 |
| 7 | G_WHITE (GPIO1) | 30 |
| 8 | G_UV (GPIO2) | 30 |
| 9 | G_IR (GPIO21) | 30 |
| 10 | AS_INT (GPIO41) | 30 |
| 11 | SHIELD_SENSE (GPIO40) | 30 |

## Per-module specifications

| Module | Supply | Current | I2C address | Interface / pins | Datasheet (verify revision) |
|---|---|---|---|---|---|
| U0 ESP32-S3 DevKitC-1 (RB-001) | 5 V in (on-board LDO → 3V3) | ≈100 mA typ, ≈350 mA Wi-Fi TX peak | — | USB (GPIO19/20), GPIO | [Espressif ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) · [DevKitC-1 guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/) |
| U3 ICM-42688-P (RB-002) | 3.3 V | ≈1 mA | 0x68 (0x69 if AD0 high) | I2C0 | [TDK ICM-42688-P](https://invensense.tdk.com/products/motion-tracking/6-axis/icm-42688-p/) |
| U4 BME280 (RB-004) | 3.3 V | ≈1 mA peak, µA avg | 0x76 (0x77) | I2C0 | [Bosch BME280](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/) |
| U5 BH1750 (RB-003) | 3.3 V | 0.12–0.19 mA | 0x23 (ADDR low) | I2C0 | [ROHM BH1750FVI](https://www.mouser.com/datasheet/2/348/bh1750fvi-e-186247.pdf) |
| U6 MAX30102 (RB-005, opt) | 3.3 V logic (LED 5 V on most breakouts) | ≈0.6 mA + LED pulses up to 50 mA | 0x57 | I2C0 | [ADI MAX30102](https://www.analog.com/en/products/max30102.html) |
| U7 NEO-M9N GNSS (RB-007, opt) | 3.3 V | ≈30–40 mA acquiring | — | UART GPIO17/18 | [u-blox NEO-M9N](https://www.u-blox.com/en/product/neo-m9n-module) |
| U8 INMP441 (RB-006) | 3.3 V | 1.4 mA | — | I2S0 GPIO12/13/14 | [TDK INMP441](https://invensense.tdk.com/products/digital/inmp441/) |
| U9 MAX98357A (ZS-E05) | 5 V (2.5–5.5 V) | ≈3 mA idle, ≈250 mA at ~1 W/8 Ω (ESTIMATE) | — | I2S1 GPIO15/16/7, SD GPIO6 | [ADI MAX98357A](https://www.analog.com/en/products/max98357a.html) |
| U10 AS7341 breakout (ZS-S01) | VIN 3.3–5 V (on-board regs) | ≈0.3 mA active | 0x39 (fixed) | I2C1 GPIO10/11, INT GPIO41 | [ams-OSRAM AS7341 DS000504](https://look.ams-osram.com/m/24266a3e584de4db/original/AS7341-DS000504.pdf) |
| LED1–48 WS2812B | 5 V (VIH ≥ 0.7·VDD → needs U2) | ≈1 mA idle, 60 mA max each | — | 1-wire 800 kHz, GPIO4 | [WS2812B (Adafruit PDF)](https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf) |
| U2 SN74AHCT1G125 | 5 V | < 0.1 mA | — | buffer | [TI SN74AHCT1G125](https://www.ti.com/product/SN74AHCT1G125) |
| U1 PowerBoost 1000C | in 5 V USB / 3.7 V LiPo; out 5.2 V | ≈1 A out (TPS61090), charge 1 A | — | EN, LBO pins | [Adafruit guide](https://learn.adafruit.com/adafruit-powerboost-1000c-load-share-usb-charge-boost) · [MCP73871](https://cdn-shop.adafruit.com/datasheets/MCP73871.pdf) · [TPS61090](https://www.ti.com/product/TPS61090) |
| Q1–Q3 AO3400A | Vgs(th) 0.65–1.45 V | 5.7 A max (20 mA used) | — | GPIO1/2/21 | [AOS AO3400A](https://www.aosmd.com/res/datasheets/AO3400A.pdf) |
| D1 USBLC6-2SC6 · D3 TPD4E05U06 · D2 SMBJ5.0A | 5 V lines | — | — | protection | [ST USBLC6-2](https://www.st.com/en/protections-and-emi-filters/usblc6-2.html) · [TI TPD4E05U06](https://www.ti.com/product/TPD4E05U06) · [Littelfuse SMBJ](https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj.aspx) |

I2C address map: **bus 0** 0x23, 0x57, 0x68, 0x76 — no conflicts; **bus 1** 0x39 alone. All datasheet links were correct when written; always check the current revision.

## Schematics

Drawn in net-label style: **same net name = connected**. [OB] on-board, [ADD] added.

<div class="sch"><img src="schematics/A_power.png"><p class="cap">Sheet A — Power (SVG: docs/schematics/A_power.svg)</p></div>

<div class="sch"><img src="schematics/B_i2c0_sensors.png"><p class="cap">Sheet B — I2C0 sensors + GNSS (SVG: docs/schematics/B_i2c0_sensors.svg)</p></div>

<div class="sch"><img src="schematics/C_audio.png"><p class="cap">Sheet C — Audio (SVG: docs/schematics/C_audio.svg)</p></div>

<div class="sch"><img src="schematics/D_led_chain.png"><p class="cap">Sheet D — LED chain (SVG: docs/schematics/D_led_chain.svg)</p></div>

<div class="sch"><img src="schematics/E_crystal_station.png"><p class="cap">Sheet E — Crystal station (SVG: docs/schematics/E_crystal_station.svg)</p></div>



# 9. Stage gates 0–3 (PROPOSED — reconstructed)

<div class="box">The original brief's Stage 0–3 text was not available to this build; these gates are a <b>reconstruction</b> from the system logic and must be confirmed by Cory.</div>

| Stage | Build state | Gate (all must pass) |
|---|---|---|
| **0 — bare DevKit** | ESP32-S3 on USB only, no wiring | Firmware flashes; native USB prints the boot line + self-test JSON; host `spark_brain` receives frames (Wi-Fi build only: softAP visible when SPARK_AP_PASS is set, WebSocket :81 streams JSON) |
| **1 — sensor bench harness** | U3–U8 on a breadboard / JST-SH chain | I2C0 scan = 0x23, 0x57, 0x68, 0x76 (present ones); every sensor value plausible and labelled MEASURED; mic RMS rises when you speak; GNSS NMEA (if fitted) |
| **2 — power + LEDs + audio in the body** | Steps 1–11 | SW1 OFF → 5V_SYS < 0.3 V; ON → 5.1–5.25 V; battery reading within 0.05 V of a meter; 48 LEDs light in order at ≤ 8 % (firmware cap); amp silent at boot, tone plays when unmuted; no brown-out during LED + audio + Wi-Fi together (log min 5V_SYS) |
| **3 — full assembly + station** | Steps 12–16 | Shield interlock: shield off → UV_5V = 0 V and SHIELD_SENSE LOW; shield on → 0x39 on I2C1 + HIGH; dark/white calibration passes repeatability (§11); robot height 314 mm ±2 |


# 10. Firmware flash and bring-up tests

Spark firmware **zs-0.4.0** is in this package at `firmware/zeref_spark_fw/` (PlatformIO, Arduino framework). It is built on Cory's Reality Bridge Probe v0.2, which is kept unchanged in `firmware/reality_bridge_probe_v0.2_original/` (his repo is not edited). It covers every DECIDED pin: LEDs (GPIO4, cap 8 %), amp I2S1 15/16/7 + mute 6 (tones and streamed speech), battery GPIO5, station I2C1 10/11 + INT 41, gates 1/2/21, shield sense 40, UV guard. Compile status: USB build and Wi-Fi build both **compile**; **never run on a board yet**.

1. Install VS Code + PlatformIO. Open `firmware/zeref_spark_fw`.
2. Connect the DevKit's **USB** (native) port — the firmware talks over native USB CDC (needed for speech audio). If upload fails: hold BOOT, tap RESET, release BOOT.
3. `pio run -e zeref-spark -t upload` then `pio device monitor`. Expect the line `Zeref Spark zs-0.4.0 (Reality Bridge Probe 0.2.0 base)` and a self-test JSON.
4. On the host: `cd host && python -m spark_brain serial /dev/ttyACM0` (the brain lives there — the robot is the nervous system). Optional Wi-Fi: build with `SPARK_AP_PASS='8+ chars' pio run -e zeref-spark-wifi` (Wi-Fi accepts speech lines only; UV/SCAN stay USB-only).



| Test | How | Pass |
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


# 11. Crystal station calibration

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



# 12. Troubleshooting

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
