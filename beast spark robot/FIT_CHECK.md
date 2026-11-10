# ZEREF SPARK — Interference / fit check (v0.2)

**DESIGN TARGET — not printed or test-fitted.** Nominal-CAD check only: it proves the parts don't overlap in the
model. It does **not** prove they fit after printing (shrink, elephant foot, warp), or that the purchased modules match the proxy sizes.

Method: `cad/check.py` rebuilds all custom parts and purchased-part proxies in their assembled positions and runs a bounding-box
prefilter. Every remaining pair then gets an exact OCC boolean intersection; pairs that don't overlap get an exact minimum distance
(BRepExtrema). The alternates (ZS-605 dark plug, PTFE reference) sit in the cup *instead of* the crystal, so they are
checked against everything except the crystal.

- Shapes: 70 (36 custom parts + 32 purchased-part proxies + 2 cup alternates: ZS-605 dark plug, PTFE disc)  ·  pairs: 2412  ·  exact tests: 166
- Threshold: > 0.5 mm³ flagged
- **Interferences found: 0**
- Removal-path check: light shield lifted 5 mm (skirt clears the groove at 4.6 mm) → 4.16 mm to torso front shell, 5.85 mm to the legs. It can then slide forward.

History:
- v0.1 run 1: 5 hits (chest flange in torso front shell 22 mm³; leg flanges in torso shells 1.9 mm³ ×4). Fixed. Re-run: 0.
- v0.2 run 1: 0 hits, but the shield had only 3.4 mm under the torso, less than its 4.6 mm skirt, so it could not be lifted out. Shield and sensor stack lowered 6 mm. Re-run: 0 hits, removal path OK.

## Zero-gap contacts (intended mating faces, verify by print)
| Part A | Part B |
|---|---|
| ZS-101_head_shell_front | ZS-102_head_shell_back |
| ZS-101_head_shell_front | ZS-103_head_bulkhead |
| ZS-101_head_shell_front | ZS-104_visor |
| ZS-102_head_shell_back | ZS-103_head_bulkhead |
| ZS-103_head_bulkhead | ZS-105_face_carrier |
| ZS-103_head_bulkhead | ZS-109_battery_tray |
| ZS-105_face_carrier | PX_led_eyeL |
| ZS-105_face_carrier | PX_led_eyeR |
| ZS-106_eye_lightpipe_L | PX_led_eyeL |
| ZS-106_eye_lightpipe_R | PX_led_eyeR |
| ZS-201_ear_pod_L_mic | ZS-203_pod_rim_diffuser_L |
| ZS-202_ear_pod_R_light | ZS-203_pod_rim_diffuser_R |
| ZS-301_torso_shell_front | ZS-302_torso_shell_back |
| ZS-301_torso_shell_front | ZS-303_torso_bulkhead_esp32_cradle |
| ZS-301_torso_shell_front | ZS-502_support_tube_acrylic |
| ZS-302_torso_shell_back | ZS-303_torso_bulkhead_esp32_cradle |
| ZS-302_torso_shell_back | ZS-502_support_tube_acrylic |
| ZS-303_torso_bulkhead_esp32_cradle | ZS-304_sensor_sled |
| ZS-501_pedestal | ZS-601_station_led_plug |
| ZS-501_pedestal | ZS-602_light_shield |
| ZS-501_pedestal | ZS-604_driver_bay_cover |
| ZS-501_pedestal | ZS-502_support_tube_acrylic |
| ZS-501_pedestal | PX_crystal_window_borosilicate |
| ZS-501_pedestal | PX_pogo_pads_4p |
| ZS-501_pedestal | PX_magnet_6x2 |
| ZS-601_station_led_plug | PX_crystal_window_borosilicate |
| ZS-602_light_shield | PX_pogo_pads_4p |
| ZS-603_sensor_mount | PX_AS7341_breakout |
| ZS-603_sensor_mount | PX_uv_cut_filter_optional |
| PX_crystal_window_borosilicate | PX_crystal_sample |
| PX_station_led_board | PX_led_white |
| PX_station_led_board | PX_led_uv365 |
| PX_station_led_board | PX_led_ir940 |
| PX_AS7341_breakout | PX_uv_cut_filter_optional |
| PX_pogo_receptacle_4p | PX_pogo_pads_4p |
| ZS-605_dark_reference_plug | PX_crystal_window_borosilicate |
| PX_ptfe_white_reference_25x3 | PX_crystal_window_borosilicate |

