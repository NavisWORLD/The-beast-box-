// =====================================================================================
// ZEREF SPARK firmware 0.3.0 — the Spark BODY for Cory's Beast Box BRAIN.
// CONCEPT DESIGN / NOT BUILT HARDWARE. Compiling is not the same as working on a board.
//
// Base: Cory's ORIGINAL Reality Bridge Probe v0.2 reference firmware
//   NavisWORLD/Reality-bridge-universal-probe-engine-sim- @13a4ee7 hardware/firmware/src/main.cpp
//   (byte-identical copy kept in ../reality_bridge_probe_v0.2_original for diffing).
// Kept from Cory: pins 8/9, 12/13/14, 17/18; 16 kHz INMP441 I2S0 RX setup; per-block mean removal and
//   >>8 / 8388608 sample scaling; CAL_AUDIO noise-floor rule (mean x1.25, clamp 0.0001..0.08); sensor
//   probing order and MAX30102 setup(60,4,2,100,411,4096); 100 ms probe packet with his field names;
//   SELFTEST / STATUS / CAL_AUDIO / HELP commands.
// Ported from Cory's Beast Box (CORY ORIGINAL math, C++ port in include/spark_features.h):
//   audio + light band features exactly as beastbox/private_features.py, so the Beast Box router
//   (beastbox/routing.py) can take them as kind=measured, feature_extraction=on-device, raw_retained=false.
// AI-WRITTEN GLUE: everything else (LED/amp/speaker/battery/crystal station/UV guard/link framing).
// =====================================================================================
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <BH1750.h>
#include <Adafruit_BME280.h>
#include <ICM42688.h>
#include <MAX30105.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_AS7341.h>
#include <Preferences.h>
#include <WiFi.h>  // radio stays off unless SPARK_WIFI_AP=1
#include "driver/i2s.h"
#if SPARK_GNSS_WIRED
#include <TinyGPS++.h>
#endif
#if SPARK_WIFI_AP
#include <WebSocketsServer.h>
#endif

#include "spark_pins.h"
#include "spark_features.h"
#include "uv_guard.h"
#include "crystal_cal.h"
#include "speech_stream.h"

#ifndef SPARK_GNSS_WIRED
#define SPARK_GNSS_WIRED 0
#endif
#ifndef SPARK_WIFI_AP
#define SPARK_WIFI_AP 0
#endif
#ifndef SPARK_UV_ENABLED
#define SPARK_UV_ENABLED 1   // child build: -DSPARK_UV_ENABLED=0 (UV LED never driven; D12)
#endif
#ifndef SPARK_AP_PASS
#define SPARK_AP_PASS ""   // set SPARK_AP_PASS in the environment at build time (>= 8 chars); empty = AP stays off
#endif

static const char* FW = "zs-0.4.0";
static const char* PROBE_BASE = "0.2.0";
static const char* SCHEMA = "zeref-spark-v1";
static constexpr uint32_t PACKET_MS = 100;        // Cory's original probe packet period
static constexpr int AUDIO_RATE = 16000;          // Cory's original mic rate
static constexpr int FRAME = 1024;                // beastbox/private_features.py frame
static constexpr uint32_t BODY_MS = 1000;
static constexpr uint32_t HOST_TIMEOUT_MS = 5000; // no host command for 5 s -> idle "no brain" glow
static constexpr int LIGHT_WINDOW = 10;           // 10 x 100 ms BH1750 samples -> 1 light feature frame / s
static constexpr int PPG_BATCH = 25;              // MAX30102: 100 sps / avg 4 = 25 sps -> 1 batch / s

BH1750 luxSensor;
Adafruit_BME280 bme;
ICM42688* imu = nullptr;
MAX30105 ppg;
Adafruit_NeoPixel strip(LED_COUNT, LED_DATA_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_AS7341 as7341;
Preferences prefs;
spark::UvGuard uv;
spark::CrystalCal cal;
#if SPARK_GNSS_WIRED
TinyGPSPlus gps;
HardwareSerial GNSS(1);
#endif
#if SPARK_WIFI_AP
WebSocketsServer ws(81);
void handleLine(const String& raw, bool fromWs);
void onWs(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_TEXT && len <= 800) handleLine(String((const char*)payload, len), true);
}
const char* AP_SSID = "ZerefSpark";
const char* AP_PASS = SPARK_AP_PASS;  // no password is compiled in by default; AP refuses to start if < 8 chars
bool apUp = false;
#endif

bool hasLux = false, hasBme = false, hasImu = false, hasPpg = false, hasMic = false, hasSpk = false, hasAs = false;
uint32_t lastPacket = 0, lastBody = 0, lastHostMs = 0, lastShow = 0, seq = 0;
bool ledsDirty = true, hostSeen = false, ampForcedMute = true, lowBattery = false, batteryPresent = false;
uint8_t ledCap = LED_BRIGHTNESS_CAP;
int vbatMv = 0;

