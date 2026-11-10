// Host-side harness for the firmware headers (AI-WRITTEN TEST GLUE).
// Usage: features_cli audio <rate> <float|double>  < samples.txt   (16384 samples)
//        features_cli light                         < values.txt
//        features_cli uv                            (runs the UV guard script, prints JSON lines)
//        features_cli speech [pop|nopop]            < speech lines; prints "S <status>" per line, "D <sample>" per played sample
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "../include/spark_features.h"
#include "../include/uv_guard.h"
#include "../include/crystal_cal.h"
#include "../include/speech_stream.h"
#include <string>
#include <iostream>

template <typename T> int audio(int rate) {
  std::vector<double> v; double x;
  while (scanf("%lf", &x) == 1) v.push_back(x);
  if ((int)v.size() != 16384) { fprintf(stderr, "need 16384 samples, got %zu\n", v.size()); return 2; }
  static spark::AudioWindow<T, 1024, 16> w(rate);
  T seg[1024];
  for (int f = 0; f < 16; f++) { for (int i = 0; i < 1024; i++) seg[i] = (T)v[f * 1024 + i]; w.pushFrame(seg); }
  spark::AudioFeatures o = w.finish();
  printf("{\"rms\":%.17g,\"phi_energy\":%.17g,\"phi_energy_alt\":%.17g,\"spectral_entropy\":%.17g,\"spectral_centroid\":%.17g,"
         "\"spectral_spread\":%.17g,\"dominant_frequency\":%.17g,\"onset_rate\":%.17g,\"zero_crossing\":%.17g,\"loudness_trend\":%.17g}\n",
         o.rms, o.phi_energy, o.phi_energy_alt, o.spectral_entropy, o.spectral_centroid, o.spectral_spread,
         o.dominant_frequency, o.onset_rate, o.zero_crossing, o.loudness_trend);
  return 0;
}

int light() {
  std::vector<double> v; double x;
  while (scanf("%lf", &x) == 1) v.push_back(x);
  spark::LightFeatures o;
  if (!spark::lightFeatures(v.data(), (int)v.size(), o)) { printf("null\n"); return 0; }
  printf("{\"mean\":%.17g,\"min\":%.17g,\"max\":%.17g,\"std\":%.17g,\"range\":%.17g,\"trend\":%.17g}\n", o.mean, o.min, o.max, o.std, o.range, o.trend);
  return 0;
}

int uv() {
  spark::UvGuard g;
  auto P = [&](const char* what, uint32_t t, spark::UvDeny r) { printf("{\"step\":\"%s\",\"t\":%u,\"result\":\"%s\",\"on\":%s}\n", what, t, spark::UvGuard::name(r), g.isOn() ? "true" : "false"); };
  P("no_shield", 0, g.request(0, 1000, false, true, false));
  P("no_sensor", 0, g.request(0, 1000, true, false, false));
  P("too_long", 0, g.request(0, 2001, true, true, false));
  P("low_batt", 0, g.request(0, 1000, true, true, true));
  P("ok_2000", 0, g.request(0, 2000, true, true, false));
  g.tick(1999, true); printf("{\"step\":\"tick1999\",\"on\":%s}\n", g.isOn() ? "true" : "false");
  g.tick(2000, true); printf("{\"step\":\"tick2000\",\"on\":%s}\n", g.isOn() ? "true" : "false");
  P("cooldown_6999", 6999, g.request(6999, 500, true, true, false));
  P("after_7000", 7000, g.request(7000, 500, true, true, false));
  g.tick(7100, false); printf("{\"step\":\"shield_lift_7100\",\"on\":%s}\n", g.isOn() ? "true" : "false");
  P("cooldown_after_lift", 9000, g.request(9000, 500, true, true, false));
  P("ok_12100", 12100, g.request(12100, 500, true, true, false));
  double t; bool ok = spark::transmission(600, 100, 1100, t); printf("{\"step\":\"T\",\"ok\":%s,\"T\":%.17g}\n", ok ? "true" : "false", t);
  ok = spark::transmission(600, 100, 104, t); printf("{\"step\":\"T_small_span\",\"ok\":%s,\"T\":%.17g}\n", ok ? "true" : "false", t);
  return 0;
}

int speechMode(bool pop) {
  static spark::SpeechRing<16384> ring;
  std::string ln; uint32_t now = 0;
  while (std::getline(std::cin, ln)) {
    now += 5;
    spark::SpeechStatus st = spark::handleSpeechLine(ln.c_str(), ring, now);
    printf("S %s\n", spark::speechStatusName(st));
    if (pop) {
      int16_t out[128];
      while (ring.count()) { size_t n = ring.pop(out, 128); for (size_t i = 0; i < n; i++) printf("D %d\n", out[i]); }
    }
  }
  printf("E received=%u played=%u buffered=%zu active=%d done=%d\n", ring.received(), ring.played(), ring.count(), ring.active() ? 1 : 0, ring.done() ? 1 : 0);
  printf("G %d %d %d\n", spark::applyGain(32767), spark::applyGain(-32768), spark::applyGain(1001));
  return 0;
}

int main(int argc, char** argv) {
  if (argc >= 2 && !strcmp(argv[1], "speech")) return speechMode(!(argc >= 3 && !strcmp(argv[2], "nopop")));
  if (argc >= 2 && !strcmp(argv[1], "audio")) {
    int rate = argc >= 3 ? atoi(argv[2]) : 16000;
    bool useFloat = argc >= 4 && !strcmp(argv[3], "float");
    return useFloat ? audio<float>(rate) : audio<double>(rate);
  }
  if (argc >= 2 && !strcmp(argv[1], "light")) return light();
  if (argc >= 2 && !strcmp(argv[1], "uv")) return uv();
  fprintf(stderr, "usage: features_cli audio|light|uv\n");
  return 1;
}