## Tightest clearances (non-contact)
| Part A | Part B | min gap mm |
|---|---|---|
| ZS-103_head_bulkhead | PX_lipo_503450_protected | 0.100 |
| ZS-103_head_bulkhead | PX_powerboost_1000c | 0.100 |
| ZS-304_sensor_sled | PX_RB-002_icm42688_imu | 0.100 |
| ZS-304_sensor_sled | PX_RB-004_bme280 | 0.100 |
| ZS-305_chest_core_housing | PX_RB-005_max30102 | 0.100 |
| ZS-602_light_shield | PX_magnet_6x2 | 0.100 |
| ZS-101_head_shell_front | ZS-107_accent_lightpipe_L | 0.200 |
| ZS-101_head_shell_front | ZS-107_accent_lightpipe_R | 0.200 |
| ZS-201_ear_pod_L_mic | PX_RB-006_inmp441_podL | 0.200 |
| ZS-202_ear_pod_R_light | PX_RB-003_bh1750_podR | 0.200 |
| ZS-203_pod_rim_diffuser_L | ZS-204_pod_cap_L_mic | 0.200 |
| ZS-203_pod_rim_diffuser_R | ZS-205_pod_cap_R_light | 0.200 |
| ZS-301_torso_shell_front | ZS-305_chest_core_housing | 0.200 |
| ZS-305_chest_core_housing | ZS-306_chest_ring_diffuser | 0.200 |
| ZS-305_chest_core_housing | ZS-307_chest_center_lens | 0.200 |
| ZS-305_chest_core_housing | PX_led_ring12_chest | 0.200 |
| ZS-306_chest_ring_diffuser | PX_led_ring12_chest | 0.200 |
| ZS-501_pedestal | PX_pogo_receptacle_4p | 0.200 |
| ZS-501_pedestal | PX_reed_switch | 0.200 |
| ZS-601_station_led_plug | PX_station_led_board | 0.200 |
| ZS-602_light_shield | ZS-603_sensor_mount | 0.200 |
| ZS-602_light_shield | PX_pogo_receptacle_4p | 0.200 |
| ZS-101_head_shell_front | ZS-201_ear_pod_L_mic | 0.300 |
| ZS-101_head_shell_front | ZS-202_ear_pod_R_light | 0.300 |
| ZS-102_head_shell_back | ZS-201_ear_pod_L_mic | 0.300 |
| ZS-102_head_shell_back | ZS-202_ear_pod_R_light | 0.300 |
| ZS-102_head_shell_back | PX_speaker28 | 0.300 |
| ZS-109_battery_tray | PX_lipo_503450_protected | 0.300 |
| ZS-201_ear_pod_L_mic | ZS-206_ear_L | 0.300 |
| ZS-202_ear_pod_R_light | ZS-206_ear_R | 0.300 |
| ZS-203_pod_rim_diffuser_L | ZS-206_ear_L | 0.300 |
| ZS-203_pod_rim_diffuser_R | ZS-206_ear_R | 0.300 |
| PX_RB-006_inmp441_podL | PX_led_ring12_podL | 0.300 |
| PX_RB-003_bh1750_podR | PX_led_ring12_podR | 0.300 |
| ZS-605_dark_reference_plug | ZS-501_pedestal | 0.300 |
| PX_ptfe_white_reference_25x3 | ZS-501_pedestal | 0.300 |
| ZS-301_torso_shell_front | ZS-401_arm_L | 0.399 |
| ZS-301_torso_shell_front | ZS-401_arm_R | 0.399 |
| ZS-301_torso_shell_front | ZS-402_leg_L | 0.399 |
| ZS-301_torso_shell_front | ZS-402_leg_R | 0.399 |
| ZS-302_torso_shell_back | ZS-401_arm_L | 0.399 |
| ZS-302_torso_shell_back | ZS-401_arm_R | 0.399 |
| ZS-302_torso_shell_back | ZS-402_leg_L | 0.399 |
| ZS-302_torso_shell_back | ZS-402_leg_R | 0.399 |
| ZS-101_head_shell_front | ZS-108_neck_coupler | 0.400 |
| ZS-102_head_shell_back | ZS-108_neck_coupler | 0.400 |
| ZS-108_neck_coupler | ZS-301_torso_shell_front | 0.400 |
| ZS-108_neck_coupler | ZS-302_torso_shell_back | 0.400 |
| ZS-109_battery_tray | PX_max98357a_amp | 0.400 |
| ZS-303_torso_bulkhead_esp32_cradle | PX_RB-001_esp32s3_devkitc1 | 0.400 |

## Risks the CAD check cannot see
- 0.1–0.5 mm gaps (sensor proxies, light pipes, pod rims, battery tray, PowerBoost) will close up with real print tolerance. Sand to fit.
- Leg-flange and chest-flange margins to the torso inner wall are small (~0.6–0.7 mm).
- Purchased-board sizes are proxies (ESTIMATE): ESP32-S3 DevKit 69 × 26, PowerBoost ~36 × 23 × 5, AS7341 board ~25.6 × 17.8, 503450 cell 50 × 34 × 5–6.
- Light-tightness of the shield/groove and stray light in the cup can only be shown by the dark/stray-light test in ASSEMBLY.md §6.
- Support-tube stiffness, centre of mass and 11 + 4 conductor fit in the 8 mm tube are not analysed.