// ---------------- audio (task on core 0) ----------------
static spark::AudioWindow<float, FRAME, 16> audioWin(AUDIO_RATE);
portMUX_TYPE audioMux = portMUX_INITIALIZER_UNLOCKED;
volatile bool audioReady = false;
spark::AudioFeatures audioOut;
volatile float legacyAudioRms = 0.0f;
float audioNoiseFloor = 0.0025f;
volatile bool calAudio = false; volatile bool calAudioDone = false;
volatile double calSum = 0; volatile uint32_t calN = 0; uint32_t calStart = 0;

bool initMicrophone() {  // Cory's original initMicrophone(), dma_buf_count raised 4 -> 8 for the streaming task
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = AUDIO_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = 256;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = false;
  cfg.fixed_mclk = 0;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = I2S_BCLK_PIN;
  pins.ws_io_num = I2S_WS_PIN;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = I2S_DATA_PIN;
  if (i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr) != ESP_OK) return false;
  if (i2s_set_pin(I2S_NUM_0, &pins) != ESP_OK) { i2s_driver_uninstall(I2S_NUM_0); return false; }
  i2s_zero_dma_buffer(I2S_NUM_0);
  return true;
}

void audioTask(void*) {
  static int32_t raw[FRAME];
  static float seg[FRAME];
  for (;;) {
    size_t total = 0;
    while (total < sizeof(raw)) {
      size_t br = 0;
      if (i2s_read(I2S_NUM_0, ((uint8_t*)raw) + total, sizeof(raw) - total, &br, portMAX_DELAY) != ESP_OK) break;
      total += br;
    }
    if (total < sizeof(raw)) continue;
    double mean = 0.0;  // Cory: mean of (sample>>8), subtracted (main.cpp:70-73)
    for (int i = 0; i < FRAME; i++) mean += (double)(raw[i] >> 8);
    mean /= FRAME;
    double e = 0.0;
    for (int i = 0; i < FRAME; i++) {
      float v = (float)(((double)(raw[i] >> 8) - mean) / 8388608.0);
      seg[i] = v < -1.f ? -1.f : (v > 1.f ? 1.f : v);
      e += (double)seg[i] * seg[i];
    }
    float rms = (float)sqrt(e / FRAME);
    if (calAudio) { calSum = calSum + rms; calN = calN + 1; if (millis() - calStart >= 1800) { calAudio = false; calAudioDone = true; } }
    legacyAudioRms = constrain(rms - audioNoiseFloor, 0.0f, 1.0f);
    audioWin.pushFrame(seg);
    if (audioWin.full()) {
      spark::AudioFeatures f = audioWin.finish();
      portENTER_CRITICAL(&audioMux); audioOut = f; audioReady = true; portEXIT_CRITICAL(&audioMux);
      audioWin.reset();
    }
  }
}

// ---------------- speaker (MAX98357A on I2S1) ----------------
struct SpkTone { float f0 = 0, f1 = 0, phase = 0; uint32_t total = 0, left = 0; } spk;
uint32_t muteAt = 0;
static spark::SpeechRing<16384> speech;   // ~1.02 s of 16 kHz mono buffer (32 KB)
uint32_t lastSpeechReport = 0;
static int16_t spkBuf[2 * 128]; size_t spkPendOff = 0, spkPendLen = 0;  // bytes not yet accepted by I2S

bool initSpeaker() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = AUDIO_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 6;
  cfg.dma_buf_len = 256;
  cfg.tx_desc_auto_clear = true;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = SPK_BCLK_PIN;
  pins.ws_io_num = SPK_LRC_PIN;
  pins.data_out_num = SPK_DIN_PIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;
  if (i2s_driver_install(I2S_NUM_1, &cfg, 0, nullptr) != ESP_OK) return false;
  if (i2s_set_pin(I2S_NUM_1, &pins) != ESP_OK) { i2s_driver_uninstall(I2S_NUM_1); return false; }
  i2s_zero_dma_buffer(I2S_NUM_1);
  return true;
}
void setAmp(bool on) { digitalWrite(AMP_SD_PIN, (on && !ampForcedMute) ? HIGH : LOW); }
void startTone(float f0, float f1, uint32_t ms) {
  if (!hasSpk || speech.active()) return;  // speech has priority over tones
  ms = min<uint32_t>(ms, 3000);
  spk.f0 = constrain(f0, 60.0f, 6000.0f); spk.f1 = constrain(f1, 60.0f, 6000.0f);
  spk.total = spk.left = (uint32_t)((uint64_t)AUDIO_RATE * ms / 1000); spk.phase = 0;
  setAmp(true);
}
void emit(JsonDocument& d, bool wifiOk = true);
void emitSpeech(const char* state) {
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "speech"; d["state"] = state; d["id"] = speech.id();
  d["free"] = speech.freeSpace(); d["buffered"] = speech.count(); d["received"] = speech.received();
  d["played"] = speech.played(); d["underruns"] = speech.underruns(); d["amp_muted"] = ampForcedMute;
  emit(d);
}
// One I2S writer for tones and speech. Bytes I2S didn't take are kept and retried, never dropped.
void pumpSpeaker(uint32_t now) {
  if (!hasSpk) return;
  if (spkPendLen) {
    size_t wr = 0;
    i2s_write(I2S_NUM_1, ((uint8_t*)spkBuf) + spkPendOff, spkPendLen, &wr, 0);
    spkPendOff += wr; spkPendLen -= wr;
    if (spkPendLen) return;
  }
  if (speech.watchdog(now)) { emitSpeech("aborted_no_data"); muteAt = now + 60; return; }
  if (speech.active()) {
    if (speech.done()) { speech.stop(); emitSpeech("done"); muteAt = now + 60; return; }
    int16_t mono[128];
    size_t got = speech.pop(mono, 128);
    if (!got && !speech.ending()) { /* waiting for data: write silence so the DAC doesn't click */ }
    for (int i = 0; i < 128; i++) { int16_t v = spark::applyGain(mono[i]); spkBuf[2 * i] = v; spkBuf[2 * i + 1] = v; }
    spkPendOff = 0; spkPendLen = sizeof(spkBuf);
    if (now - lastSpeechReport >= 100) { lastSpeechReport = now; emitSpeech("streaming"); }  // flow-control credits
    return;
  }
  if (spk.left == 0) { if (muteAt && now >= muteAt) { setAmp(false); muteAt = 0; } return; }
  uint32_t n = min<uint32_t>(128, spk.left);
  for (uint32_t i = 0; i < n; i++) {
    float prog = 1.0f - (float)(spk.left - i) / (float)spk.total;
    float f = spk.f0 + (spk.f1 - spk.f0) * prog;
    float env = min(1.0f, min(prog * 20.0f, (1.0f - prog) * 20.0f));     // 5% fade in/out, no clicks
    int16_t v = (int16_t)(0.25f * env * 32767.0f * sinf(spk.phase));    // 25% amplitude: DESIGN CHOICE (battery)
    spk.phase += 2.0f * PI * f / AUDIO_RATE; if (spk.phase > 2 * PI) spk.phase -= 2 * PI;
    spkBuf[2 * i] = v; spkBuf[2 * i + 1] = v;
  }
  spk.left -= n;
  spkPendOff = 0; spkPendLen = n * 4;
  if (spk.left == 0) muteAt = now + 60;
}

