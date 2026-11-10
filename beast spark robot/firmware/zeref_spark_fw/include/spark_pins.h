// ZEREF SPARK pin map — CONCEPT DESIGN / NOT BUILT HARDWARE.
// Label: AI-WRITTEN GLUE from the DECIDED pin table in ../../wiring.md (v0.4).
// All pins DECIDED by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D3).
// Pins 8/9, 12/13/14 and 17/18 are Cory's ORIGINAL Reality Bridge Probe v0.2 pins
// (ref/repo hardware/firmware/src/main.cpp:18-20 @13a4ee7) and are not moved.
#pragma once

// --- Cory's original probe pins (unchanged) ---
static constexpr int SDA_PIN = 8, SCL_PIN = 9;                 // I2C0: BH1750, BME280, ICM-42688-P, MAX30102
static constexpr int I2S_BCLK_PIN = 12, I2S_WS_PIN = 13, I2S_DATA_PIN = 14;  // INMP441 mic (I2S0 RX)
static constexpr int GNSS_RX_PIN = 17, GNSS_TX_PIN = 18;       // GNSS UART — UNWIRED BY DEFAULT

// --- Spark additions (DECIDED; LED data, speaker I2S1, amp mute were approved by Cory 2026-11-09) ---
static constexpr int LED_DATA_PIN = 4;                          // -> 74AHCT125 -> 48 x WS2812B
static constexpr int SPK_BCLK_PIN = 15, SPK_LRC_PIN = 16, SPK_DIN_PIN = 7;  // MAX98357A (I2S1 TX)
static constexpr int AMP_SD_PIN = 6;                            // MAX98357A SD: LOW = shutdown/mute

// --- Spark additions (DECIDED by Robot X under Cory's delegation 2026-11-09) ---
static constexpr int BAT_SENSE_PIN = 5;                         // ADC1_CH4, 100k/100k divider => VBAT = 2*Vadc
static constexpr int ST_SDA_PIN = 10, ST_SCL_PIN = 11;          // I2C1: crystal station AS7341 (0x39)
static constexpr int AS_INT_PIN = 41;                           // AS7341 INT (open drain, optional)
static constexpr int WHITE_LED_PIN = 1;                         // AO3400A Q1 gate
static constexpr int UV_LED_PIN = 2;                            // AO3400A Q2 gate; reed switch in series (hardware interlock)
static constexpr int IR_LED_PIN = 21;                           // AO3400A Q3 gate (moved from 42)
static constexpr int SHIELD_SENSE_PIN = 40;                     // HIGH = shield seated (12k/20k divider after reed)

// LED chain order (wiring.md: chest 12 -> eye L 5 -> eye R 5 -> pod L 12 -> pod R 12 -> crown 2)
static constexpr int LED_COUNT = 48;
static constexpr int LED_CHEST0 = 0,  LED_CHEST_N = 12;
static constexpr int LED_EYEL0 = 12,  LED_EYE_N = 5;
static constexpr int LED_EYER0 = 17;
static constexpr int LED_PODL0 = 22,  LED_POD_N = 12;
static constexpr int LED_PODR0 = 34;
static constexpr int LED_CROWN0 = 46, LED_CROWN_N = 2;

// Power headroom: boost limit ~1 A vs estimated peak (docs/electrical_spec.md) -> cap LEDs at 8% everywhere (D1).
static constexpr uint8_t LED_BRIGHTNESS_CAP = 20;      // 20/255 = 7.8 %
static constexpr uint8_t LED_BRIGHTNESS_LOWBAT = 10;   // ~4 % when VBAT < LOW_BAT_MV (DESIGN CHOICE)
static constexpr int LOW_BAT_MV = 3400;                // DESIGN CHOICE, not measured
// Battery sense: 100k/100k divider => VBAT = 2 * Vadc. BAT_CAL is 1.0 until one meter reading sets it
// (BAT_CAL = meter_mV / reported_mV). ESTIMATE pending hardware check (DESIGN_DECISIONS.md D7).
static constexpr float BAT_DIVIDER = 2.0f;
static constexpr float BAT_CAL = 1.0f;
