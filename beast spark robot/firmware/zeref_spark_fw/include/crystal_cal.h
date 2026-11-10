// Crystal station calibration — AI-WRITTEN GLUE for the agreed formula T = (S - D) / (W - D)
//   S = sample counts, D = dark-plug counts, W = PTFE white-reference counts, same illumination,
//   same gain/integration. Result is a DERIVED relative transmission/reflectance per channel,
//   NOT an absolute or certified spectrophotometer value.
#pragma once
#include <cstdint>

namespace spark {

static constexpr int AS_CH = 10;  // F1..F8, Clear, NIR (flicker not used)
static constexpr int ILLUM = 4;   // 0 ambient/off, 1 white, 2 uv365, 3 ir940
static const char* const ILLUM_NAME[ILLUM] = {"off", "white", "uv365", "ir940"};
static const char* const CH_NAME[AS_CH] = {"F1_415", "F2_445", "F3_480", "F4_515", "F5_555",
                                           "F6_590", "F7_630", "F8_680", "CLEAR", "NIR_910"};

// Returns false (and writes NaN-free 0) when W-D is too small to divide by: that channel is "invalid", never guessed.
inline bool transmission(double s, double d, double w, double& t, double minSpan = 8.0) {
  double span = w - d;
  if (!(span >= minSpan)) { t = 0.0; return false; }
  t = (s - d) / span;
  return true;
}

// AS7341 defaults — decided by Robot X under Cory's delegation 2026-11-09 (DESIGN_DECISIONS.md D7).
// ESTIMATE pending a hardware check with the real LEDs, crystal cup and PTFE reference.
//   integration = (ATIME+1) * (ASTEP+1) * 2.78 us = 30 * 600 * 2.78 us ~= 50 ms; full scale = 30*600 = 18000 counts
//   gain per illumination mode: off 64x (dark/ambient leakage is tiny), white 16x (bright white LED through the cup:
//   keeps PTFE white below ~50% of full scale), uv365 64x (only visible light under UV reaches F1..F8), ir940 64x (NIR weak).
//   Dark, white and sample of the SAME mode always use the same gain, so T=(S-D)/(W-D) stays valid.
static constexpr uint8_t AS_ATIME = 29;
static constexpr uint16_t AS_ASTEP = 599;
static constexpr uint32_t AS_FULL_SCALE = (AS_ATIME + 1u) * (AS_ASTEP + 1u);   // 18000
static constexpr uint32_t AS_SAT_COUNTS = AS_FULL_SCALE * 9u / 10u;          // >= 90% of full scale = saturated
static constexpr uint16_t MODE_GAIN_X[ILLUM] = {64, 16, 64, 64};
inline bool saturated(uint32_t counts) { return counts >= AS_SAT_COUNTS; }

struct CrystalCal {
  uint16_t dark[ILLUM][AS_CH] = {};
  uint16_t white[ILLUM][AS_CH] = {};
  bool haveDark[ILLUM] = {}, haveWhite[ILLUM] = {};
  bool ready(int m) const { return haveDark[m] && haveWhite[m]; }
};

}  // namespace spark