// ---------------- LEDs ----------------
void fillRange(int first, int n, uint8_t r, uint8_t g, uint8_t b) {
  for (int i = first; i < first + n && i < LED_COUNT; i++) strip.setPixelColor(i, r, g, b);
  ledsDirty = true;
}
bool setRegion(const String& region, uint8_t r, uint8_t g, uint8_t b) {
  if (region == "ALL") fillRange(0, LED_COUNT, r, g, b);
  else if (region == "CHEST") fillRange(LED_CHEST0, LED_CHEST_N, r, g, b);
  else if (region == "EYES") { fillRange(LED_EYEL0, LED_EYE_N, r, g, b); fillRange(LED_EYER0, LED_EYE_N, r, g, b); }
  else if (region == "EYEL") fillRange(LED_EYEL0, LED_EYE_N, r, g, b);
  else if (region == "EYER") fillRange(LED_EYER0, LED_EYE_N, r, g, b);
  else if (region == "PODS") { fillRange(LED_PODL0, LED_POD_N, r, g, b); fillRange(LED_PODR0, LED_POD_N, r, g, b); }
  else if (region == "CROWN") fillRange(LED_CROWN0, LED_CROWN_N, r, g, b);
  else return false;
  return true;
}
void applyBrightness() {
  uint8_t cap = lowBattery ? min(ledCap, LED_BRIGHTNESS_LOWBAT) : ledCap;
  strip.setBrightness(min(cap, LED_BRIGHTNESS_CAP));  // never above the 8% cap
  ledsDirty = true;
}
void idleGlow(uint32_t now) {  // "no brain connected": slow dim breathing on the chest (DESIGN CHOICE)
  float k = 0.5f + 0.5f * sinf(now / 900.0f);
  uint8_t v = (uint8_t)(40 + 120 * k);
  fillRange(0, LED_COUNT, 0, 0, 0);
  fillRange(LED_CHEST0, LED_CHEST_N, 0, v / 3, v);
}

// ---------------- crystal station ----------------
bool shieldRaw() { return digitalRead(SHIELD_SENSE_PIN) == HIGH; }
bool shieldSeated = false; uint32_t shieldChangedAt = 0; bool shieldLast = false;
void pollShield(uint32_t now) {
  bool s = shieldRaw();
  if (s != shieldLast) { shieldLast = s; shieldChangedAt = now; }
  bool next = (now - shieldChangedAt >= 50) ? s : shieldSeated;  // 50 ms debounce, but un-seat acts at once below
  if (!s) next = false;
  shieldSeated = next;
}
bool stationAck() { Wire1.beginTransmission(0x39); return Wire1.endTransmission() == 0; }
void stationLedsOff() { digitalWrite(WHITE_LED_PIN, LOW); digitalWrite(IR_LED_PIN, LOW); uv.off(millis()); digitalWrite(UV_LED_PIN, LOW); }
bool readAs(uint16_t out[spark::AS_CH]) {
  uint16_t b[12];
  if (!as7341.readAllChannels(b)) return false;
  out[0] = b[AS7341_CHANNEL_415nm_F1]; out[1] = b[AS7341_CHANNEL_445nm_F2]; out[2] = b[AS7341_CHANNEL_480nm_F3];
  out[3] = b[AS7341_CHANNEL_515nm_F4]; out[4] = b[AS7341_CHANNEL_555nm_F5]; out[5] = b[AS7341_CHANNEL_590nm_F6];
  out[6] = b[AS7341_CHANNEL_630nm_F7]; out[7] = b[AS7341_CHANNEL_680nm_F8]; out[8] = b[AS7341_CHANNEL_CLEAR];
  out[9] = b[AS7341_CHANNEL_NIR];
  return true;
}
void serviceDuringScan();

