// UV 365 nm safety guard — AI-WRITTEN GLUE implementing the Spark safety rule from ../../wiring.md:
//   UV max 2 s ON, then at least 5 s OFF; only when the shield is seated (GPIO40 HIGH) AND the AS7341
//   answers on I2C1. The reed switch in series with the UV supply is the hardware interlock; this is
//   the second, software layer. Pure C++ (no Arduino) so host tests can drive it with a fake clock.
// Authority rule (Cory's Beast Box, beastbox/events.py:41-63 bounded_output): model text can never
// request a physical action. Only an owner command (UV / SCAN on the serial link) may ask for UV.
#pragma once
#include <cstdint>

namespace spark {

enum class UvDeny : uint8_t { OK = 0, NO_SHIELD, NO_SENSOR, COOLDOWN, TOO_LONG, LOW_BATTERY, ALREADY_ON };

class UvGuard {
 public:
  static constexpr uint32_t MAX_ON_MS = 2000;
  static constexpr uint32_t MIN_OFF_MS = 5000;

  // Ask to turn UV on for `ms` milliseconds at time `now`.
  UvDeny request(uint32_t now, uint32_t ms, bool shieldSeated, bool sensorAck, bool lowBattery) {
    if (on_) return UvDeny::ALREADY_ON;
    if (!shieldSeated) return UvDeny::NO_SHIELD;
    if (!sensorAck) return UvDeny::NO_SENSOR;
    if (lowBattery) return UvDeny::LOW_BATTERY;
    if (ms == 0 || ms > MAX_ON_MS) return UvDeny::TOO_LONG;
    if (everOn_ && (uint32_t)(now - offAt_) < MIN_OFF_MS) return UvDeny::COOLDOWN;
    on_ = true; everOn_ = true; onAt_ = now; budget_ = ms;
    return UvDeny::OK;
  }
  // Call every loop. Returns the pin level the UV gate must have right now.
  bool tick(uint32_t now, bool shieldSeated) {
    if (on_ && (!shieldSeated || (uint32_t)(now - onAt_) >= budget_)) off(now);
    return on_;
  }
  void off(uint32_t now) { if (on_) { on_ = false; offAt_ = now; } }
  bool isOn() const { return on_; }
  uint32_t cooldownLeft(uint32_t now) const {
    if (!everOn_ || on_) return 0;
    uint32_t el = now - offAt_;
    return el >= MIN_OFF_MS ? 0 : MIN_OFF_MS - el;
  }
  static const char* name(UvDeny d) {
    switch (d) {
      case UvDeny::OK: return "OK"; case UvDeny::NO_SHIELD: return "NO_SHIELD"; case UvDeny::NO_SENSOR: return "NO_SENSOR";
      case UvDeny::COOLDOWN: return "COOLDOWN"; case UvDeny::TOO_LONG: return "TOO_LONG"; case UvDeny::LOW_BATTERY: return "LOW_BATTERY";
      default: return "ALREADY_ON";
    }
  }

 private:
  bool on_ = false, everOn_ = false;
  uint32_t onAt_ = 0, offAt_ = 0, budget_ = 0;
};

}  // namespace spark
