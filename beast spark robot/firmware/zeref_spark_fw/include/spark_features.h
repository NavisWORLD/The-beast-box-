// Spark on-device feature extraction.
// Label: PORT of CORY ORIGINAL math. Line-for-line C++ port of
//   NavisWORLD/The-beast-box- beastbox/private_features.py  (commit 478314665120...)
//   audio_features()  lines 72-119   and   light_features()  lines 163-173,  unit() line 34.
// Only the numeric features named in beastbox/routing.json leave the device; raw audio never does.
// Pure C++ (no Arduino) so the SAME header is compiled on the host by test_native/ and checked against
// Cory's Python with tests (host/tests/test_firmware_parity.py).
// Streaming form: Cory's function takes n samples, frame 1024, hop=max(1024,(n-1024)//15), <=16 frames.
// With n = 16*1024 = 16384 that is exactly 16 back-to-back frames (hop 1024), so feeding 16 frames
// one at a time gives the same numbers without holding 16384 samples in RAM.
#pragma once
#include <cmath>
#include <cstddef>

namespace spark {

template <typename T> inline T clamp1(T x, T lo = T(-1), T hi = T(1)) { return x < lo ? lo : (x > hi ? hi : x); }
// private_features.py:34  unit(x, lo, hi) = clamp(2*clamp((x-lo)/(hi-lo),0,1)-1)
template <typename T> inline T unit(T x, T lo, T hi) { return clamp1<T>(T(2) * clamp1<T>((x - lo) / (hi - lo), T(0), T(1)) - T(1)); }

// private_features.py:44-69 (in-place radix-2 FFT, same loop structure)
template <typename T> void fft(T* re, T* im, int n) {
  int j = 0;
  for (int i = 1; i < n; i++) {
    int bit = n >> 1;
    while (j & bit) { j ^= bit; bit >>= 1; }
    j ^= bit;
    if (i < j) { T t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (int size = 2; size <= n; size <<= 1) {
    double ang = -2.0 * M_PI / size;
    T wr = (T)std::cos(ang), wi = (T)std::sin(ang);
    int half = size / 2;
    for (int start = 0; start < n; start += size) {
      T cr = 1, ci = 0;
      for (int k = 0; k < half; k++) {
        int a = start + k, b = start + k + half;
        T tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti;
        re[a] = re[a] + tr; im[a] = im[a] + ti;
        T ncr = cr * wr - ci * wi, nci = cr * wi + ci * wr; cr = ncr; ci = nci;
      }
    }
  }
}

struct AudioFeatures {  // names = routing.json audio source features
  double rms, phi_energy, phi_energy_alt, spectral_entropy, spectral_centroid, spectral_spread,
         dominant_frequency, onset_rate, zero_crossing, loudness_trend;
};

template <typename T, int FRAME = 1024, int FRAMES = 16>
class AudioWindow {
 public:
  explicit AudioWindow(int rate) : rate_(rate) {
    for (int i = 0; i < FRAME; i++) window_[i] = (T)(0.5 - 0.5 * std::cos(2.0 * M_PI * i / (FRAME - 1)));
    reset();
  }
  void reset() {
    count_ = 0; sumsq_ = 0; zc_ = 0; havePrev_ = false; prev_ = 0;
    for (int k = 0; k < FRAME / 2; k++) power_[k] = 0;
  }
  bool full() const { return count_ >= FRAMES; }
  int frames() const { return count_; }
  static constexpr int samplesNeeded() { return FRAME * FRAMES; }
  // seg: FRAME samples, floats in [-1, 1]
  void pushFrame(const T* seg) {
    if (full()) return;
    double fs = 0;
    for (int i = 0; i < FRAME; i++) {
      T s = seg[i];
      sumsq_ += (double)s * s;
      fs += (double)s * s;
      if (havePrev_ && ((prev_ < 0 && 0 <= s) || (prev_ >= 0 && 0 > s))) zc_++;
      prev_ = s; havePrev_ = true;
      re_[i] = seg[i] * window_[i]; im_[i] = 0;
    }
    framesRms_[count_] = std::sqrt(fs / FRAME);
    fft<T>(re_, im_, FRAME);
    for (int k = 0; k < FRAME / 2; k++) power_[k] += (double)re_[k] * re_[k] + (double)im_[k] * im_[k];
    count_++;
  }
  AudioFeatures finish() const {
    const double PHI = (1.0 + std::sqrt(5.0)) / 2.0;
    const int n = count_ * FRAME;
    double rms = std::sqrt(sumsq_ / n);
    double e = rms / 0.5; if (e > 1.0) e = 1.0;
    double energy = e * e;
    double zc = (double)zc_ / (n - 1);
    double total = 0; for (int k = 0; k < FRAME / 2; k++) total += power_[k];
    if (total == 0) total = 1e-12;
    double nyq = rate_ / 2.0, centroid = 0, ent = 0; int dom = 0;
    for (int k = 0; k < FRAME / 2; k++) {
      double p = power_[k] / total, f = (k + 0.5) * nyq / (FRAME / 2);
      centroid += f * p;
      if (p > 0) ent -= p * std::log2(p);
      if (power_[k] > power_[dom]) dom = k;   // first maximum, like Python max()
    }
    double spread2 = 0;
    for (int k = 0; k < FRAME / 2; k++) { double p = power_[k] / total, f = (k + 0.5) * nyq / (FRAME / 2); spread2 += p * (f - centroid) * (f - centroid); }
    double spread = std::sqrt(spread2), entropy = ent / std::log2((double)(FRAME / 2));
    double dominant = (dom + 0.5) * nyq / (FRAME / 2);
    // onsets (private_features.py:107-110)
    int nf = count_; double flux[FRAMES]; int nflux = nf > 1 ? nf - 1 : 0; double fsum = 0, rsum = 0;
    for (int i = 0; i < nf; i++) rsum += framesRms_[i];
    for (int i = 0; i < nflux; i++) { double d = framesRms_[i + 1] - framesRms_[i]; flux[i] = d > 0 ? d : 0; fsum += flux[i]; }
    double floor_ = 0.05 * (nf ? rsum / nf : 0.0);
    double thresh = (nflux ? fsum / nflux : 0.0) * 1.5; if (thresh < floor_) thresh = floor_;
    int onsets = 0;
    for (int i = 0; i < nflux; i++) if (flux[i] > thresh && (i == 0 || flux[i - 1] <= flux[i])) onsets++;
    double seconds = (double)n / rate_;
    int half = nf / 2; if (half < 1) half = 1;
    double early = 0, late = 0; for (int i = 0; i < half && i < nf; i++) early += framesRms_[i]; early /= half;
    for (int i = half; i < nf; i++) late += framesRms_[i]; late /= (nf - half > 1 ? nf - half : 1);
    double denom = late + early; if (denom < 1e-9) denom = 1e-9;
    double trend = (late - early) / denom;
    AudioFeatures o;
    o.rms = unit<double>(std::sqrt(energy), 0, 1);
    o.phi_energy = unit<double>(PHI * energy, 0, PHI);
    o.phi_energy_alt = unit<double>(PHI * energy, 0, PHI);
    o.spectral_entropy = unit<double>(entropy, 0, 1);
    o.spectral_centroid = unit<double>(centroid, 0, nyq);
    o.spectral_spread = unit<double>(spread, 0, nyq / 2);
    o.dominant_frequency = unit<double>(dominant, 0, nyq);
    o.onset_rate = unit<double>(onsets / (seconds > 1e-9 ? seconds : 1e-9), 0, 10);
    o.zero_crossing = unit<double>(zc, 0, 0.5);
    o.loudness_trend = clamp1<double>(trend);
    return o;
  }
  double lastFrameRms() const { return count_ ? framesRms_[count_ - 1] : 0.0; }

 private:
  int rate_, count_;
  double sumsq_; long zc_; bool havePrev_; T prev_;
  T window_[FRAME], re_[FRAME], im_[FRAME];
  double power_[FRAME / 2];
  double framesRms_[FRAMES];
};

struct LightFeatures { double mean, min, max, std, range, trend; };

// private_features.py:163-173. values in [0,1], 3 <= n.
inline bool lightFeatures(const double* v, int n, LightFeatures& o) {
  if (n < 3) return false;
  double mean = 0, mn = v[0], mx = v[0];
  for (int i = 0; i < n; i++) { if (v[i] < 0 || v[i] > 1) return false; mean += v[i]; if (v[i] < mn) mn = v[i]; if (v[i] > mx) mx = v[i]; }
  mean /= n;
  double var = 0; for (int i = 0; i < n; i++) var += (v[i] - mean) * (v[i] - mean);
  double sd = std::sqrt(var / n);
  int third = n / 3; if (third < 1) third = 1;
  double a = 0, b = 0; for (int i = 0; i < third; i++) { a += v[i]; b += v[n - third + i]; }
  double trend = b / third - a / third;
  o.mean = unit<double>(mean, 0, 1); o.min = unit<double>(mn, 0, 1); o.max = unit<double>(mx, 0, 1);
  o.std = unit<double>(sd, 0, 0.5); o.range = unit<double>(mx - mn, 0, 1); o.trend = clamp1<double>(trend * 2.0);
  return true;
}

// Lux -> brightness in [0,1] for the light band.  DECIDED default (D7, Robot X under Cory's delegation 2026-11-09),
// ESTIMATE pending hardware check. DESIGN CHOICE (AI-written, not from Cory's code):
// log scale over the BH1750 range 0..65535 lx, so a dim room and daylight both move the band.
inline double luxToBrightness(double lux) {
  if (!(lux > 0)) return 0.0;
  double b = std::log10(1.0 + lux) / std::log10(1.0 + 65535.0);
  return b < 0 ? 0 : (b > 1 ? 1 : b);
}

}  // namespace spark