void emit(JsonDocument& d, bool wifiOk) {
  String out; serializeJson(d, out); Serial.println(out);
#if SPARK_WIFI_AP
  if (wifiOk) ws.broadcastTXT(out);
#else
  (void)wifiOk;
#endif
}

as7341_gain_t asGain(uint16_t x) {
  switch (x) { case 1: return AS7341_GAIN_1X; case 2: return AS7341_GAIN_2X; case 4: return AS7341_GAIN_4X;
    case 8: return AS7341_GAIN_8X; case 16: return AS7341_GAIN_16X; case 32: return AS7341_GAIN_32X;
    case 128: return AS7341_GAIN_128X; case 256: return AS7341_GAIN_256X; default: return AS7341_GAIN_64X; }
}
// kind: "sample" | "dark" | "white"
void crystalScan(const char* kind) {
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "crystal"; d["kind"] = kind; d["t"] = millis(); d["seq"] = ++seq;
  d["sensor"] = "AS7341"; d["atime"] = spark::AS_ATIME; d["astep"] = spark::AS_ASTEP; d["full_scale"] = spark::AS_FULL_SCALE;
  d["settings"] = "ESTIMATE defaults pending hardware check (DESIGN_DECISIONS.md D7)";
  d["label"] = "MEASURED counts; T=(S-D)/(W-D) is DERIVED relative transmission, not a certified spectrum";
  if (!shieldSeated || !hasAs || !stationAck()) {
    d["ok"] = false; d["reason"] = !shieldSeated ? "NO_SHIELD" : "NO_SENSOR"; emit(d); return;
  }
  JsonObject modes = d["modes"].to<JsonObject>();
  bool isDark = !strcmp(kind, "dark"), isWhite = !strcmp(kind, "white"), isSample = !strcmp(kind, "sample");
  for (int m = 0; m < spark::ILLUM; m++) {
    JsonObject mo = modes[spark::ILLUM_NAME[m]].to<JsonObject>();
    if (!shieldSeated) { mo["skipped"] = "NO_SHIELD"; continue; }
    as7341.setGain(asGain(spark::MODE_GAIN_X[m])); mo["gain_x"] = spark::MODE_GAIN_X[m];
    if (m == 1) digitalWrite(WHITE_LED_PIN, HIGH);
    if (m == 3) digitalWrite(IR_LED_PIN, HIGH);
    if (m == 2 && !SPARK_UV_ENABLED) { mo["skipped"] = "UV_DISABLED_BUILD"; continue; }
    if (m == 2) {
      spark::UvDeny r = uv.request(millis(), 1500, shieldSeated, true, lowBattery);
      if (r != spark::UvDeny::OK) { mo["skipped"] = spark::UvGuard::name(r); continue; }
      digitalWrite(UV_LED_PIN, HIGH);
    }
    delay(30);  // LED settle
    uint16_t c[spark::AS_CH];
    bool ok = readAs(c);
    stationLedsOff();
    pollShield(millis());
    if (!ok || !shieldSeated) { mo["skipped"] = ok ? "SHIELD_LIFTED" : "READ_FAIL"; continue; }
    JsonArray arr = mo["counts"].to<JsonArray>();
    for (int i = 0; i < spark::AS_CH; i++) arr.add(c[i]);
    JsonArray sat = mo["sat"].to<JsonArray>();
    for (int i = 0; i < spark::AS_CH; i++) sat.add(spark::saturated(c[i]));
    if (isDark) { memcpy(cal.dark[m], c, sizeof(c)); cal.haveDark[m] = true; }
    if (isWhite) { memcpy(cal.white[m], c, sizeof(c)); cal.haveWhite[m] = true; }
    if (isSample && cal.ready(m)) {
      JsonArray t = mo["T"].to<JsonArray>();
      JsonArray v = mo["T_valid"].to<JsonArray>();
      for (int i = 0; i < spark::AS_CH; i++) {
        double tv; bool good = !spark::saturated(c[i]) && !spark::saturated(cal.white[m][i]) &&
                               spark::transmission(c[i], cal.dark[m][i], cal.white[m][i], tv);
        if (!good) tv = 0.0;
        t.add(good ? tv : 0.0); v.add(good);
      }
    }
    serviceDuringScan();
  }
  if (isDark || isWhite) {
    prefs.putBytes(isDark ? "dark" : "white", isDark ? (void*)cal.dark : (void*)cal.white, sizeof(cal.dark));
    prefs.putBytes(isDark ? "hd" : "hw", isDark ? (void*)cal.haveDark : (void*)cal.haveWhite, sizeof(cal.haveDark));
  }
  d["ok"] = true;
  JsonArray names = d["channels"].to<JsonArray>();
  for (int i = 0; i < spark::AS_CH; i++) names.add(spark::CH_NAME[i]);
  emit(d);
}

