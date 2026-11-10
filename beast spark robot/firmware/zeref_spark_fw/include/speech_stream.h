// Streamed speech audio for the MAX98357A (I2S1) — AI-WRITTEN GLUE.
// Decided by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D6).
// Pure C++ (no Arduino) so the host test harness can drive the exact same parser and ring buffer.
//
// Wire format (text lines, same link as every other command; USB CDC, or WebSocket text on the Wi-Fi build):
//   SAY_BEGIN <id> 16000 <total_samples>     open a stream: mono, signed 16-bit, 16 kHz, <= 30 s
//   PCM <id> <seq> <base64 s16le>            <= 256 samples per line, seq counts up from 0 with no gaps
//   SAY_END <id>                             play what is buffered, then mute
//   SAY_STOP                                 flush now, mute now
// Authority: these lines carry audio samples only. Nothing in a PCM payload is ever parsed as a command
// (base64 has no spaces or newlines), and the host only builds them from TTS output (host/spark_brain/speech.py).
#pragma once
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace spark {

enum class SpeechStatus : uint8_t { OK = 0, NOT_SPEECH, BAD_FORMAT, BAD_RATE, TOO_LONG, BAD_ID, BAD_SEQ, OVERFLOW, NOT_ACTIVE, BAD_B64 };
inline const char* speechStatusName(SpeechStatus s) {
  static const char* n[] = {"OK", "NOT_SPEECH", "BAD_FORMAT", "BAD_RATE", "TOO_LONG", "BAD_ID", "BAD_SEQ", "OVERFLOW", "NOT_ACTIVE", "BAD_B64"};
  return n[(int)s];
}

inline int b64val(char c) {
  if (c >= 'A' && c <= 'Z') return c - 'A';
  if (c >= 'a' && c <= 'z') return c - 'a' + 26;
  if (c >= '0' && c <= '9') return c - '0' + 52;
  if (c == '+') return 62;
  if (c == '/') return 63;
  return -1;
}
// Strict base64 (with '=' padding). Returns bytes written or -1.
inline int b64decode(const char* s, size_t n, uint8_t* out, size_t cap) {
  if (n % 4) return -1;
  size_t o = 0;
  for (size_t i = 0; i < n; i += 4) {
    int v[4];
    int pad = 0;
    for (int k = 0; k < 4; k++) {
      char c = s[i + k];
      if (c == '=' && i + 4 == n && k >= 2) { v[k] = 0; pad++; continue; }
      if (pad) return -1;
      v[k] = b64val(c);
      if (v[k] < 0) return -1;
    }
    uint32_t t = (v[0] << 18) | (v[1] << 12) | (v[2] << 6) | v[3];
    uint8_t b[3] = {(uint8_t)(t >> 16), (uint8_t)(t >> 8), (uint8_t)t};
    for (int k = 0; k < 3 - pad; k++) { if (o >= cap) return -1; out[o++] = b[k]; }
  }
  return (int)o;
}

template <size_t N>  // ring capacity in samples
class SpeechRing {
 public:
  static constexpr uint32_t RATE = 16000;
  static constexpr uint32_t MAX_SAMPLES = 30u * 16000u;   // 30 s per utterance (DESIGN CHOICE)
  static constexpr uint32_t CHUNK_MAX = 256;
  static constexpr uint32_t RX_TIMEOUT_MS = 2000;         // no data for 2 s mid-stream -> abort + mute

  bool active() const { return active_; }
  bool ending() const { return ending_; }
  uint32_t id() const { return id_; }
  size_t count() const { return count_; }
  size_t freeSpace() const { return N - count_; }
  uint32_t received() const { return received_; }
  uint32_t played() const { return played_; }
  uint32_t underruns() const { return underruns_; }
  bool done() const { return active_ && ending_ && count_ == 0; }

  SpeechStatus begin(uint32_t id, uint32_t rate, uint32_t total, uint32_t now) {
    if (rate != RATE) return SpeechStatus::BAD_RATE;
    if (total == 0 || total > MAX_SAMPLES) return SpeechStatus::TOO_LONG;
    reset();
    active_ = true; id_ = id; total_ = total; lastRx_ = now;
    return SpeechStatus::OK;
  }
  SpeechStatus push(uint32_t id, uint32_t seq, const int16_t* s, size_t k, uint32_t now) {
    if (!active_ || ending_) return SpeechStatus::NOT_ACTIVE;
    if (id != id_) return SpeechStatus::BAD_ID;
    if (seq != nextSeq_) return SpeechStatus::BAD_SEQ;
    if (k == 0 || k > CHUNK_MAX || received_ + k > total_) return SpeechStatus::TOO_LONG;
    if (k > freeSpace()) return SpeechStatus::OVERFLOW;   // host broke flow control; chunk dropped, stream continues
    for (size_t i = 0; i < k; i++) { buf_[head_] = s[i]; head_ = (head_ + 1) % N; }
    count_ += k; received_ += (uint32_t)k; nextSeq_++; lastRx_ = now;
    return SpeechStatus::OK;
  }
  SpeechStatus end(uint32_t id) {
    if (!active_) return SpeechStatus::NOT_ACTIVE;
    if (id != id_) return SpeechStatus::BAD_ID;
    ending_ = true;
    return SpeechStatus::OK;
  }
  void stop() { reset(); }
  // Pull up to k samples for the DAC. Returns how many real samples were copied; pads the rest with silence.
  size_t pop(int16_t* out, size_t k) {
    size_t n = k < count_ ? k : count_;
    for (size_t i = 0; i < n; i++) { out[i] = buf_[tail_]; tail_ = (tail_ + 1) % N; }
    for (size_t i = n; i < k; i++) out[i] = 0;
    count_ -= n; played_ += (uint32_t)n;
    if (active_ && !ending_ && n < k && received_ < total_) underruns_++;
    return n;
  }
  // true if the stream was aborted for lack of data
  bool watchdog(uint32_t now) {
    if (active_ && !ending_ && now - lastRx_ > RX_TIMEOUT_MS) { reset(); return true; }
    return false;
  }

 private:
  void reset() {
    head_ = tail_ = count_ = 0; active_ = ending_ = false; id_ = 0; nextSeq_ = 0;
    total_ = received_ = played_ = underruns_ = 0;
  }
  int16_t buf_[N];
  size_t head_ = 0, tail_ = 0, count_ = 0;
  bool active_ = false, ending_ = false;
  uint32_t id_ = 0, nextSeq_ = 0, total_ = 0, received_ = 0, played_ = 0, underruns_ = 0, lastRx_ = 0;
};

inline bool parseU32(const char*& p, uint32_t& v) {
  while (*p == ' ') p++;
  if (*p < '0' || *p > '9') return false;
  char* e = nullptr;
  unsigned long x = strtoul(p, &e, 10);
  if (e == p || (*e != ' ' && *e != 0) || x > 0xFFFFFFFFul) return false;
  v = (uint32_t)x; p = e;
  return true;
}

// Parse one speech line and apply it to the ring. NOT_SPEECH means "not a speech line" (hand it to the normal
// command parser). `line` is the raw line (case preserved; base64 is case-sensitive).
template <size_t N>
SpeechStatus handleSpeechLine(const char* line, SpeechRing<N>& ring, uint32_t now) {
  if (!strncmp(line, "PCM ", 4)) {
    const char* p = line + 4;
    uint32_t id, seq;
    if (!parseU32(p, id) || !parseU32(p, seq)) return SpeechStatus::BAD_FORMAT;
    while (*p == ' ') p++;
    size_t n = strlen(p);
    while (n && (p[n - 1] == '\r' || p[n - 1] == ' ')) n--;
    uint8_t bytes[2 * 256 + 3];
    int got = b64decode(p, n, bytes, sizeof(bytes));
    if (got < 0 || got % 2) return SpeechStatus::BAD_B64;
    int16_t s[256];
    size_t k = (size_t)got / 2;
    for (size_t i = 0; i < k; i++) s[i] = (int16_t)(bytes[2 * i] | (bytes[2 * i + 1] << 8));  // little-endian
    return ring.push(id, seq, s, k, now);
  }
  if (!strncmp(line, "SAY_BEGIN ", 10)) {
    const char* p = line + 10;
    uint32_t id, rate, total;
    if (!parseU32(p, id) || !parseU32(p, rate) || !parseU32(p, total)) return SpeechStatus::BAD_FORMAT;
    return ring.begin(id, rate, total, now);
  }
  if (!strncmp(line, "SAY_END ", 8)) {
    const char* p = line + 8;
    uint32_t id;
    if (!parseU32(p, id)) return SpeechStatus::BAD_FORMAT;
    return ring.end(id);
  }
  if (!strcmp(line, "SAY_STOP")) { ring.stop(); return SpeechStatus::OK; }
  return SpeechStatus::NOT_SPEECH;
}

// Speech output gain: Q15. 0.5 = -6 dBFS headroom on the 3 W amp, battery-friendly (DESIGN CHOICE, ESTIMATE).
static constexpr int32_t SPEECH_GAIN_Q15 = 16384;
inline int16_t applyGain(int16_t s) {
  int32_t v = ((int32_t)s * SPEECH_GAIN_Q15) >> 15;
  return (int16_t)(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
}

}  // namespace spark
