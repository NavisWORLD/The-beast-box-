/**
 * Beast Box Muse browser module.
 *
 * Same trait schema as Cosmic Synapse HANDHELD arcade/lost-cosmos/muse.mjs:
 * focus = rounded beta share, calm = rounded alpha share, spark = rounded gamma share.
 * Wellness and game signals only. Not a medical measurement.
 * Raw samples stay in this page and are cleared after each trait update.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.BeastboxMuse = api;
})(typeof window !== "undefined" ? window : (typeof globalThis !== "undefined" ? globalThis : null), function () {
  var TRAIT_SCHEMA = "cosmic-muse-traits-v1";
  var DISCLAIMER = "Wellness and game signals only. Not a medical measurement, diagnosis, or treatment.";
  var EEG_RATE = 256;
  var WINDOW = 256;
  var MUSE_SERVICE = 0xfe8d;
  var CONTROL = "273e0001-4c4d-454d-96be-f03bac821358";
  var EEG = {
    TP9: "273e0003-4c4d-454d-96be-f03bac821358",
    AF7: "273e0004-4c4d-454d-96be-f03bac821358",
    AF8: "273e0005-4c4d-454d-96be-f03bac821358",
    TP10: "273e0006-4c4d-454d-96be-f03bac821358"
  };
  var FALLBACK_ORDER = ["lsl", "ble"];
  var BIO_CHANNELS = [
    ["heart_rate_bpm", 30, 220],
    ["hrv_rmssd_ms", 0, 500],
    ["respiration_rate_bpm", 4, 60],
    ["skin_temperature_c", 20, 45],
    ["spo2_pct", 70, 100],
    ["eda_microsiemens", 0, 100],
    ["accelerometer_rms_g", 0, 20],
    ["eeg_alpha_relative", 0, 1],
    ["eeg_beta_relative", 0, 1],
    ["eeg_theta_relative", 0, 1],
    ["eeg_delta_relative", 0, 1],
    ["eeg_gamma_relative", 0, 1]
  ];

  function encodeCommand(cmd) {
    var encoded = new TextEncoder().encode("X" + cmd + "\n");
    encoded[0] = encoded.length - 1;
    return encoded;
  }

  function decodeUnsigned12BitData(samples) {
    var out = [];
    for (var i = 0; i < samples.length; i++) {
      if (i % 3 === 0) out.push((samples[i] << 4) | (samples[i + 1] >> 4));
      else {
        out.push(((samples[i] & 0xf) << 8) | samples[i + 1]);
        i++;
      }
    }
    return out;
  }

  function decodeEegPacket(packet) {
    var bytes = packet instanceof DataView
      ? new Uint8Array(packet.buffer, packet.byteOffset, packet.byteLength)
      : packet;
    var sequence = bytes[0] | (bytes[1] << 8);
    var raw = decodeUnsigned12BitData(bytes.subarray(2));
    return { sequence: sequence, samples: raw.map(function (n) { return 0.48828125 * (n - 0x800); }) };
  }

  function bandPowers(samples, sampleRate) {
    var rate = sampleRate || EEG_RATE;
    var n = samples.length;
    var bands = { delta: 0, theta: 0, alpha: 0, beta: 0, gamma: 0 };
    var half = n >> 1;
    for (var k = 1; k < half; k++) {
      var freq = (k * rate) / n;
      if (freq >= 45) break;
      var re = 0;
      var im = 0;
      for (var i = 0; i < n; i++) {
        var ang = (-2 * Math.PI * k * i) / n;
        var s = samples[i];
        re += s * Math.cos(ang);
        im += s * Math.sin(ang);
      }
      var power = re * re + im * im;
      if (freq < 4) bands.delta += power;
      else if (freq < 8) bands.theta += power;
      else if (freq < 13) bands.alpha += power;
      else if (freq < 30) bands.beta += power;
      else bands.gamma += power;
    }
    Object.keys(bands).forEach(function (name) {
      if (bands[name] < 1e-18) bands[name] = 0;
    });
    return bands;
  }

  function deriveTraits(bands) {
    var sum = bands.delta + bands.theta + bands.alpha + bands.beta + bands.gamma;
    var round = function (part) {
      return sum > 0 ? Math.max(0, Math.min(100, Math.round((100 * part) / sum))) : 0;
    };
    return {
      schema: TRAIT_SCHEMA,
      focus: round(bands.beta),
      calm: round(bands.alpha),
      spark: round(bands.gamma)
    };
  }

  function relativeBands(bands) {
    var sum = bands.delta + bands.theta + bands.alpha + bands.beta + bands.gamma;
    var share = function (part) {
      if (!(sum > 0)) return 0;
      return Math.min(1, Math.max(0, part / sum));
    };
    return {
      delta: share(bands.delta),
      theta: share(bands.theta),
      alpha: share(bands.alpha),
      beta: share(bands.beta),
      gamma: share(bands.gamma)
    };
  }

  function bioFeatures(relative) {
    var readings = {
      eeg_delta_relative: relative.delta,
      eeg_theta_relative: relative.theta,
      eeg_alpha_relative: relative.alpha,
      eeg_beta_relative: relative.beta,
      eeg_gamma_relative: relative.gamma
    };
    return BIO_CHANNELS.map(function (spec) {
      var name = spec[0];
      var low = spec[1];
      var high = spec[2];
      if (!Object.prototype.hasOwnProperty.call(readings, name)) return 0;
      return (2 * (readings[name] - low) / (high - low)) - 1;
    });
  }

  function mockWindow() {
    var samples = new Float64Array(WINDOW);
    for (var i = 0; i < WINDOW; i++) {
      var t = i / EEG_RATE;
      samples[i] = 30 * Math.sin(2 * Math.PI * 10 * t)
        + 8 * Math.sin(2 * Math.PI * 20 * t)
        + 4 * Math.sin(2 * Math.PI * 40 * t);
    }
    return samples;
  }

  function mockTraits() {
    var samples = mockWindow();
    var traits = deriveTraits(bandPowers(samples));
    samples.fill(0);
    return traits;
  }

  function simulatedSnapshot() {
    var samples = mockWindow();
    var powers = bandPowers(samples);
    var traits = deriveTraits(powers);
    var relative = relativeBands(powers);
    var features = bioFeatures(relative);
    samples.fill(0);
    return {
      schema: "beastbox-muse-snapshot-v1",
      disclaimer: DISCLAIMER,
      transport: "simulate",
      simulated: true,
      hardwareAttested: false,
      traits: traits,
      relative: relative,
      bioFeatures: features,
      rawEeg: "omitted"
    };
  }

  function browserSupport() {
    var nav = typeof navigator === "undefined" ? null : navigator;
    var ua = nav && nav.userAgent ? nav.userAgent : "";
    var ios = /iPad|iPhone|iPod/.test(ua) || (nav && nav.platform === "MacIntel" && nav.maxTouchPoints > 1);
    var safari = /safari/i.test(ua) && !/chrome|android|crios|fxios|edg/i.test(ua);
    var hasBT = !!(nav && nav.bluetooth && nav.bluetooth.requestDevice);
    var reason = "";
    if (ios || safari) {
      reason = "Safari and iOS do not implement Web Bluetooth. Use desktop Chrome, Edge, Opera, or another Chromium browser, or the Python kit.";
    } else if (!hasBT) {
      reason = "This browser does not expose Web Bluetooth. Use desktop Chrome, Edge, or Opera. The simulated headband still works.";
    } else if (typeof isSecureContext === "boolean" && !isSecureContext) {
      reason = "Web Bluetooth needs a secure page. http://127.0.0.1 is fine; plain http on another host is not.";
    }
    return {
      webBluetooth: hasBT && !ios && !safari,
      safari: !!safari,
      ios: !!ios,
      ok: hasBT && !ios && !safari,
      reason: reason,
      fallbackOrder: FALLBACK_ORDER.slice()
    };
  }

  function MuseLink(onTraits) {
    this.onTraits = onTraits;
    this.device = null;
    this.running = false;
    this.ring = new Float64Array(WINDOW);
    this.filled = 0;
    this.write = 0;
  }

  MuseLink.prototype.clear = function () {
    this.ring.fill(0);
    this.filled = 0;
    this.write = 0;
  };

  MuseLink.prototype.push = function (samples) {
    for (var s = 0; s < samples.length; s++) {
      this.ring[this.write] = samples[s];
      this.write = (this.write + 1) % WINDOW;
      if (this.filled < WINDOW) this.filled++;
    }
    if (this.filled < WINDOW) return;
    var ordered = new Float64Array(WINDOW);
    for (var i = 0; i < WINDOW; i++) ordered[i] = this.ring[(this.write + i) % WINDOW];
    var powers = bandPowers(ordered);
    var traits = deriveTraits(powers);
    var snapshot = {
      schema: "beastbox-muse-snapshot-v1",
      disclaimer: DISCLAIMER,
      transport: "browser",
      simulated: false,
      hardwareAttested: false,
      traits: traits,
      relative: relativeBands(powers),
      bioFeatures: bioFeatures(relativeBands(powers)),
      rawEeg: "omitted"
    };
    ordered.fill(0);
    this.onTraits(snapshot);
  };

  MuseLink.prototype.connect = async function (options) {
    var aux = options && options.aux;
    var nav = typeof navigator === "undefined" ? null : navigator;
    if (!nav || !nav.bluetooth) throw new Error("Web Bluetooth is not available in this browser");
    this.device = await nav.bluetooth.requestDevice({
      filters: [{ services: [MUSE_SERVICE] }],
      optionalServices: [MUSE_SERVICE]
    });
    var server = await this.device.gatt.connect();
    var service = await server.getPrimaryService(MUSE_SERVICE);
    var control = await service.getCharacteristic(CONTROL);
    var self = this;
    var send = function (cmd) { return control.writeValue(encodeCommand(cmd)); };
    await send("h");
    await send(aux ? "p20" : "p21");
    var channel = await service.getCharacteristic(EEG.AF7);
    await channel.startNotifications();
    channel.addEventListener("characteristicvaluechanged", function (event) {
      if (!self.running) return;
      var decoded = decodeEegPacket(event.target.value);
      self.push(decoded.samples);
    });
    await send("s");
    this.running = true;
    this.device.addEventListener("gattserverdisconnected", function () {
      self.running = false;
      self.clear();
    });
  };

  MuseLink.prototype.stop = async function () {
    this.running = false;
    this.clear();
    try { if (this.device && this.device.gatt) this.device.gatt.disconnect(); } catch (err) { /* already gone */ }
  };

  return {
    TRAIT_SCHEMA: TRAIT_SCHEMA,
    DISCLAIMER: DISCLAIMER,
    EEG_RATE: EEG_RATE,
    WINDOW: WINDOW,
    FALLBACK_ORDER: FALLBACK_ORDER,
    encodeCommand: encodeCommand,
    decodeUnsigned12BitData: decodeUnsigned12BitData,
    decodeEegPacket: decodeEegPacket,
    bandPowers: bandPowers,
    deriveTraits: deriveTraits,
    relativeBands: relativeBands,
    bioFeatures: bioFeatures,
    mockWindow: mockWindow,
    mockTraits: mockTraits,
    simulatedSnapshot: simulatedSnapshot,
    browserSupport: browserSupport,
    MuseLink: MuseLink
  };
});