// ---------------- PPG (MAX30102) ----------------
uint32_t ppgBuf[PPG_BATCH]; int ppgN = 0; uint32_t ppgT0 = 0, lastIr = 0, lastRed = 0;
void drainPpg() {
  if (!hasPpg) return;
  ppg.check();
  while (ppg.available()) {
    if (ppgN == 0) ppgT0 = millis();
    lastIr = ppg.getFIFOIR(); lastRed = ppg.getFIFORed(); ppg.nextSample();
    ppgBuf[ppgN++] = lastIr;
    if (ppgN == PPG_BATCH) {
      JsonDocument d;
      d["schema"] = SCHEMA; d["type"] = "ppg"; d["t0"] = ppgT0; d["fs"] = 25; d["seq"] = ++seq;
      d["label"] = "raw IR counts for host-side pulse ESTIMATE (non-medical); host keeps features only";
      JsonArray a = d["ir"].to<JsonArray>();
      for (int i = 0; i < PPG_BATCH; i++) a.add(ppgBuf[i]);
      emit(d, false);  // raw PPG never goes over Wi-Fi
      ppgN = 0;
    }
  }
}

// ---------------- light ----------------
double lightBuf[LIGHT_WINDOW]; int lightN = 0; double luxSum = 0;
void pushLight(float lux) {
  if (!hasLux) return;
  lightBuf[lightN++] = spark::luxToBrightness(lux); luxSum += lux;
  if (lightN < LIGHT_WINDOW) return;
  spark::LightFeatures f;
  if (spark::lightFeatures(lightBuf, lightN, f)) {
    JsonDocument d;
    d["schema"] = SCHEMA; d["type"] = "features"; d["src"] = "light"; d["t"] = millis(); d["seq"] = ++seq;
    d["site"] = "on-device"; d["extractor"] = "beastbox.private_features/v1 light_features (C++ port)";
    d["brightness_map"] = "log10(1+lux)/log10(65536)"; d["n"] = lightN; d["lux_mean"] = luxSum / lightN;
    JsonObject o = d["features"].to<JsonObject>();
    o["mean"] = f.mean; o["min"] = f.min; o["max"] = f.max; o["std"] = f.std; o["range"] = f.range; o["trend"] = f.trend;
    emit(d);
  }
  lightN = 0; luxSum = 0;
}

void emitAudioFeatures() {
  if (!audioReady) return;
  spark::AudioFeatures f;
  portENTER_CRITICAL(&audioMux); f = audioOut; audioReady = false; portEXIT_CRITICAL(&audioMux);
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "features"; d["src"] = "audio"; d["t"] = millis(); d["seq"] = ++seq;
  d["site"] = "on-device"; d["extractor"] = "beastbox.private_features/v1 audio_features (C++ port)";
  d["n"] = FRAME * 16; d["rate"] = AUDIO_RATE;
  JsonObject o = d["features"].to<JsonObject>();
  o["rms"] = f.rms; o["phi_energy"] = f.phi_energy; o["phi_energy_alt"] = f.phi_energy_alt;
  o["spectral_entropy"] = f.spectral_entropy; o["spectral_centroid"] = f.spectral_centroid;
  o["spectral_spread"] = f.spectral_spread; o["dominant_frequency"] = f.dominant_frequency;
  o["onset_rate"] = f.onset_rate; o["zero_crossing"] = f.zero_crossing; o["loudness_trend"] = f.loudness_trend;
  emit(d);
}

// ---------------- battery ----------------
void readBattery() {
  uint32_t s = 0; for (int i = 0; i < 8; i++) s += analogReadMilliVolts(BAT_SENSE_PIN);
  vbatMv = (int)(BAT_DIVIDER * BAT_CAL * (float)s / 8.0f);  // ESTIMATE until checked once with a meter (D7)
  batteryPresent = vbatMv > 2500;
  bool low = batteryPresent && vbatMv < LOW_BAT_MV;
  if (low != lowBattery) { lowBattery = low; applyBrightness(); }
}

float imuA[3] = {0, 0, 0}, imuG[3] = {0, 0, 0};
float envT = 0, envH = 0, envP = 0;
void emitBody() {
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "body"; d["t"] = millis(); d["seq"] = ++seq;
  d["vbat_mv"] = vbatMv; d["battery_present"] = batteryPresent; d["low_battery"] = lowBattery;
  d["shield"] = shieldSeated; d["station"] = shieldSeated && hasAs; d["uv_on"] = uv.isOn();
  d["uv_cooldown_ms"] = uv.cooldownLeft(millis()); d["as_int"] = digitalRead(AS_INT_PIN);
  d["led_cap"] = lowBattery ? min(ledCap, LED_BRIGHTNESS_LOWBAT) : ledCap; d["host"] = hostSeen;
  d["amp_muted"] = ampForcedMute; d["heap"] = ESP.getFreeHeap();
  if (hasBme) {
    JsonObject e = d["env"].to<JsonObject>();
    e["temp_c"] = envT; e["humidity_pct"] = envH; e["pressure_hpa"] = envP;
  }
  if (hasImu) {
    JsonArray a = d["acc_g"].to<JsonArray>(); JsonArray g = d["gyr_dps"].to<JsonArray>();
    for (int i = 0; i < 3; i++) { a.add(imuA[i]); g.add(imuG[i]); }
  }
  d["label"] = "MEASURED body telemetry; host routes it into Spark overlay band 8 (not Cory's 54 slots)";
  emit(d);
}

