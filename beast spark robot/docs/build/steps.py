"""Assembly step data + step images (highlight new parts, ghost context). DESIGN TARGET."""
import sys, json
sys.path.insert(0, "/workspace/zeref-spark/docs/build")
from partmeta import M
HEAD = [s for s in M if M[s][5] in ("head", "power")]
PODS = [s for s in M if M[s][5] == "pods"]
TORSO = [s for s in M if M[s][5] == "torso"]
LIMBS = [s for s in M if M[s][5] == "limbs"]
PED = [s for s in M if M[s][5] == "pedestal"] + [s for s in M if M[s][5] == "station" and s not in ("ZS-605_dark_reference_plug", "PX_ptfe_white_reference_25x3")]
F = (-1.0, -1.5, 0.7)   # front-left-high
B = (1.0, 1.6, 0.6)     # back-right-high
S = [
 dict(t="Heat-set inserts in all shell halves", ctx=HEAD + TORSO, new=["ZS-101_head_shell_front", "ZS-301_torso_shell_front"], cam=F,
      fas="8 × ZS-F01 M3 heat-set inserts (short, brass): 4 in the ZS-101 head front bosses, 4 in the ZS-301 torso front bosses. Pilot 4.0 mm (ESTIMATE — match your insert).",
      act=["Iron at ~220 °C (PLA) / ~245 °C (PETG). Push each insert straight down with the insert tip; stop 0.2 mm proud and flatten with a flat block while warm.", "Let cool 1 min before handling. Clear any plastic that squeezed into the thread with an M3 screw."],
      wire="None.", chk="An M3 screw threads fully into every insert by hand; no insert spins or tilts."),
 dict(t="Visor and accent light-pipes into the front head shell", ctx=HEAD, new=["ZS-104_visor", "ZS-107_accent_lightpipe_L", "ZS-107_accent_lightpipe_R", "PX_led_accent_pcb"], cam=F,
      fas="Visor: clear silicone or CA onto the ZS-101 ledge. Accent pipes: press-fit.",
      act=["Insert the visor from the inside of ZS-101 so the lip sits on the inner ledge.", "Press both accent pipes into their slots; the flat faces point inward to the accent LED PCB.", "Seat the accent PCB (crown pair, last 2 LEDs in the chain) behind the pipes."],
      wire="Accent PCB: 5V_SYS / GND / DIN from eye R DOUT (26 AWG power, 30 AWG data). See Sheet D.", chk="Visor sits flush with no light gap; pipes do not rattle."),
 dict(t="Face carrier, eye light-pipes and eye LED boards", ctx=HEAD, new=["ZS-105_face_carrier", "ZS-106_eye_lightpipe_L", "ZS-106_eye_lightpipe_R", "PX_led_eyeL", "PX_led_eyeR"], cam=F,
      fas="Face carrier: 2 × 2.5 mm PT × 12 (ZS-F04) into ZS-103 posts. Eye boards: hot glue or M2 × 4 (ESTIMATE).",
      act=["Press the eye pipes into the face carrier.", "Mount eye L and eye R LED boards (5 LEDs each) against the pipe ends.", "Fit C18 (100 µF 10 V) across 5V/GND at the eye boards."],
      wire="Chain: chest ring DOUT → eye L DIN → eye L DOUT → eye R DIN → … (Sheet D). C18 at eyes.", chk="Pipes aligned with LEDs; continuity 5V_SYS ↔ every eye LED 5V pin; no short 5V↔GND (> 1 kΩ)."),
 dict(t="Power bay: battery tray, protected LiPo, PowerBoost 1000C, EN switch", ctx=HEAD, new=["ZS-109_battery_tray", "PX_lipo_503450_protected", "PX_powerboost_1000c", "PX_slide_switch_EN"], cam=B,
      fas="Battery tray: 2 × M2 × 6 into ZS-103. PowerBoost: 2 × M2 to ZS-103. Cell: foam tape only — never screws or clamps on the cell.",
      act=["ADULT step. Check the cell is a PROTECTED cell (PCM board under the yellow tape) and reads 3.6–4.2 V before installing.", "Fit SW1 so OFF = EN tied to GND. Solder F2 (optional) in the battery + lead, then BT1 to U1 BAT via JST-PH 2.0.", "Solder C2 (47 µF) at U1 USB input, C3 (220 µF) + C4 (100 nF) at U1 5V output."],
      wire="Sheet A. BAT: 24 AWG ≤ 75 mm. 5V_SYS and VBUS: 2 × 26 AWG in parallel. EN: 30 AWG.", chk="SW1 OFF: U1 5V output < 0.3 V. SW1 ON (no USB): 5.1–5.25 V, blue LED on. Plug USB: charge LED on, 5V stays up."),
 dict(t="Head bulkhead: amplifier, speaker, GNSS", ctx=HEAD, new=["ZS-103_head_bulkhead", "PX_max98357a_amp", "PX_speaker28", "PX_RB-007_gnss_head"], cam=B,
      fas="Bulkhead ZS-103 is clamped later by the 4 × RB-008 shell screws. Amp + GNSS: M2 × 4 or VHB tape (ESTIMATE). Speaker: hot glue ring.",
      act=["Fix the bulkhead into the back head shell.", "Mount U9 MAX98357A; fit R7 22 kΩ SD → GND, C12 100 µF + C13 10 µF at VIN.", "Mount speaker SPK1; mount optional U7 GNSS with antenna side up, C11 10 µF at its VIN."],
      wire="Sheet C (I2S1 GPIO15/16/7, SD GPIO6) and Sheet B (GNSS UART GPIO17/18). Speaker 26 AWG.", chk="R7 measured 21.8–22.2 kΩ to GND; 8 Ω ±2 across SPK1; no short on 5V_SYS."),
 dict(t="Ear pods: mic, light sensor, LED rings, caps and ears", ctx=PODS, new=PODS, cam=(-1.2, -1.0, 0.5),
      fas="Ears to pods: 2 × ZS-F02 M3 × 10 self-tapping. Pod caps: snap / glue into the rims.",
      act=["Left pod: INMP441 (U8) with its port facing the cap hole, L/R tied to GND.", "Right pod: BH1750 (U5) behind the window, ADDR → GND for 0x23.", "Mount both 12-LED rings behind the rim diffusers; C16/C17 100 µF on each ring."],
      wire="Sheet B (BH1750 on I2C0), Sheet C (INMP441 on I2S0 12/13/14), Sheet D (rings). 30 AWG signals, 26 AWG ring power.", chk="Continuity per pin from the pod connector to the module; mic port unobstructed; window clean."),
 dict(t="Close the head", ctx=HEAD + PODS, new=["ZS-102_head_shell_back", "ZS-108_neck_coupler"], cam=F,
      fas="4 × RB-008 M3 × 8 through the back-shell clearance bosses into the ZS-F01 inserts. Neck coupler ZS-108 is captured by both shell pairs (no screws).",
      act=["Route the head harness through the neck coupler first.", "Close the back shell onto the front shell, pod pegs captured by the split.", "Tighten diagonally, snug only (PLA cracks)."],
      wire="Head harness exits the neck: 5V_SYS, GND, VBUS, D+, D−, LED DIN, I2S0 ×3, I2S1 ×3, AMP_SD, SDA0, SCL0, GNSS ×2, VBAT_SENSE (ESTIMATE 17 conductors).", chk="No pinched wire visible at the seam; the head harness pulls freely 5 mm."),
 dict(t="ESP32-S3 DevKitC-1 into the torso cradle", ctx=TORSO, new=["ZS-303_torso_bulkhead_esp32_cradle", "PX_RB-001_esp32s3_devkitc1"], cam=B,
      fas="DevKit: 2 × ZS-F05 2.5 mm zip ties in the cradle rails. Cradle ZS-303 is clamped later by the torso RB-008 screws.",
      act=["Fit C6 10 µF across the DevKit 5V/GND pins.", "Fit the level-shifter U2 + C14 and R8 330 Ω on the LED data line.", "Fit R1/R2 100 kΩ + C5 100 nF battery divider at GPIO5."],
      wire="Sheets A + D. Use the USB-C port marked USB (native, GPIO19/20) for the pigtail: D+/D−/GND only — do NOT connect pigtail VBUS.", chk="DevKit powers from 5V_SYS only; GPIO5 reads VBAT/2 (1.5–2.1 V) with a multimeter."),
 dict(t="Sensor sled: IMU + BME280", ctx=TORSO, new=["ZS-304_sensor_sled", "PX_RB-002_icm42688_imu", "PX_RB-004_bme280"], cam=B,
      fas="Sled: 2 × M2 × 6 PT (ZS-F03) into ZS-303. Breakouts: M2 × 4 or nylon standoffs (ESTIMATE).",
      act=["Mount U3 ICM-42688-P flat, axis arrows recorded in your notes (needed for firmware).", "Mount U4 BME280 near the vent slot, away from the ESP32 (self-heating).", "Daisy-chain STEMMA-QT / Qwiic cables; fit R3/R4 2.2 kΩ only if needed (see Electrical)."],
      wire="Sheet B: I2C0 SDA GPIO8 / SCL GPIO9, 3V3, GND. JST-SH 1.0 mm.", chk="I2C scan on bus 0 shows 0x68 (or 0x69) and 0x76 (or 0x77)."),
 dict(t="Chest core: LED ring, diffuser, lens, MAX30102", ctx=TORSO, new=["ZS-305_chest_core_housing", "ZS-306_chest_ring_diffuser", "ZS-307_chest_center_lens", "PX_led_ring12_chest", "PX_RB-005_max30102"], cam=F,
      fas="Chest core flange is captured behind the torso front shell (no screws). Diffuser + lens: press-fit.",
      act=["Seat the 12-LED chest ring; solder C15 1000 µF 10 V across its 5V/GND input (watch polarity).", "Fit MAX30102 (optional) behind the lens with its window touching the lens.", "Press in diffuser and lens."],
      wire="Sheet D (chest ring = first LED, DIN from R8). Sheet B (MAX30102 0x57).", chk="C15 polarity checked twice; 5V↔GND > 1 kΩ after the cap charges."),
 dict(t="Close the torso, capturing arms and legs", ctx=TORSO + LIMBS, new=LIMBS + ["ZS-302_torso_shell_back"], cam=F,
      fas="4 × RB-008 M3 × 8 into the torso ZS-F01 inserts. Limbs are captured by their flanged pegs — no screws.",
      act=["Place all four limb pegs into the front shell sockets.", "Join head harness to torso harness at the JST-PH joints.", "Close the back shell; tighten diagonally."],
      wire="Harness table in the Electrical Specifications section: torso ↔ head and torso ↔ tube.", chk="Each limb rotates with light friction and does not fall out."),
 dict(t="Pedestal: USB-C entry and support tube", ctx=PED, new=["ZS-501_pedestal", "PX_usbc_breakout_pedestal", "ZS-502_support_tube_acrylic"], cam=(0.9, -1.4, 0.8),
      fas="USB-C breakout: glued in the pedestal back pocket. Tube ZS-502: glued into the pedestal; slip fit into the torso.",
      act=["Mount J1, then F1, D2, C1 and D1 right behind it.", "Feed the 11-conductor station/robot harness up the tube.", "Press the tube into the pedestal socket."],
      wire="Sheet A (VBUS_IN → F1 → VBUS). VBUS/GND 2 × 26 AWG; D+/D− twisted 30 AWG.", chk="With a 5 V/3 A adapter: VBUS 4.75–5.25 V at the tube top; VBUS↔GND not shorted."),
 dict(t="Crystal station: LED plug, window", ctx=PED, new=["ZS-601_station_led_plug", "PX_station_led_board", "PX_led_white", "PX_led_uv365", "PX_led_ir940", "PX_crystal_window_borosilicate"], cam=(0.9, -1.4, 0.8),
      fas="LED plug ZS-601: 2 × M3 × 8 PT into the pedestal. Window: inserted from BELOW into its seat (the cup lip holds it from above); no glue on the optical faces.",
      act=["Solder D4 white + R20 100 Ω, D5 UV + R21 68 Ω, D6 IR + R22 180 Ω (optional), C21 10 µF on the LED board.", "Clean the borosilicate window with isopropyl alcohol and insert it from below into its seat.", "Push ZS-601 up behind the window and fix it."],
      wire="Sheet E (anodes to VBUS; UV anode to UV_5V after S1).", chk="Diode-test each LED (white/UV glow faintly; IR seen through a phone camera). Do not look at the UV LED."),
 dict(t="Station: pogo receptacle, reed switch, driver board, cover", ctx=PED, new=["PX_pogo_receptacle_4p", "PX_reed_switch", "PX_station_driver_board", "ZS-604_driver_bay_cover"], cam=(0.9, -1.4, 0.8),
      fas="Driver board sits in the bay under ZS-604; cover: 2 × M2 × 6 PT. Reed: hot glue in its slot (glass — no pressure). Pogo receptacle: pocket at x 29…34, glue.",
      act=["Build the driver board: Q1–Q3 AO3400A, R14–R16 100 Ω, R17–R19 100 kΩ, R23 12 kΩ / R24 20 kΩ, R9/R10 4.7 kΩ, R11/R12 100 Ω.", "Mount J2 pogo receptacle + D3 + C19/C20.", "Reed S1 in SERIES with the UV LED supply."],
      wire="Sheet E. Gates GPIO1 / GPIO2 / GPIO21; SHIELD_SENSE GPIO40; I2C1 GPIO10/11; INT GPIO41.", chk="Shield off: SHIELD_SENSE 0 V and UV_5V 0 V. Magnet held at the reed: SHIELD_SENSE ≈ 3.1 V."),
 dict(t="Light shield and sensor mount (AS7341)", ctx=PED, new=["ZS-602_light_shield", "ZS-603_sensor_mount", "PX_AS7341_breakout", "PX_pogo_pads_4p", "PX_magnet_6x2", "PX_uv_cut_filter_optional"], cam=(0.9, -1.4, 0.8),
      fas="AS7341 board: 2 × M2 × 5 to ZS-603; ZS-603 glued into the shield top. Magnet Ø6 × 2: glued into the flange pocket above the reed.",
      act=["Mount the AS7341 breakout in ZS-603, sensor facing down through the aperture.", "Insert the optional UV-cut filter for fluorescence mode only.", "Press the magnet into the shield flange above the reed position."],
      wire="Sheet E (pogo: VBUS, GND, SDA1_P, SCL1_P).", chk="Seat the shield: I2C scan on bus 1 shows 0x39 AND GPIO40 reads HIGH. Lift it: both go away."),
 dict(t="Mount the robot on the pedestal", ctx=HEAD + PODS + TORSO + LIMBS + PED, new=["ZS-108_neck_coupler", "ZS-502_support_tube_acrylic"], cam="iso_fit",
      fas="Robot slides onto the tube (slip fit, no screws). Optionally 1 drop of removable adhesive (ESTIMATE).",
      act=["Join the tube harness to the torso harness.", "Lower the robot onto the tube, front facing the station.", "Final dress of wires; nothing touching the station window."],
      wire="All sheets. Final continuity check per the harness table.", chk="Robot stands without wobble; total height 314 mm ±2 (DESIGN TARGET)."),
]
def render():
    from rlib import render_scene, callout_canvas, explode, np
    IMG = "/workspace/zeref-spark/docs/img"
    for i, s in enumerate(S, 1):
        items = list(dict.fromkeys(s["ctx"] + s["new"]))
        new = set(s["new"])
        off = (lambda n, new=new: explode(n) * 0.35 if n in new else np.zeros(3))
        cam = {"dir": s["cam"], "zoom": 1.05} if isinstance(s["cam"], tuple) else s["cam"]
        img, anc = render_scene(items, cam, 1300, 1000, offsets=off, highlight=new, ghost_others=True)
        labels = {n: (n.split("_")[0] if n.startswith("ZS") else "PX") + " " + M[n][0] for n in s["new"]}
        C = callout_canvas(img, anc, labels, margin=400, title=f"Step {i} — {s['t']}", sub="Highlighted = parts added in this step · grey = already installed / context", fs=19)
        C.save(f"{IMG}/step_{i:02d}.png"); print("step", i, flush=True)
if __name__ == "__main__":
    render()