void emitSelfTest() {  // Cory's emitSelfTest() fields + Spark parts
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "selftest"; d["firmware"] = FW; d["probe_base"] = PROBE_BASE; d["millis"] = millis();
  JsonObject s = d["sensors"].to<JsonObject>();
  s["lux"] = hasLux; s["bme280"] = hasBme; s["imu"] = hasImu; s["ppg"] = hasPpg; s["microphone"] = hasMic;
  s["speaker"] = hasSpk; s["as7341"] = hasAs; s["shield"] = shieldSeated;
  s["speech"] = hasSpk ? "pcm_s16le_16k_stream" : "no_speaker";
#if ARDUINO_USB_CDC_ON_BOOT
  s["link"] = "usb_cdc";
#else
  s["link"] = "uart";   // a UART bridge at 115200 is too slow for speech (needs ~43 kB/s); tones still work
#endif
#if SPARK_WIFI_AP
  s["wifi_ap"] = apUp;
#else
  s["wifi_ap"] = "off_build";
#endif
#if SPARK_GNSS_WIRED
  s["gnssStreamSeen"] = gps.charsProcessed() > 0;
#else
  s["gnss"] = "unwired";
#endif
  d["audioNoiseFloor"] = audioNoiseFloor; d["heapFree"] = ESP.getFreeHeap(); d["led_cap"] = ledCap;
  JsonObject c = d["crystal_cal"].to<JsonObject>();
  for (int m = 0; m < spark::ILLUM; m++) c[spark::ILLUM_NAME[m]] = cal.ready(m);
  d["label"] = "CONCEPT DESIGN / NOT BUILT HARDWARE";
  emit(d);
}

void reply(const char* cmd, const char* status, const char* detail = nullptr) {
  JsonDocument d; d["schema"] = SCHEMA; d["type"] = "ack"; d["cmd"] = cmd; d["status"] = status;
  if (detail) d["detail"] = detail;
  emit(d);
}

// ---------------- commands (text lines, like Cory's) ----------------
String line;
void handleCommand(String cmd) {
  cmd.trim(); cmd.toUpperCase();
  if (!cmd.length()) return;
  lastHostMs = millis(); hostSeen = true;
  int sp = cmd.indexOf(' ');
  String op = sp < 0 ? cmd : cmd.substring(0, sp);
  String rest = sp < 0 ? "" : cmd.substring(sp + 1);
  if (op == "SELFTEST" || op == "STATUS") emitSelfTest();
  else if (op == "HELP") Serial.println("Zeref Spark commands: SELFTEST | STATUS | CAL_AUDIO | PING | EXPR <ALL|CHEST|EYES|EYEL|EYER|PODS|CROWN> r g b | BRIGHT n | LEDS_OFF | TONE f0 f1 ms | MUTE 0/1 | SCAN | CAL_DARK | CAL_WHITE | UV ms | SAY_BEGIN id 16000 n | PCM id seq b64 | SAY_END id | SAY_STOP | HELP");
  else if (op == "PING") reply("PING", "OK");
  else if (op == "CAL_AUDIO") {
    Serial.println("{\"type\":\"calibration\",\"stage\":\"audio\",\"status\":\"starting\"}");
    audioNoiseFloor = 0.0f; calSum = 0; calN = 0; calStart = millis(); calAudioDone = false; calAudio = true;
  } else if (op == "EXPR") {
    char region[12] = {0}; int r = 0, g = 0, b = 0;
    if (sscanf(rest.c_str(), "%11s %d %d %d", region, &r, &g, &b) == 4 &&
        setRegion(String(region), constrain(r, 0, 255), constrain(g, 0, 255), constrain(b, 0, 255))) reply("EXPR", "OK");
    else reply("EXPR", "INVALID");
  } else if (op == "BRIGHT") {
    int v = rest.toInt(); ledCap = (uint8_t)constrain(v, 0, (int)LED_BRIGHTNESS_CAP); applyBrightness();
    reply("BRIGHT", v > LED_BRIGHTNESS_CAP ? "CLAMPED_TO_CAP" : "OK");
  } else if (op == "LEDS_OFF") { fillRange(0, LED_COUNT, 0, 0, 0); reply("LEDS_OFF", "OK"); }
  else if (op == "TONE") {
    float f0 = 0, f1 = 0; int ms = 0;
    if (sscanf(rest.c_str(), "%f %f %d", &f0, &f1, &ms) == 3 && ms > 0) { startTone(f0, f1, ms); reply("TONE", hasSpk ? "OK" : "NO_SPEAKER"); }
    else reply("TONE", "INVALID");
  } else if (op == "MUTE") { ampForcedMute = rest.toInt() != 0; setAmp(spk.left > 0 || speech.active()); reply("MUTE", ampForcedMute ? "MUTED" : "UNMUTED"); }
  else if (op == "SCAN") crystalScan("sample");
  else if (op == "CAL_DARK") crystalScan("dark");
  else if (op == "CAL_WHITE") crystalScan("white");
  else if (op == "UV" && !SPARK_UV_ENABLED) reply("UV", "UV_DISABLED_BUILD");
  else if (op == "UV") {
    int ms = rest.toInt();
    bool ack = hasAs && stationAck();
    spark::UvDeny r = uv.request(millis(), ms < 0 ? 0 : (uint32_t)ms, shieldSeated, ack, lowBattery);
    if (r == spark::UvDeny::OK) digitalWrite(UV_LED_PIN, HIGH);
    reply("UV", spark::UvGuard::name(r));
  } else reply(op.c_str(), "UNKNOWN");
}
// Speech lines first (case-sensitive base64), then the normal command set. From Wi-Fi only speech is accepted.
void handleLine(const String& raw, bool fromWs) {
  uint32_t now = millis();
  spark::SpeechStatus st = spark::handleSpeechLine(raw.c_str(), speech, now);
  if (st == spark::SpeechStatus::NOT_SPEECH) {
    if (fromWs) { reply("WS", "SPEECH_ONLY"); return; }   // UV/SCAN/LED commands never come over Wi-Fi
    handleCommand(raw);
    return;
  }
  lastHostMs = now; hostSeen = true;
  bool isPcm = raw.startsWith("PCM ");
  if (st == spark::SpeechStatus::OK) {
    if (raw.startsWith("SAY_BEGIN ")) { spk.left = 0; setAmp(true); muteAt = 0; emitSpeech(ampForcedMute ? "begin_amp_muted" : "begin"); }
    else if (raw.startsWith("SAY_STOP")) { spkPendLen = 0; muteAt = now + 20; emitSpeech("stopped"); }
    else if (!isPcm) emitSpeech("ending");
  } else {
    reply(isPcm ? "PCM" : "SAY", spark::speechStatusName(st));
  }
}
static constexpr unsigned MAX_LINE = 800;   // a PCM line is <= ~700 chars (256 samples as base64)
void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') { if (line.length()) handleLine(line, false); line = ""; }
    else if (line.length() < MAX_LINE) line += c;
  }
}

void serviceDuringScan() { drainPpg(); pumpSpeaker(millis()); }

void setup() {
  // Safe states first: amp muted, all station LEDs off.
  pinMode(AMP_SD_PIN, OUTPUT); digitalWrite(AMP_SD_PIN, LOW);
  pinMode(WHITE_LED_PIN, OUTPUT); digitalWrite(WHITE_LED_PIN, LOW);
  pinMode(UV_LED_PIN, OUTPUT); digitalWrite(UV_LED_PIN, LOW);
  pinMode(IR_LED_PIN, OUTPUT); digitalWrite(IR_LED_PIN, LOW);
  pinMode(SHIELD_SENSE_PIN, INPUT); pinMode(AS_INT_PIN, INPUT_PULLUP);
  analogSetPinAttenuation(BAT_SENSE_PIN, ADC_11db);

#if ARDUINO_USB_CDC_ON_BOOT
  Serial.setRxBufferSize(4096);   // native USB CDC: speech PCM lines arrive at ~43 kB/s
#endif
  Serial.begin(115200); delay(350);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire1.begin(ST_SDA_PIN, ST_SCL_PIN, 100000);
  hasLux = luxSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  hasBme = bme.begin(0x76) || bme.begin(0x77);
  static ICM42688 imu68(Wire, 0x68), imu69(Wire, 0x69);
  if (imu68.begin() >= 0) { imu = &imu68; hasImu = true; } else if (imu69.begin() >= 0) { imu = &imu69; hasImu = true; }
  hasPpg = ppg.begin(Wire, I2C_SPEED_FAST); if (hasPpg) ppg.setup(60, 4, 2, 100, 411, 4096);
  hasMic = initMicrophone();
  hasSpk = initSpeaker();
  hasAs = as7341.begin(0x39, &Wire1);
  if (hasAs) { as7341.setATIME(spark::AS_ATIME); as7341.setASTEP(spark::AS_ASTEP); as7341.setGain(AS7341_GAIN_64X); }
  prefs.begin("zs-crystal", false);
  prefs.getBytes("dark", cal.dark, sizeof(cal.dark)); prefs.getBytes("white", cal.white, sizeof(cal.white));
  prefs.getBytes("hd", cal.haveDark, sizeof(cal.haveDark)); prefs.getBytes("hw", cal.haveWhite, sizeof(cal.haveWhite));
#if SPARK_GNSS_WIRED
  GNSS.begin(9600, SERIAL_8N1, GNSS_RX_PIN, GNSS_TX_PIN);
#endif
#if SPARK_WIFI_AP
  if (strlen(AP_PASS) >= 8) { WiFi.mode(WIFI_AP); apUp = WiFi.softAP(AP_SSID, AP_PASS); ws.begin(); ws.onEvent(onWs); }
  else Serial.println("{\"type\":\"ack\",\"cmd\":\"WIFI\",\"status\":\"AP_OFF_NO_PASSWORD\"}");
#endif
  strip.begin(); applyBrightness(); fillRange(0, LED_COUNT, 0, 0, 0); strip.show();
  if (hasMic) xTaskCreatePinnedToCore(audioTask, "zs-audio", 8192, nullptr, 2, nullptr, 0);
  readBattery(); pollShield(millis());
  Serial.printf("Zeref Spark %s (Reality Bridge Probe %s base) link: USB CDC JSON lines (115200 nominal)\n", FW, PROBE_BASE);
  emitSelfTest();
}

void loop() {
  uint32_t now = millis();
#if SPARK_WIFI_AP
  ws.loop();
#endif
#if SPARK_GNSS_WIRED
  while (GNSS.available()) gps.encode(GNSS.read());
#endif
  pollSerial();
  pollShield(now);
  if (!uv.tick(now, shieldSeated)) digitalWrite(UV_LED_PIN, LOW);
  if (!shieldSeated) { digitalWrite(WHITE_LED_PIN, LOW); digitalWrite(IR_LED_PIN, LOW); }
  drainPpg();
  pumpSpeaker(now);
  emitAudioFeatures();
  if (calAudioDone) {
    calAudioDone = false;
    audioNoiseFloor = calN ? (float)(calSum / calN) * 1.25f : 0.0025f;   // Cory's rule (main.cpp:82-83)
    audioNoiseFloor = constrain(audioNoiseFloor, 0.0001f, 0.08f);
    JsonDocument d; d["type"] = "calibration"; d["stage"] = "audio"; d["status"] = "complete"; d["noiseFloor"] = audioNoiseFloor; emit(d);
  }
  if (hostSeen && now - lastHostMs > HOST_TIMEOUT_MS) hostSeen = false;
  if (!hostSeen && now - lastShow >= 40) idleGlow(now);
  if (ledsDirty && now - lastShow >= 20) { strip.show(); ledsDirty = false; lastShow = now; }

  if (now - lastBody >= BODY_MS) { lastBody = now; readBattery(); emitBody(); }
  if (now - lastPacket < PACKET_MS) return;
  lastPacket = now;
  // Cory's 100 ms probe packet (main.cpp:111-121), same field names so his Reality Bridge sim still reads it.
  float lux = hasLux ? luxSensor.readLightLevel() : 0.0f, tempC = hasBme ? bme.readTemperature() : 0.0f,
        humidity = hasBme ? bme.readHumidity() : 0.0f, pressure = hasBme ? bme.readPressure() / 100.0f : 0.0f;
  envT = tempC; envH = humidity; envP = pressure;
  float motion = 0.0f, heading = 0.0f;
  if (hasImu && imu->getAGT() >= 0) {
    imuA[0] = imu->accX(); imuA[1] = imu->accY(); imuA[2] = imu->accZ();
    imuG[0] = imu->gyrX(); imuG[1] = imu->gyrY(); imuG[2] = imu->gyrZ();
    float ax = imuA[0] * 9.80665f, ay = imuA[1] * 9.80665f, az = imuA[2] * 9.80665f;  // g -> m/s^2 like Adafruit events
    motion = min(1.0f, sqrtf(ax * ax + ay * ay + az * az) / 30.0f);
    heading = fmodf(atan2f(ay, ax) * 180.0f / PI + 360.0f, 360.0f);
  }
  pushLight(lux);
  JsonDocument d;
  d["schema"] = SCHEMA; d["type"] = "probe";
  d["t"] = now; d["lux"] = lux; d["motion"] = motion; d["audioRms"] = (float)legacyAudioRms; d["temperatureC"] = tempC;
  d["humidityPct"] = humidity; d["pressureHpa"] = pressure; d["ppgIr"] = lastIr; d["ppgRed"] = lastRed; d["heading"] = heading;
  d["firmware"] = FW; d["probe_base"] = PROBE_BASE;
#if SPARK_GNSS_WIRED
  if (gps.location.isValid()) { d["latitude"] = gps.location.lat(); d["longitude"] = gps.location.lng(); } else { d["latitude"] = nullptr; d["longitude"] = nullptr; }
  d["altitudeM"] = gps.altitude.isValid() ? gps.altitude.meters() : 0.0; d["satellites"] = gps.satellites.isValid() ? gps.satellites.value() : 0;
#else
  d["latitude"] = nullptr; d["longitude"] = nullptr; d["gnss"] = "unwired";
#endif
  JsonObject present = d["present"].to<JsonObject>();
  present["lux"] = hasLux; present["environment"] = hasBme; present["imu"] = hasImu; present["ppg"] = hasPpg;
  present["microphone"] = hasMic; present["speaker"] = hasSpk; present["as7341"] = hasAs;
#if SPARK_GNSS_WIRED
  present["gnss"] = gps.charsProcessed() > 0;
#else
  present["gnss"] = false;
#endif
  emit(d);
}
